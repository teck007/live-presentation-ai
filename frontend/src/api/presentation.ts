import type {
  GenerateSlideRequest,
  GenerateSlideResponse,
  SlideLayoutId,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

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

/** Pide al backend un slide JSON desde un turno final de transcripción. */
export async function generateSlide(
  req: GenerateSlideRequest,
): Promise<GenerateSlideResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/presentations/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: controller.signal,
    });
    if (!response.ok) {
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
