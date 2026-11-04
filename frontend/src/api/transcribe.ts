import type { TranscribeResponse } from "../types";
import { API_BASE_URL, authHeaders, throwForAuthStatus } from "./auth";
import type { GetTokenFn } from "./auth";

// Tiempo maximo de espera para la transcripcion (180 segundos).
const TIMEOUT_MS = 180_000;

/** Extrae el mensaje de error de una respuesta JSON del backend. */
async function extractDetail(response: Response): Promise<string> {
  try {
    const data = await response.json();
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    return JSON.stringify(data);
  } catch {
    try {
      const text = await response.text();
      return text || `Error ${response.status}`;
    } catch {
      return `Error ${response.status}`;
    }
  }
}

/**
 * Envia un blob de audio al backend para transcribir.
 * Usa FormData con el campo "file" y aborta a los 180 segundos.
 */
export async function transcribeAudio(
  blob: Blob,
  filename: string,
  getToken?: GetTokenFn,
  language?: string,
): Promise<TranscribeResponse> {
  const formData = new FormData();
  formData.append("file", blob, filename);
  if (language === "es" || language === "en") {
    formData.append("language", language);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/transcribe`, {
      method: "POST",
      headers: await authHeaders(getToken),
      body: formData,
      signal: controller.signal,
    });
    if (!response.ok) {
      // 401 -> sign in, 403 -> trial ended (typed, no expires_at leak).
      throwForAuthStatus(response.status);
      const detail = await extractDetail(response);
      throw new Error(`Error ${response.status}: ${detail}`);
    }
    const data = (await response.json()) as TranscribeResponse;
    return {
      text: typeof data.text === "string" ? data.text : "",
      sessionId: data.sessionId ?? null,
      audioDurationMs: data.audioDurationMs ?? null,
      turns: Array.isArray(data.turns) ? data.turns : [],
      topic: typeof data.topic === "string" ? data.topic : null,
      cleaned: typeof data.cleaned === "string" ? data.cleaned : null,
      keywords: Array.isArray(data.keywords)
        ? data.keywords.filter((k): k is string => typeof k === "string")
        : [],
    };
  } catch (error) {
    // Mensaje claro si el pedido fue abortado por timeout.
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "La transcripción tardó demasiado (180s) y fue cancelada. Prueba con un audio más corto.",
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
