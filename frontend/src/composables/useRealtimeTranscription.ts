import { computed, ref } from "vue";
import { RealtimeClient } from "../api/realtimeClient";
import { createPrefilter } from "./useAudioPrefilter";
import type { AudioPrefilter } from "./useAudioPrefilter";
import type {
  RealtimeStatus,
  ServerEvent,
  SlideWsEvent,
  TranscriptItem,
  TurnState,
} from "../types";

// Umbrales locales (el backend es la autoridad de la pausa prolongada).
const IDLE_PAUSE_HINT_MS = 15000; // Aviso idle_pause tras 15s de silencio.
const SPEAKING_HANGOVER_MS = 400; // Extiende "hablando" ante micro-cortes.
const WORKLET_THRESHOLD = 0.02; // RMS minimo para considerar voz.
const PREFILTER_ENABLED_KEY = "prefilter.enabled";
const PREFILTER_THRESHOLD_KEY = "prefilter.threshold";

function readPrefilterEnabled(): boolean {
  try {
    const raw = localStorage.getItem(PREFILTER_ENABLED_KEY);
    return raw === null ? true : raw !== "false";
  } catch {
    return true;
  }
}

function readPrefilterThreshold(): number {
  try {
    const raw = localStorage.getItem(PREFILTER_THRESHOLD_KEY);
    const v = raw === null ? WORKLET_THRESHOLD : Number(raw);
    if (!Number.isFinite(v)) return WORKLET_THRESHOLD;
    return Math.min(0.05, Math.max(0.01, v));
  } catch {
    return WORKLET_THRESHOLD;
  }
}

interface FrameMessage {
  type: string;
  pcm?: ArrayBuffer;
  voiced?: boolean;
}

/**
 * Composable de transcripcion realtime: AudioWorklet PCM 24k + WS.
 * Semantica de parciales CUMULATIVE: reemplaza, no agrega.
 * Sin turnId en el parcial: pertenece al ultimo speechStart.
 */
export function useRealtimeTranscription(options?: {
  onSlideEvent?: (event: SlideWsEvent) => void;
  onLiveSession?: (liveSessionId: string) => void;
}) {
  const status = ref<RealtimeStatus>("idle");
  const error = ref<string | null>(null);
  const notice = ref<string | null>(null);
  // True when the WS closed with 4401 (auth/trial rejected): UI must
  // re-check the trial and route to sign-in or the expired view.
  const authBlocked = ref(false);
  const finalItems = ref<TranscriptItem[]>([]);
  const serverPaused = ref(false);
  // Versión de topic vigente reflejada del backend (eventos slide_* la portan).
  const topicVersion = ref(1);
  // Id de sesión viva del bridge (estable entre reintentos WS).
  const liveSessionId = ref<string | null>(null);

  const turnMap = ref<Map<string, TurnState>>(new Map());
  const turnOrder = ref<string[]>([]);
  let lastActiveTurnId: string | null = null;

  let client: RealtimeClient | null = null;
  let pendingSessionConfig: { topic?: string; keywords?: string[]; topicVersion?: number; palette_id?: string; audience?: string; liveSessionId?: string; resume?: boolean; displayScale?: number } | null = null;
  let audioContext: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let sourceNode: MediaStreamAudioSourceNode | null = null;
  let workletNode: AudioWorkletNode | null = null;
  let prefilter: AudioPrefilter | null = null;
  let levelTimer: ReturnType<typeof setInterval> | null = null;
  let lastVoiceAt = 0;
  let idleHintSent = false;
  let hangoverTimer: ReturnType<typeof setTimeout> | null = null;

  const prefilterEnabled = ref(readPrefilterEnabled());
  const prefilterThreshold = ref(readPrefilterThreshold());
  const prefilterLevel = ref(0);

  const partialText = computed(() => {
    const parts: string[] = [];
    for (const id of turnOrder.value) {
      const turn = turnMap.value.get(id);
      if (turn && !turn.final && turn.text.trim()) parts.push(turn.text.trim());
    }
    return parts.join(" ");
  });

  const activeTurnCount = computed(() => {
    let n = 0;
    for (const turn of turnMap.value.values()) if (!turn.final) n += 1;
    return n;
  });

  function touchTurn(turnId: string): TurnState {
    let turn = turnMap.value.get(turnId);
    if (!turn) {
      turn = { turnId, text: "", final: false, ended: false, updatedAt: Date.now() };
      turnMap.value.set(turnId, turn);
      turnOrder.value.push(turnId);
    }
    return turn;
  }

  function hasFinalTurn(turnId: string): boolean {
    return finalItems.value.some((item) => item.sessionId === turnId);
  }

  function finalizeTurn(
    turnId: string,
    text: string,
    enriched?: { cleaned?: string | null; topic?: string | null; keywords?: string[] },
  ) {
    const turn = touchTurn(turnId);
    turn.text = text;
    turn.final = true;
    turn.updatedAt = Date.now();
    if (enriched) {
      turn.cleaned = enriched.cleaned ?? null;
      turn.topic = enriched.topic ?? null;
      turn.keywords = enriched.keywords ?? [];
    }
    const clean = text.trim();
    // Dedupe opción B: si el transcript final=true ya pusheó este turnId, no duplicar.
    if (clean && !hasFinalTurn(turnId)) {
      finalItems.value.unshift({
        text: clean,
        sessionId: turnId,
        cleaned: turn.cleaned ?? enriched?.cleaned ?? null,
        topic: turn.topic ?? enriched?.topic ?? null,
        keywords: turn.keywords ?? enriched?.keywords ?? [],
      });
    }
  }

  /** Aplica un evento del servidor con semantica replace para parciales. */
  function applyServerEvent(event: ServerEvent) {
    // Identidad de sesión viva: se refleja y se reenvía (como los slide_*).
    if (event.type === "live_session") {
      if (typeof event.live_session_id === "string" && event.live_session_id) {
        liveSessionId.value = event.live_session_id;
        options?.onLiveSession?.(event.live_session_id);
      }
      if (typeof event.topicVersion === "number" && event.topicVersion > topicVersion.value) {
        topicVersion.value = event.topicVersion;
      }
      return;
    }
    // Los eventos slide_* no tocan el estado de transcripción: se reenvían.
    if (
      event.type === "slide_pending" ||
      event.type === "slide" ||
      event.type === "slide_filtered" ||
      event.type === "slide_kept" ||
      event.type === "slide_error" ||
      event.type === "slide_replaced" ||
      event.type === "slide_removed" ||
      event.type === "slide_image_updated"
    ) {
      if (typeof event.topicVersion === "number" && event.topicVersion > topicVersion.value) {
        topicVersion.value = event.topicVersion;
      }
      options?.onSlideEvent?.(event);
      return;
    }
    switch (event.type) {
      case "speechStart": {
        touchTurn(event.turnId);
        lastActiveTurnId = event.turnId;
        break;
      }
      case "transcript": {
        // CUMULATIVE = reemplaza el texto del turno, no lo agrega.
        const target = event.turnId ?? lastActiveTurnId;
        if (!target) break;
        const turn = touchTurn(target);
        turn.text = event.transcript ?? "";
        turn.final = event.final ?? false;
        turn.updatedAt = Date.now();
        if (turn.final) {
          turn.cleaned = event.cleaned ?? null;
          turn.topic = event.topic ?? null;
          turn.keywords = event.keywords ?? [];
          const clean = turn.text.trim();
          // Dedupe opción B: evita duplicar si speechComplete ya lo registró.
          if (clean && !hasFinalTurn(target))
            finalItems.value.unshift({
              text: clean,
              sessionId: target,
              cleaned: turn.cleaned,
              topic: turn.topic,
              keywords: turn.keywords,
            });
        }
        break;
      }
      case "speechEnd": {
        // Limite de turno, no texto: solo marca.
        const turn = turnMap.value.get(event.turnId);
        if (turn) turn.ended = true;
        break;
      }
      case "speechComplete": {
        finalizeTurn(event.turnId, event.transcript ?? "", {
          cleaned: event.cleaned,
          topic: event.topic,
          keywords: event.keywords,
        });
        if (lastActiveTurnId === event.turnId) lastActiveTurnId = null;
        break;
      }
      case "paused": {
        serverPaused.value = true;
        if (status.value !== "error") status.value = "paused";
        break;
      }
      case "resumed": {
        serverPaused.value = false;
        idleHintSent = false;
        lastVoiceAt = Date.now();
        if (status.value === "paused") status.value = "listening";
        break;
      }
      case "upstream_close": {
        if (event.code === 1008) {
          error.value =
            "La sesión realtime fue rechazada (1008). Revisa la clave del backend e inicia de nuevo.";
          status.value = "error";
        } else if (event.code && event.code !== 1000) {
          notice.value = `Conexión con Meta interrumpida (código ${event.code}). Reintentando…`;
        }
        break;
      }
      case "error": {
        error.value = event.message;
        status.value = "error";
        break;
      }
      default: {
        // Eventos futuros o slide_* no esperados aquí: se ignoran sin romper.
        break;
      }
    }
  }

  function markSpeaking() {
    if (status.value === "error" || status.value === "idle") return;
    if (serverPaused.value) {
      // Voz durante la pausa: el backend hara WAKE con pre-roll.
      status.value = "speaking";
      return;
    }
    status.value = "speaking";
    if (hangoverTimer) clearTimeout(hangoverTimer);
    hangoverTimer = setTimeout(() => {
      if (status.value === "speaking" && !serverPaused.value) {
        status.value = "listening";
      }
    }, SPEAKING_HANGOVER_MS);
  }

  function handleFrame(msg: FrameMessage) {
    if (!msg.pcm || !client) return;
    client.sendPcm(msg.pcm);
    const now = Date.now();
    if (msg.voiced) {
      lastVoiceAt = now;
      idleHintSent = false;
      markSpeaking();
    } else if (
      now - lastVoiceAt >= IDLE_PAUSE_HINT_MS &&
      !idleHintSent &&
      !serverPaused.value
    ) {
      idleHintSent = true;
      client.notifyIdlePause();
    }
  }

  function cleanupAudio() {
    if (hangoverTimer) {
      clearTimeout(hangoverTimer);
      hangoverTimer = null;
    }
    if (levelTimer) {
      clearInterval(levelTimer);
      levelTimer = null;
    }
    prefilterLevel.value = 0;
    try {
      workletNode?.disconnect();
    } catch {
      // Ignora errores de limpieza.
    }
    try {
      sourceNode?.disconnect();
    } catch {
      // Ignora errores de limpieza.
    }
    try {
      prefilter?.disconnect();
    } catch {
      // Ignora errores de limpieza.
    }
    workletNode = null;
    sourceNode = null;
    prefilter = null;
    if (mediaStream) {
      for (const track of mediaStream.getTracks()) track.stop();
      mediaStream = null;
    }
    if (audioContext) {
      const ctx = audioContext;
      audioContext = null;
      void ctx.close().catch(() => undefined);
    }
  }

  /** Inicia microfono + worklet + WS. Mantiene el grabador por lotes como fallback. */
  async function start(authToken?: string | null) {
    error.value = null;
    notice.value = null;
    authBlocked.value = false;
    if (status.value === "connecting" || status.value === "listening" || status.value === "speaking") return;
    if (!navigator.mediaDevices?.getUserMedia) {
      error.value =
        "Este navegador no soporta audio en vivo. Usa el grabador por lotes de abajo.";
      status.value = "error";
      return;
    }
    if (typeof AudioWorkletNode === "undefined") {
      error.value =
        "Este navegador no soporta AudioWorklet. Usa el grabador por lotes de abajo.";
      status.value = "error";
      return;
    }
    status.value = "connecting";
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch {
      error.value = "No se pudo acceder al micrófono. Revisa los permisos del navegador.";
      status.value = "error";
      return;
    }
    try {
      audioContext = new AudioContext();
      await audioContext.audioWorklet.addModule(
        new URL("../worklets/pcmCaptureProcessor.js", import.meta.url),
      );
      sourceNode = audioContext.createMediaStreamSource(mediaStream);
      workletNode = new AudioWorkletNode(audioContext, "pcm-capture-processor");
      workletNode.port.postMessage({ type: "config", threshold: WORKLET_THRESHOLD });
      workletNode.port.onmessage = (ev: MessageEvent) => {
        handleFrame(ev.data as FrameMessage);
      };
      // Prefiltro de ruido con fallback Safari: si falla, sigue sin filtro.
      try {
        prefilter = createPrefilter(audioContext);
        prefilter.setThreshold(prefilterThreshold.value);
        prefilter.setEnabled(prefilterEnabled.value);
        sourceNode.connect(prefilter.input);
        prefilter.output.connect(workletNode);
        levelTimer = setInterval(() => {
          try {
            prefilterLevel.value = prefilter?.getLevel() ?? 0;
          } catch {
            // No rompe el audio si el vumetro falla.
          }
        }, 120);
      } catch {
        prefilter = null;
        try {
          sourceNode.connect(workletNode);
        } catch {
          // Ignora errores de conexion.
        }
      }
      // Sin conexion a destination: no hay monitoreo local (evita feedback).

      lastVoiceAt = Date.now();
      idleHintSent = false;

      client = new RealtimeClient({
        onEvent: applyServerEvent,
        onOpen: () => {
          if (status.value === "connecting") status.value = "listening";
          // Flush config queued while socket was not OPEN (race after start()).
          if (pendingSessionConfig) {
            const queued = pendingSessionConfig;
            pendingSessionConfig = null;
            client?.sendSessionConfig(queued);
          }
        },
        onClose: (code) => {
          // 4401: auth/trial rejected by the backend, no retry (see client).
          if (code === 4401) {
            authBlocked.value = true;
            error.value =
              "Acceso denegado al realtime (4401): sesión inválida o prueba finalizada.";
            status.value = "error";
            return;
          }
          if (status.value !== "idle" && status.value !== "error") {
            if (code !== 1000) {
              error.value = `Conexión realtime cerrada (código ${code}).`;
              status.value = "error";
            }
          }
        },
        onError: (message) => {
          error.value = message;
          status.value = "error";
        },
      });
      client.setAuthToken(authToken ?? null);
      client.connect(IDLE_PAUSE_HINT_MS);
    } catch (err) {
      cleanupAudio();
      client?.disconnect();
      client = null;
      error.value =
        err instanceof Error
          ? err.message
          : "No se pudo iniciar la transcripción en vivo.";
      status.value = "error";
    }
  }

  function stop() {
    client?.disconnect();
    client = null;
    cleanupAudio();
    serverPaused.value = false;
    if (status.value !== "error") status.value = "idle";
  }

  function clearLive() {
    turnMap.value = new Map();
    turnOrder.value = [];
    lastActiveTurnId = null;
    finalItems.value = [];
    error.value = null;
    notice.value = null;
  }

  /** Activa/desactiva el prefiltro en vivo y persiste en localStorage. */
  function setPrefilterEnabled(value: boolean) {
    prefilterEnabled.value = value;
    try {
      localStorage.setItem(PREFILTER_ENABLED_KEY, String(value));
    } catch {
      // Persistencia opcional.
    }
    try {
      prefilter?.setEnabled(value);
    } catch {
      // No rompe si el nodo ya se limpio.
    }
  }

  /** Ajusta el umbral del gate en vivo y persiste en localStorage. */
  function setPrefilterThreshold(value: number) {
    const v = Number.isFinite(value)
      ? Math.min(0.05, Math.max(0.01, value))
      : WORKLET_THRESHOLD;
    prefilterThreshold.value = v;
    try {
      localStorage.setItem(PREFILTER_THRESHOLD_KEY, String(v));
    } catch {
      // Persistencia opcional.
    }
    try {
      prefilter?.setThreshold(v);
    } catch {
      // No rompe si el nodo ya se limpio.
    }
  }

  /** Envía topic/keywords/version/audience/sesión/escala al backend por el frame `config`. Queues until OPEN. */
  function sendSessionConfig(config: { topic?: string; keywords?: string[]; topicVersion?: number; palette_id?: string; audience?: string; liveSessionId?: string; resume?: boolean; displayScale?: number }) {
    if (client) {
      client.sendSessionConfig(config);
    } else {
      // No client yet (e.g. topic set before start()): queue for next onopen.
      pendingSessionConfig = { ...(pendingSessionConfig ?? {}), ...config };
    }
    if (typeof config.topicVersion === "number" && config.topicVersion > 0) {
      topicVersion.value = Math.floor(config.topicVersion);
    }
  }

  return {
    status,
    error,
    notice,
    authBlocked,
    partialText,
    activeTurnCount,
    finalItems,
    turnMap,
    topicVersion,
    liveSessionId,
    serverPaused,
    prefilterEnabled,
    prefilterThreshold,
    prefilterLevel,
    setPrefilterEnabled,
    setPrefilterThreshold,
    sendSessionConfig,
    start,
    stop,
    clearLive,
  };
}
