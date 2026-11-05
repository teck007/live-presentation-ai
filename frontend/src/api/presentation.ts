import type {
  GenerateSlideRequest,
  GenerateSlideResponse,
  LiveSessionStatus,
  SlideItem,
  SlideLayoutId,
} from "../types";
import { API_BASE_URL, authHeaders, throwForAuthStatus } from "./auth";
import type { GetTokenFn } from "./auth";

const TIMEOUT_MS = 60_000;
const VALID_LAYOUTS: SlideLayoutId[] = [
  "title_text",
  "title_bullets",
  "text_image",
  "quote",
  "hero_cover",
  "cards_flex",
  "split_code",
  "split_media",
  "separator",
  "compare_2",
  "checklist_flex",
  "stats_flex",
  "chips_flex",
  "bullets_flex",
  "steps_flex",
  "definition_guided",
  "concept_editorial",
  "pillars_3",
  "timeline_4",
  "takeaway",
  "stat_hero",
];

function strField(value: unknown, limit: number): string | undefined {
  if (typeof value !== "string" || !value) return undefined;
  return value.slice(0, limit);
}

function strList(value: unknown, limit = 4): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string").slice(0, limit);
}

function normalizeCodigo(value: unknown): GenerateSlideResponse["codigo_matematica"] {
  if (value === null || value === undefined) return undefined;
  if (typeof value !== "object" || Array.isArray(value)) return undefined;
  const v = value as Record<string, unknown>;
  const tipo = typeof v.tipo === "string" ? v.tipo : "";
  if (tipo !== "codigo" && tipo !== "matematica") return undefined;
  const contenido = typeof v.contenido === "string" ? v.contenido : "";
  if (!contenido.trim()) return undefined;
  return {
    tipo,
    titulo: typeof v.titulo === "string" ? v.titulo.slice(0, 80) : "Ejemplo",
    contenido: contenido.slice(0, 1000),
  };
}

function normalizeResponse(data: unknown): GenerateSlideResponse {
  const d = (data ?? {}) as Partial<GenerateSlideResponse> & Record<string, unknown>;
  const layout: SlideLayoutId = VALID_LAYOUTS.includes(d.layout as SlideLayoutId)
    ? (d.layout as SlideLayoutId)
    : "title_text";
  const palette =
    d.palette && typeof d.palette === "object"
      ? (d.palette as Record<string, string>)
      : undefined;
  const bullets = Array.isArray(d.bullets)
    ? d.bullets.filter((b): b is string => typeof b === "string")
    : [];
  const listadoRaw = (d as Record<string, unknown>).listado;
  const listado = Array.isArray(listadoRaw)
    ? listadoRaw.filter((b): b is string => typeof b === "string").slice(0, 4)
    : bullets.slice(0, 4);
  const title = typeof d.title === "string" && d.title ? d.title : typeof d.titulo === "string" ? d.titulo : "";
  const text = typeof d.text === "string" && d.text ? d.text : typeof d.texto === "string" ? d.texto : "";
  return {
    layout,
    title,
    titulo: typeof d.titulo === "string" ? d.titulo : title || undefined,
    text,
    texto: typeof d.texto === "string" ? d.texto : text || undefined,
    bullets,
    listado,
    keywords: Array.isArray(d.keywords)
      ? d.keywords.filter((k): k is string => typeof k === "string").slice(0, 5)
      : [],
    filtered: d.filtered === true,
    kicker: typeof d.kicker === "string" ? d.kicker : undefined,
    subtitle: typeof d.subtitle === "string" ? d.subtitle : undefined,
    cards: Array.isArray(d.cards) ? d.cards.slice(0, 4) : undefined,
    conceptos: Array.isArray(d.conceptos) ? d.conceptos.slice(0, 4) : undefined,
    stats: Array.isArray(d.stats) ? d.stats.slice(0, 4) : undefined,
    chips: strList(d.chips),
    steps: Array.isArray(d.steps) ? d.steps.slice(0, 4) : undefined,
    code: typeof d.code === "string" ? d.code : undefined,
    code_tipo: typeof d.code_tipo === "string" ? d.code_tipo : undefined,
    code_titulo: typeof d.code_titulo === "string" ? d.code_titulo : undefined,
    codigo_matematica: normalizeCodigo(d.codigo_matematica),
    image: typeof d.image === "string" ? d.image : undefined,
    imagen_hashtag: typeof d.imagen_hashtag === "string" ? d.imagen_hashtag : undefined,
    imagen_prompt: typeof d.imagen_prompt === "string" ? d.imagen_prompt : undefined,
    explanation: strField(d.explanation ?? d.texto, 900),
    concept: strField(d.concept, 200),
    example: strField(d.example, 400),
    takeaway: strField(d.takeaway, 200),
    content_type: strField(d.content_type, 40),
    layout_reason: strField(d.layout_reason, 200),
    audience: typeof d.audience === "string" ? d.audience : undefined,
    html: typeof d.html === "string" ? d.html : undefined,
    palette_id: typeof d.palette_id === "string" ? d.palette_id : undefined,
    palette,
  };
}

function normalizeDisplayScale(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return 1.0;
  return Math.min(1.3, Math.max(0.8, value));
}

/** GET /api/presentations/live-session: resume check (Clerk auth, fail-open en dev). */
export async function fetchLiveSessionStatus(
  getToken?: GetTokenFn,
): Promise<LiveSessionStatus> {
  const response = await fetch(`${API_BASE_URL}/api/presentations/live-session`, {
    headers: await authHeaders(getToken),
  });
  if (!response.ok) {
    throwForAuthStatus(response.status);
    throw new Error(`Error ${response.status}`);
  }
  const data = (await response.json()) as Partial<LiveSessionStatus>;
  return {
    has_saved: data.has_saved === true,
    live_session_id:
      typeof data.live_session_id === "string" ? data.live_session_id : null,
    topic: typeof data.topic === "string" ? data.topic : "",
    slide_count: typeof data.slide_count === "number" ? data.slide_count : 0,
    displayScale: normalizeDisplayScale(data.displayScale),
    updated_at: typeof data.updated_at === "string" ? data.updated_at : null,
  };
}

/** Snapshot for visual restore: full ordered slides of a saved live session. */
export interface LiveSessionSlides {
  live_session_id: string;
  topic: string;
  slides: SlideItem[];
  displayScale: number;
  updated_at: string | null;
  maxTopicVersion: number;
}

/** GET /api/presentations/live-session/{id}/slides: ordered slides for Continuar. */
export async function fetchLiveSessionSlides(
  id: string,
  getToken?: GetTokenFn,
): Promise<LiveSessionSlides> {
  const response = await fetch(
    `${API_BASE_URL}/api/presentations/live-session/${encodeURIComponent(id)}/slides`,
    {
      headers: await authHeaders(getToken),
    },
  );
  if (!response.ok) {
    throwForAuthStatus(response.status);
    throw new Error(`Error ${response.status}`);
  }
  const data = (await response.json()) as {
    live_session_id?: unknown;
    topic?: unknown;
    slides?: unknown;
    displayScale?: unknown;
    updated_at?: unknown;
  };
  const rawSlides = Array.isArray(data.slides) ? data.slides : [];
  const now = Date.now();
  let maxTopicVersion = 0;
  const slides: SlideItem[] = [];
  for (const raw of rawSlides) {
    if (!raw || typeof raw !== "object") continue;
    const rec = raw as Record<string, unknown>;
    const tv = typeof rec.topicVersion === "number" ? Math.floor(rec.topicVersion) : 0;
    if (tv > maxTopicVersion) maxTopicVersion = tv;
    const slideId =
      typeof rec.id === "string" && rec.id ? rec.id : `snapshot-${slides.length}`;
    slides.push({
      ...normalizeResponse(rec),
      id: slideId,
      timestamp: now,
    });
  }
  return {
    live_session_id: typeof data.live_session_id === "string" ? data.live_session_id : id,
    topic: typeof data.topic === "string" ? data.topic : "",
    slides,
    displayScale: normalizeDisplayScale(data.displayScale),
    updated_at: typeof data.updated_at === "string" ? data.updated_at : null,
    maxTopicVersion,
  };
}

/** DELETE /api/presentations/live-session/{id}: descarta la sesión guardada. */
export async function discardLiveSession(
  id: string,
  getToken?: GetTokenFn,
): Promise<boolean> {
  const response = await fetch(
    `${API_BASE_URL}/api/presentations/live-session/${encodeURIComponent(id)}`,
    {
      method: "DELETE",
      headers: await authHeaders(getToken),
    },
  );
  if (!response.ok) {
    throwForAuthStatus(response.status);
    throw new Error(`Error ${response.status}`);
  }
  const data = (await response.json()) as { discarded?: unknown };
  return data.discarded === true;
}

/** Imagen async dedicada para la portada: texto ya pintado, parcha al llegar. */
export interface CoverImageRequest {
  topic: string;
  title: string;
  language?: string;
  palette_id?: string | null;
}

const COVER_IMAGE_TIMEOUT_MS = 45_000;

export async function generateCoverImage(
  req: CoverImageRequest,
  getToken?: GetTokenFn,
): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), COVER_IMAGE_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/presentations/cover-image`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(await authHeaders(getToken)),
      },
      body: JSON.stringify(req),
      signal: controller.signal,
    });
    if (!response.ok) return null;
    const data = (await response.json()) as { image?: unknown };
    return typeof data.image === "string" && data.image.startsWith("https://")
      ? data.image
      : null;
  } catch {
    // Fail-open: la portada de texto ya está pintada.
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** Pide al backend un slide JSON desde un turno final de transcripción. */
export async function generateSlide(
  req: GenerateSlideRequest,
  getToken?: GetTokenFn,
): Promise<GenerateSlideResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/presentations/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(await authHeaders(getToken)),
      },
      body: JSON.stringify(req),
      signal: controller.signal,
    });
    if (!response.ok) {
      // 401 -> sign in, 403 -> trial ended (typed, no expires_at leak).
      throwForAuthStatus(response.status);
      let detail = `Error ${response.status}`;
      try {
        const data = await response.json();
        const d = (data as { detail?: unknown }).detail;
        if (typeof d === "string" && d.trim()) detail = d;
      } catch {
        // Usa el status como fallback.
      }
      throw new Error(detail);
    }
    return normalizeResponse(await response.json());
  } finally {
    clearTimeout(timer);
  }
}
