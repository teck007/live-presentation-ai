import { ref } from "vue";
import { generateSlide } from "../api/presentation";
import type { SlideItem, SlideReplacedEvent, SlideWsEvent, SlideWsSlideEvent, TranscriptItem } from "../types";

// Evento terminal que pinta: slide nuevo o reemplazo de regen.
type SlidePaintEvent = SlideWsSlideEvent | SlideReplacedEvent;

// Evita saturar al LLM: espera este silencio antes de enviar el turno final.
const DEBOUNCE_MS = 4000;

function readWsSlidesFlag(): boolean {
  try {
    const raw = import.meta.env.VITE_WS_SLIDES_ENABLED;
    if (raw === undefined || raw === null || String(raw).trim() === "") return true;
    const v = String(raw).trim().toLowerCase();
    return v !== "false" && v !== "0" && v !== "no" && v !== "off";
  } catch {
    return true;
  }
}

/**
 * Cola de turnos finales -> POST /api/presentations/generate -> slides[] (flag-off),
 * o inserción directa de eventos WS slide_* (flag-on).
 * El LLM devuelve JSON plano (layout + texto); el diseño vive en SlideCanvas.
 */
export function useLivePresentation(options?: { wsEnabled?: boolean; topicVersion?: number }) {
  const slides = ref<SlideItem[]>([]);
  const pending = ref(0);
  const error = ref<string | null>(null);
  const lastFiltered = ref(false);

  // Flag WS async: on -> los slides llegan por WS; off -> debounce 4s + POST.
  const wsSlidesEnabled = ref(options?.wsEnabled ?? readWsSlidesFlag());
  // Versión de topic vigente (autoridad: backend; el frontend la refleja).
  const currentTopicVersion = ref(options?.topicVersion ?? 1);
  // Single palette per session: first received wins, reused for POST calls.
  const paletteId = ref<string | null>(null);
  const audience = ref<string>("general");

  // Turnos ya reclamados por el WS (pending o filtered vistos): el POST los salta.
  const wsOwnedTurnIds = new Set<string>();
  // Turnos WS con pending sin terminal (mueven el spinner).
  const pendingWsTurns = new Set<string>();
  // seq -> slide id, para inserción ordenada por llegada (seq de arribo backend).
  const slideSeqById = new Map<string, number>();
  const maxPaintedSeq = ref(0);

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  let queued: TranscriptItem | null = null;
  let topic = "";
  // Dedupe opción B: red de seguridad por turnId (el origen ya evita el doble push).
  const seenTurnIds = new Set<string>();
  let lastSentKey = "";

  function setTopic(value: string) {
    topic = value.trim();
  }

  function setWsEnabled(value: boolean) {
    wsSlidesEnabled.value = value;
  }

  function setTopicVersion(version: number) {
    if (Number.isFinite(version) && version > 0) {
      currentTopicVersion.value = Math.floor(version);
    }
  }

  function setPaletteId(value: string | null) {
    paletteId.value = value && value.trim() ? value.trim() : null;
  }

  function setAudience(value: string) {
    const v = (value || "").trim().toLowerCase();
    const valid = ["ninos", "estudiantes", "general", "profesionales", "expertos"];
    audience.value = valid.includes(v) ? v : "general";
  }

  function isWsOwned(turnId: string): boolean {
    return wsOwnedTurnIds.has(turnId);
  }

  function clear() {
    slides.value = [];
    error.value = null;
    lastFiltered.value = false;
    queued = null;
    seenTurnIds.clear();
    wsOwnedTurnIds.clear();
    pendingWsTurns.clear();
    paletteId.value = null;
    slideSeqById.clear();
    maxPaintedSeq.value = 0;
    lastSentKey = "";
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    pending.value = 0;
  }

  function trackTerminal(turnId: string) {
    if (pendingWsTurns.delete(turnId)) {
      pending.value = Math.max(0, pending.value - 1);
    }
  }

  /** Inserta un SlideItem manteniendo el orden por seq de arribo. */
  function insertBySeq(item: SlideItem, seq: number) {
    let index = slides.value.length;
    for (let i = 0; i < slides.value.length; i++) {
      const existing = slideSeqById.get(slides.value[i].id);
      if (existing !== undefined && existing > seq) {
        index = i;
        break;
      }
    }
    slides.value.splice(index, 0, item);
    slideSeqById.set(item.id, seq);
    if (seq > maxPaintedSeq.value) maxPaintedSeq.value = seq;
  }

  /** Pinta un terminal de inmediato, en posición ordenada por seq. */
  function paintSlide(event: SlidePaintEvent) {
    error.value = null;
    lastFiltered.value = false;
    // Regen: el reemplazo elimina el slide anterior del mismo turno al pintar.
    if (event.type === "slide_replaced") {
      const prefix = `${event.turnId}-`;
      for (let i = slides.value.length - 1; i >= 0; i--) {
        if (slides.value[i].id.startsWith(prefix)) {
          slideSeqById.delete(slides.value[i].id);
          slides.value.splice(i, 1);
        }
      }
    }
    insertBySeq(
      {
        layout: event.layout,
        title: event.title,
        titulo: event.titulo,
        text: event.text,
        texto: event.texto,
        bullets: event.bullets,
        listado: event.listado,
        keywords: event.keywords,
        filtered: false,
        kicker: event.kicker,
        subtitle: event.subtitle,
        cards: event.cards,
        conceptos: event.conceptos,
        stats: event.stats,
        chips: event.chips,
        steps: event.steps,
        code: event.code,
        code_tipo: event.code_tipo,
        code_titulo: event.code_titulo,
        codigo_matematica: event.codigo_matematica,
        image: event.image,
        imagen_hashtag: event.imagen_hashtag,
        imagen_prompt: event.imagen_prompt,
        explanation: event.explanation,
        concept: event.concept,
        example: event.example,
        takeaway: event.takeaway,
        content_type: event.content_type,
        layout_reason: event.layout_reason,
        audience: event.audience,
        html: event.html,
        palette_id: event.palette_id,
        palette: event.palette,
        id: `${event.turnId}-${event.seq}`,
        timestamp: Date.now(),
      },
      event.seq,
    );
  }

  /**
   * Aplica un evento WS de slide con pintura inmediata.
   * - `slide_pending`: marca el turno como WS-owned y sube el spinner.
   * - `slide`: pre-paint version guard + dedupe por id, pinta al llegar.
   * - `slide_filtered`: solo log, sin pintar (pero reclama el turno).
   * - `slide_kept`: como `slide_filtered` (log, sin pintar).
   *   El gate decidió que el slide actual ya cubre el turno.
   * - `slide_replaced`: como `slide`, pero elimina al pintar el slide anterior del turno.
   * - `slide_removed`: elimina el slide del turno.
   * - `slide_error`: pinta el error.
   * - `slide_image_updated`: parchea image (+html) del slide `${turnId}-${seq}`
   *   sin reordenar ni mover el slide activo.
   */
  function handleSlideEvent(event: SlideWsEvent) {
    // El backend es la autoridad de la versión: se adopta la mayor vista.
    // Así el guard nunca corre con una versión local rezagada.
    if (event.topicVersion > currentTopicVersion.value) {
      currentTopicVersion.value = event.topicVersion;
    }
    // First palette wins: keep session stable.
    if (
      (event.type === "slide" || event.type === "slide_replaced") &&
      typeof event.palette_id === "string" &&
      event.palette_id &&
      !paletteId.value
    ) {
      paletteId.value = event.palette_id;
    }
    switch (event.type) {
      case "slide_pending": {
        wsOwnedTurnIds.add(event.turnId);
        if (!pendingWsTurns.has(event.turnId)) {
          pendingWsTurns.add(event.turnId);
          pending.value += 1;
        }
        error.value = null;
        break;
      }
      case "slide": {
        wsOwnedTurnIds.add(event.turnId);
        trackTerminal(event.turnId);
        // Pre-paint guard: versión vieja nunca pinta aunque haya pasado el server.
        if (event.topicVersion !== currentTopicVersion.value) break;
        // Dedupe: el mismo turno+seq nunca pinta dos veces.
        if (slideSeqById.has(`${event.turnId}-${event.seq}`)) break;
        paintSlide(event);
        break;
      }
      case "slide_filtered": {
        wsOwnedTurnIds.add(event.turnId);
        trackTerminal(event.turnId);
        lastFiltered.value = true;
        // Silencioso en UI; visible solo en logs.
        console.info(
          `[slides] filtrado turnId=${event.turnId} seq=${event.seq} v=${event.topicVersion}`,
        );
        break;
      }
      case "slide_kept": {
        wsOwnedTurnIds.add(event.turnId);
        trackTerminal(event.turnId);
        // Gate keep: el slide actual ya cubre el turno. Log, sin pintar.
        console.info(
          `[slides] kept turnId=${event.turnId} seq=${event.seq} v=${event.topicVersion}`,
        );
        break;
      }
      case "slide_replaced": {
        wsOwnedTurnIds.add(event.turnId);
        trackTerminal(event.turnId);
        // Pre-paint guard: versión vieja nunca pinta aunque haya pasado el server.
        if (event.topicVersion !== currentTopicVersion.value) break;
        // Dedupe: el mismo turno+seq nunca pinta dos veces.
        if (slideSeqById.has(`${event.turnId}-${event.seq}`)) break;
        paintSlide(event);
        break;
      }
      case "slide_removed": {
        wsOwnedTurnIds.add(event.turnId);
        trackTerminal(event.turnId);
        if (event.topicVersion !== currentTopicVersion.value) break;
        const prefix = `${event.turnId}-`;
        for (let i = slides.value.length - 1; i >= 0; i--) {
          if (slides.value[i].id.startsWith(prefix)) {
            slideSeqById.delete(slides.value[i].id);
            slides.value.splice(i, 1);
          }
        }
        break;
      }
      case "slide_error": {
        trackTerminal(event.turnId);
        error.value = event.message || "No se pudo generar el slide.";
        break;
      }
      case "slide_image_updated": {
        // Progressive patch: version guard + patch in place, no reorder,
        // no activeIndex change (length unchanged, so no auto-jump).
        if (event.topicVersion !== currentTopicVersion.value) break;
        if (typeof event.image !== "string" || !event.image.startsWith("https://")) break;
        const id = `${event.turnId}-${event.seq}`;
        const target = slides.value.find((s) => s.id === id);
        if (!target) break;
        target.image = event.image;
        if (typeof event.html === "string" && event.html.trim()) {
          target.html = event.html;
        }
        break;
      }
    }
  }

  async function flush() {
    const item = queued;
    queued = null;
    if (!item || !item.text.trim()) return;
    // Single-producer: si el WS ya reclamó este turnId, el POST no compite.
    if (item.sessionId && wsOwnedTurnIds.has(item.sessionId)) return;
    // Segunda barrera: mismo turnId o mismo texto ya enviado → no repite consulta al LLM.
    const key = `${item.sessionId ?? "turn"}|${item.text.trim()}`;
    if (item.sessionId && seenTurnIds.has(item.sessionId)) return;
    if (key === lastSentKey) return;
    if (item.sessionId) seenTurnIds.add(item.sessionId);
    lastSentKey = key;
    pending.value += 1;
    error.value = null;
    try {
      const res = await generateSlide({
        transcript: item.text,
        topic,
        keywords: item.keywords ?? [],
        palette_id: paletteId.value,
        audience: audience.value,
        is_opening: slides.value.length === 0,
      });
      lastFiltered.value = res.filtered;
      if (res.filtered) return;
      if (typeof res.palette_id === "string" && res.palette_id && !paletteId.value) {
        paletteId.value = res.palette_id;
      }
      slides.value.push({
        ...res,
        id: `${item.sessionId ?? "turn"}-${Date.now()}`,
        timestamp: Date.now(),
      });
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "No se pudo generar el slide.";
    } finally {
      pending.value = Math.max(0, pending.value - 1);
    }
  }

  /** Encola un turno final; se envía tras DEBOUNCE_MS sin nuevos turnos (solo flag-off). */
  function queueTranscript(item: TranscriptItem) {
    // Flag-on: el WS es el único productor; no se encola al POST.
    if (wsSlidesEnabled.value) return;
    queued = item;
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => void flush(), DEBOUNCE_MS);
  }

  // Test helper: generates a slide from typed text without speaking.
  // Calls the LLM endpoint directly with no debounce and no WS/dedupe checks,
  // only skipping empty or too-short input.
  async function submitTestTranscript(text: string): Promise<void> {
    const transcript = text.trim();
    if (transcript.length < 3) return;
    pending.value += 1;
    error.value = null;
    try {
      const res = await generateSlide({
        transcript,
        topic,
        keywords: [],
        palette_id: paletteId.value,
        audience: audience.value,
        is_opening: slides.value.length === 0,
      });
      lastFiltered.value = res.filtered;
      if (res.filtered) return;
      if (typeof res.palette_id === "string" && res.palette_id && !paletteId.value) {
        paletteId.value = res.palette_id;
      }
      slides.value.push({
        ...res,
        id: `test-${Date.now()}`,
        timestamp: Date.now(),
      });
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : "No se pudo generar el slide.";
    } finally {
      pending.value = Math.max(0, pending.value - 1);
    }
  }

  return {
    slides,
    pending,
    error,
    lastFiltered,
    wsSlidesEnabled,
    currentTopicVersion,
    maxPaintedSeq,
    paletteId,
    audience,
    setTopic,
    setWsEnabled,
    setTopicVersion,
    setPaletteId,
    setAudience,
    isWsOwned,
    handleSlideEvent,
    queueTranscript,
    submitTestTranscript,
    clear,
  };
}
