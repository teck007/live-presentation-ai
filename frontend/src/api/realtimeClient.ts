import type { ServerEvent } from "../types";

// Base HTTP del backend (solo para derivar el host del WS cuando hay override).
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

function deriveWsUrl(): string {
  // En desarrollo con Vite el proxy de /ws evita CORS: usa el mismo origen
  // cuando el frontend y el backend comparten host. Si VITE_API_BASE_URL
  // apunta a otro host, deriva ws(s)://host de ahi.
  try {
    const base = new URL(API_BASE_URL, window.location.origin);
    if (base.host === window.location.host && window.location.host !== "") {
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      return `${scheme}://${window.location.host}/ws/transcribe`;
    }
    const scheme = base.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${base.host}/ws/transcribe`;
  } catch {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${window.location.host}/ws/transcribe`;
  }
}

export interface SessionConfig {
  silencePauseMs?: number;
  topic?: string;
  keywords?: string[];
  topicVersion?: number;
  palette_id?: string;
  audience?: string;
  language?: string;
  liveSessionId?: string;
  resume?: boolean;
  displayScale?: number;
}

export type RealtimeClientEvents = {
  onEvent: (event: ServerEvent) => void;
  onOpen?: () => void;
  onClose?: (code: number, reason: string) => void;
  onError?: (message: string) => void;
};

/**
 * Cliente WS realtime: PCM binario hacia arriba, eventos JSON hacia abajo.
 * No reintenta ante 1008/4401 (sesión inválida o sin auth/trial);
 * 1011/1013 con backoff.
 */
export class RealtimeClient {
  private socket: WebSocket | null = null;
  private events: RealtimeClientEvents;
  private manualClose = false;
  private retries = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingConfig: SessionConfig | null = null;
  private authToken: string | null = null;
  readonly url: string;

  constructor(events: RealtimeClientEvents, url?: string) {
    this.events = events;
    this.url = url ?? deriveWsUrl();
  }

  get connected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  /** Clerk JWT for the WS handshake (sent as ?token=, reused on retries). */
  setAuthToken(token: string | null): void {
    this.authToken = token && token.length > 0 ? token : null;
  }

  private urlWithAuth(): string {
    if (!this.authToken) return this.url;
    const sep = this.url.includes("?") ? "&" : "?";
    return `${this.url}${sep}token=${encodeURIComponent(this.authToken)}`;
  }

  connect(silencePauseMsOrOptions?: number | SessionConfig): void {
    this.manualClose = false;
    this.disconnect(1000, "reconnect");
    const options: SessionConfig =
      typeof silencePauseMsOrOptions === "number"
        ? { silencePauseMs: silencePauseMsOrOptions }
        : (silencePauseMsOrOptions ?? {});
    const socket = new WebSocket(this.urlWithAuth());
    socket.binaryType = "arraybuffer";
    this.socket = socket;
    socket.onopen = () => {
      this.retries = 0;
      const config: Record<string, unknown> = { type: "config" };
      if (options.silencePauseMs) config.silencePauseMs = options.silencePauseMs;
      if (options.topic !== undefined) config.topic = options.topic;
      if (options.keywords !== undefined) config.keywords = options.keywords;
      if (options.topicVersion !== undefined) config.topicVersion = options.topicVersion;
      if (options.palette_id !== undefined) config.palette_id = options.palette_id;
      if (options.audience !== undefined) config.audience = options.audience;
      if (options.language !== undefined) config.language = options.language;
      if (options.liveSessionId !== undefined) config.liveSessionId = options.liveSessionId;
      if (options.resume !== undefined) config.resume = options.resume;
      if (options.displayScale !== undefined) config.displayScale = options.displayScale;
      if (Object.keys(config).length > 1) {
        this.sendControl(config);
      }
      // Flush config queued before OPEN (avoids sendSessionConfig race after start()).
      if (this.pendingConfig) {
        const queued = this.pendingConfig;
        this.pendingConfig = null;
        this.sendSessionConfig(queued);
      }
      this.events.onOpen?.();
    };
    socket.onmessage = (ev: MessageEvent) => {
      if (typeof ev.data !== "string") return;
      try {
        const parsed = JSON.parse(ev.data) as ServerEvent;
        // Passthrough sin filtrar: los eventos slide_* llegan intactos al listener.
        if (parsed && typeof parsed.type === "string") {
          this.events.onEvent(parsed);
        }
      } catch {
        // Ignora frames no JSON.
      }
    };
    socket.onerror = () => {
      this.events.onError?.("Error de conexión con el servidor realtime.");
    };
    socket.onclose = (ev: CloseEvent) => {
      this.events.onClose?.(ev.code, ev.reason);
      // 1008/4401: rechazo definitivo (sesión inválida o sin auth/trial).
      // Cierre manual: tampoco reintentar.
      if (this.manualClose || ev.code === 1008 || ev.code === 4401) return;
      // 1011/1013 o cierres abnormales: backoff (max 3 intentos).
      if (this.retries < 3) {
        const delay = [1000, 2000, 4000][this.retries] ?? 4000;
        this.retries += 1;
        this.retryTimer = setTimeout(() => this.connect(options), delay);
      }
    };
  }

  sendPcm(buffer: ArrayBuffer): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(buffer);
    }
  }

  sendControl(payload: Record<string, unknown>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  notifyIdlePause(): void {
    this.sendControl({ type: "idle_pause" });
  }

  /** Envía topic/keywords/version al backend (frame `config`). Queues until OPEN. */
  sendSessionConfig(config: Omit<SessionConfig, "silencePauseMs">): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      const payload: Record<string, unknown> = { type: "config" };
      if (config.topic !== undefined) payload.topic = config.topic;
      if (config.keywords !== undefined) payload.keywords = config.keywords;
      if (config.topicVersion !== undefined) payload.topicVersion = config.topicVersion;
      if (config.palette_id !== undefined) payload.palette_id = config.palette_id;
      if (config.audience !== undefined) payload.audience = config.audience;
      if (config.language !== undefined) payload.language = config.language;
      if (config.liveSessionId !== undefined) payload.liveSessionId = config.liveSessionId;
      if (config.resume !== undefined) payload.resume = config.resume;
      if (config.displayScale !== undefined) payload.displayScale = config.displayScale;
      this.sendControl(payload);
      return;
    }
    // Socket not OPEN yet (e.g. sendSessionConfig right after start()): queue for onopen.
    this.pendingConfig = { ...(this.pendingConfig ?? {}), ...config };
  }

  disconnect(code = 1000, reason = "done"): void {
    this.manualClose = true;
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.socket) {
      try {
        this.sendControl({ type: "end" });
      } catch {
        // El socket puede estar ya cerrado.
      }
      try {
        this.socket.close(code, reason);
      } catch {
        // Ignora errores de cierre.
      }
      this.socket = null;
    }
  }
}
