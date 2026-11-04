"""Realtime WS proxy: frontend <-> backend <-> Meta Muse Voice realtime ASR.

Protocol frontend<->backend:
  frontend -> backend : binary PCM signed 16-bit LE mono 24kHz (~80ms frames)
  frontend -> backend : JSON control {"type": "idle_pause"} (hint) | {"type": "end"}
  backend  -> frontend: Meta events forwarded as-is (speechStart/transcript/
                             speechEnd/speechComplete) plus control events
                             {"type":"paused"} / {"type":"resumed"} /
                             {"type":"upstream_close","code":int} /
                             {"type":"error","message":str}

Silence state machine (backend is authoritative):
  STREAMING: forward PCM to Meta. Short trailing silence (< pause threshold)
             still forwards PCM silence so Meta can emit speechComplete.
  PAUSED (prolonged silence >= REALTIME_SILENCE_PAUSE_MS, default 15000ms):
             send {"type":"endStream"} upstream, drain pending events, close
             upstream 1000. front<->backend socket stays open. Upstream gets
             ~0 bytes while paused. Keep a PRE_ROLL_MS (default 500ms) ring
             buffer; on WAKE (150-250ms confirmed voice) open a NEW upstream
             session, send pre-roll first, then resume streaming.
"""
import asyncio
import json
import logging
import math
import os
import struct
import time
import uuid
from collections import deque

from fastapi import WebSocket, WebSocketDisconnect

from backend.presentation_api.utils.topic_cleaner import is_relevant

logger = logging.getLogger("realtime_proxy")


_latency_store = None


def _latency():
    """Process-wide latency baseline, lazy: top-level would cycle via presentation_api __init__."""
    global _latency_store
    if _latency_store is None:
        from backend.presentation_api.utils.latency import baseline as _b

        _latency_store = _b
    return _latency_store

META_REALTIME_URL_DEFAULT = "wss://api.meta.ai/v1/asr/realtime"
ASR_MODEL_DEFAULT = "muse-voice-transcribe-1.0"

SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2
FRAME_BYTES = 3840  # 80ms @ 24kHz mono int16
FRAME_S = FRAME_BYTES / (SAMPLE_RATE * BYTES_PER_SAMPLE)  # 0.08s per frame
MAX_BACKLOG_MS = 5000
MAX_QUEUE_FRAMES = (MAX_BACKLOG_MS * SAMPLE_RATE * BYTES_PER_SAMPLE) // 1000 // FRAME_BYTES  # ~62
DRAIN_TIMEOUT_S = 4.0
WATCHDOG_INTERVAL_S = 0.2
# 150-250ms confirmed voice to wake: with 80ms frames -> 3 voiced frames.
WAKE_VOICED_FRAMES = 3


def get_config() -> dict:
    try:
        silence_pause_ms = int(os.getenv("REALTIME_SILENCE_PAUSE_MS", "15000"))
    except ValueError:
        silence_pause_ms = 15000
    silence_pause_ms = max(5000, min(60000, silence_pause_ms))
    try:
        pre_roll_ms = int(os.getenv("REALTIME_PRE_ROLL_MS", "500"))
    except ValueError:
        pre_roll_ms = 500
    pre_roll_ms = max(0, min(2000, pre_roll_ms))
    try:
        vad_threshold = float(os.getenv("REALTIME_VAD_THRESHOLD", "0.02"))
    except ValueError:
        vad_threshold = 0.02
    try:
        slide_window_s = float(os.getenv("SLIDE_WINDOW_S", "10"))
    except ValueError:
        slide_window_s = 10.0
    slide_window_s = max(0.0, min(120.0, slide_window_s))
    try:
        window_target_words = int(os.getenv("WINDOW_TARGET_WORDS", "18"))
    except ValueError:
        window_target_words = 18
    window_target_words = max(5, min(60, window_target_words))
    try:
        window_max_voice_s = float(os.getenv("WINDOW_MAX_VOICE_S", "12.0"))
    except ValueError:
        window_max_voice_s = 12.0
    window_max_voice_s = max(5.0, min(60.0, window_max_voice_s))
    try:
        window_min_content_words = int(os.getenv("WINDOW_MIN_CONTENT_WORDS", "5"))
    except ValueError:
        window_min_content_words = 5
    window_min_content_words = max(1, min(20, window_min_content_words))
    try:
        window_grace_s = float(os.getenv("WINDOW_GRACE_S", "2.5"))
    except ValueError:
        window_grace_s = 2.5
    window_grace_s = max(0.0, min(5.0, window_grace_s))
    try:
        slide_context_chars = int(os.getenv("SLIDE_CONTEXT_CHARS", "600"))
    except ValueError:
        slide_context_chars = 600
    slide_context_chars = max(0, min(4000, slide_context_chars))
    return {
        "silence_pause_ms": silence_pause_ms,
        "pre_roll_ms": pre_roll_ms,
        "vad_threshold": vad_threshold,
        "slide_window_s": slide_window_s,
        "window_target_words": window_target_words,
        "window_max_voice_s": window_max_voice_s,
        "window_min_content_words": window_min_content_words,
        "window_grace_s": window_grace_s,
        "window_duty_cycle": os.getenv("WINDOW_DUTY_CYCLE", "").strip(),
        "slide_context_chars": slide_context_chars,
        "model": os.getenv("ASR_MODEL", ASR_MODEL_DEFAULT).strip() or ASR_MODEL_DEFAULT,
        "url": os.getenv("META_REALTIME_URL", META_REALTIME_URL_DEFAULT).strip()
        or META_REALTIME_URL_DEFAULT,
    }


def get_api_key() -> str:
    return os.getenv("MODEL_API_KEY", "").strip()


def frame_rms(frame: bytes) -> float:
    """RMS normalizado 0..1 de un frame PCM16LE. Silencio exacto -> 0.0."""
    if not frame:
        return 0.0
    n = len(frame) // 2
    if n == 0:
        return 0.0
    fmt = f"<{n}h"
    try:
        samples = struct.unpack(fmt, frame[: n * 2])
    except struct.error:
        return 0.0
    acc = 0.0
    for s in samples:
        v = s / 32768.0
        acc += v * v
    return math.sqrt(acc / n)


def is_voiced(frame: bytes, threshold: float) -> bool:
    return frame_rms(frame) >= threshold


def enrich_event(obj: dict) -> dict:
    """Add cleaned/topic/keywords to final transcript events (additive only)."""
    try:
        # Lazy import: top-level would cycle via backend.presentation_api.__init__
        # (controllers.transcription imports handle_frontend_socket from here).
        from backend.presentation_api.utils.topic_cleaner import analyze_topic

        t = obj.get("type")
        if t == "speechComplete":
            raw = obj.get("transcript") or ""
            if isinstance(raw, str) and raw.strip():
                a = analyze_topic(raw)
                obj = {**obj, "cleaned": a["cleaned"], "topic": a["topic"], "keywords": a["keywords"]}
        elif t == "transcript" and obj.get("final") is True:
            raw = obj.get("transcript") or ""
            if isinstance(raw, str) and raw.strip():
                a = analyze_topic(raw)
                obj = {**obj, "cleaned": a["cleaned"], "topic": a["topic"], "keywords": a["keywords"]}
    except Exception:  # noqa: BLE001
        pass
    return obj


def build_handshake(api_key: str, model: str) -> str:
    return json.dumps(
        {
            "authorization": {"accessToken": f"Bearer {api_key}"},
            "audioEncoding": "PCM_24KHZ",
            "model": model,
            "mode": "ENDPOINTING",
            "languageBias": ["Spanish"],
            "partialMode": "CUMULATIVE",
            "emitAudioProgress": False,
        }
    )


class RealtimeBridge:
    """Puente de una sesion frontend<->Meta con maquina de pausa por silencio."""

    def __init__(
        self,
        frontend: WebSocket,
        config: dict,
        user_id: str = "dev-local",
        live_session_id: str | None = None,
    ):
        self.frontend = frontend
        self.config = config
        self.send_lock = asyncio.Lock()
        # Serialize read-patch-commit of the shared session entry so two
        # concurrent slide tasks never clobber each other (seq guard is the
        # second line of defense inside the store itself).
        self._session_lock = asyncio.Lock()
        self.upstream = None
        self.upstream_session_id: str | None = None
        self.streaming = False  # True = upstream abierto y recibiendo audio
        self.closed = False
        self.audio_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_FRAMES)
        self.pre_roll = deque()  # bytes, cap PRE_ROLL_MS
        self.pre_roll_bytes = 0
        self.pre_roll_cap = (
            config["pre_roll_ms"] * SAMPLE_RATE * BYTES_PER_SAMPLE // 1000
        )
        self.last_voice_at = asyncio.get_event_loop().time()
        self.wake_counter = 0
        self.consumer_task: asyncio.Task | None = None
        self.watchdog_task: asyncio.Task | None = None
        self.relay_task: asyncio.Task | None = None
        # Clerk identity: never trust a frontend-provided user_id; the
        # controller passes the verified sub (dev-local fail-open in dev).
        self.user_id = str(user_id or "dev-local").strip() or "dev-local"
        from backend.presentation_api.utils import live_sessions as _live

        self.live_session_id = (
            str(live_session_id or "").strip() or _live.new_session_id()
        )
        # U1 ws-llm-slides-async: per-connection slide-task state.
        self.seq_counter = 0
        self.seen_turnIds: set[str] = set()
        self.pending_tasks: dict[str, asyncio.Task] = {}
        self.slide_semaphore = asyncio.Semaphore(2)
        # Semáforo propio de imágenes (vivo progresivo): no compite con slides.
        self.image_semaphore = asyncio.Semaphore(3)
        self.image_tasks: set[asyncio.Task] = set()
        self.current_topic_version = 1
        self.current_topic = ""
        self.current_keywords: list[str] = []
        self.current_audience = "general"
        self.last_layout: str | None = None
        self.opened_versions: set[int] = set()
        self.presentation_palette: dict | None = None
        self.presentation_palette_id: str | None = None
        # Resume: adopt stored session state so WS retries keep the same
        # live_session_id, monotonic seq and no repeated hero opening.
        try:
            entry = _live.get_or_create(self.user_id, self.live_session_id)
            self.live_session_id = str(entry.get("live_session_id") or self.live_session_id)
            self.current_topic = str(entry.get("topic") or "")
            self.current_audience = str(entry.get("audience") or "general") or "general"
            self.current_topic_version = int(entry.get("topic_version") or 1)
            if entry.get("palette") is not None:
                self.presentation_palette = entry.get("palette")
                self.presentation_palette_id = entry.get("palette_id")
            try:
                self.seq_counter = int(entry.get("last_recorded_seq") or 0)
            except (TypeError, ValueError):
                self.seq_counter = 0
            if entry.get("current_slide") or entry.get("history"):
                self.opened_versions.add(self.current_topic_version)
            current = entry.get("current_slide")
            if isinstance(current, dict) and current:
                self.last_layout = str(current.get("layout") or "") or None
                self.last_slide_summary = {
                    "titulo": str(current.get("titulo") or current.get("title") or "")[:120],
                    "resumen": str(current.get("texto") or current.get("text") or "")[:300],
                }
        except Exception:  # noqa: BLE001 - store never breaks the bridge
            pass
        # Jev gate + word-count windows: forced eval without cutting PCM.
        self.vad_window_s = 0.0
        self.window_seq = 0
        self.active_turn_id: str | None = None
        self.partial_by_turn: dict[str, str] = {}
        self.last_forced_text: dict[str, str] = {}
        self.window_grace_until: float = 0.0
        self.slide_context_tail = ""
        self.last_slide_summary: dict = {"titulo": "", "resumen": ""}
        self.window_cycle_start = asyncio.get_event_loop().time()

    async def send_front(self, obj: dict) -> None:
        async with self.send_lock:
            await self.frontend.send_text(json.dumps(obj))

    # --- U1 ws-llm-slides-async: non-blocking slide tasks ---

    def _window_enabled(self) -> bool:
        try:
            return float(self.config.get("slide_window_s") or 0) > 0
        except (TypeError, ValueError):
            return False

    def _duty_active(self, now: float) -> bool:
        """WINDOW_DUTY_CYCLE: "" always on; "X/Y" active X sec of every Y sec."""
        spec = str(self.config.get("window_duty_cycle") or "").strip()
        if not spec or spec == "0":
            return True
        try:
            if "/" in spec:
                active_s, period_s = spec.split("/", 1)
                active = float(active_s)
                period = float(period_s)
                if active <= 0 or period <= 0:
                    return True
                return ((now - self.window_cycle_start) % period) < active
            duty = float(spec)
            if duty <= 0 or duty > 1:
                return True
            return (now % 60.0) < duty * 60.0
        except (TypeError, ValueError):
            return True

    def _note_meta_event(self, event: dict) -> None:
        """Track partial transcripts per turn for window-forced evaluation."""
        t = event.get("type")
        if t == "speechStart":
            turn_id = event.get("turnId")
            if turn_id:
                self.active_turn_id = turn_id
                self.partial_by_turn.setdefault(turn_id, "")
                self.last_forced_text.setdefault(turn_id, "")
                self.window_grace_until = 0.0
        elif t == "transcript":
            turn_id = event.get("turnId") or self.active_turn_id
            if turn_id:
                if event.get("turnId"):
                    self.active_turn_id = turn_id
                text = event.get("transcript")
                if isinstance(text, str):
                    self.partial_by_turn[turn_id] = text
        elif t == "speechComplete":
            turn_id = event.get("turnId")
            if turn_id:
                # Drop the partial; last_forced_text stays until
                # handle_speech_complete decides tail vs filtered.
                self.partial_by_turn.pop(turn_id, None)
                if self.active_turn_id == turn_id:
                    self.active_turn_id = None

    def _append_context(self, transcript: str) -> None:
        """Rolling tail of recent transcripts for update fusion."""
        try:
            limit = int(self.config.get("slide_context_chars") or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit <= 0:
            return
        tail = (self.slide_context_tail + "\n" + (transcript or "").strip()).strip()
        self.slide_context_tail = tail[-limit:]

    async def _spawn_gated_slide(
        self,
        turn_id: str,
        seq: int,
        version: int,
        transcript: str,
        topic: str,
        keywords: list,
        is_regen: bool,
        is_opening: bool,
    ) -> None:
        try:
            await self.send_front(
                {"type": "slide_pending", "turnId": turn_id,
                 "seq": seq, "topicVersion": version}
            )
        except Exception:  # noqa: BLE001
            return
        task = asyncio.create_task(
            self._run_gated_slide(turn_id, seq, version, transcript, topic, list(keywords), is_regen, is_opening)
        )
        key = turn_id if not is_regen else f"{turn_id}#regen{seq}"
        self.pending_tasks[key] = task

        def _drop(_t: asyncio.Task, key: str = key, expected: asyncio.Task = task) -> None:
            if self.pending_tasks.get(key) is expected:
                self.pending_tasks.pop(key, None)

        task.add_done_callback(_drop)

    async def _run_gated_slide(
        self,
        turn_id: str,
        seq: int,
        version: int,
        transcript: str,
        topic: str,
        keywords: list,
        is_regen: bool = False,
        is_opening: bool = False,
    ) -> None:
        """Jev gate (off the relay loop) then branch keep/update/new.

        keep -> slide_kept terminal (no paint, order advances).
        update -> fused context regen (slide_replaced terminal with the
                  real previous slide id in ``replaces``).
        new -> regular slide task. Fail-open is conservative (keep with a
        current slide, new without one) so the live flow never stalls.
        """
        # Stale version drops unchanged: nunca guarda ni decide para version vieja.
        if version != self.current_topic_version:
            return
        prev_tail = self.slide_context_tail
        self._append_context(transcript)
        try:
            from backend.presentation_api.utils import live_sessions as _live

            _entry = _live.get_or_create(self.user_id, self.live_session_id)
            # Registra ANTES de decidir: si dos tareas Jev corren en paralelo,
            # la segunda ya ve el texto de la primera aunque su slide aun no
            # se haya commiteado (mitiga la condicion de carrera).
            try:
                _live.append_transcript(_entry, turn_id, seq, transcript)
            except Exception:  # noqa: BLE001 - store never breaks the gate
                pass
            slide_actual, historial = _live.build_jev_context(_entry)
            transcripcion_reciente = _live.build_transcript_context(
                _entry, exclude_turn_id=turn_id)
        except Exception:  # noqa: BLE001 - store never breaks the gate
            slide_actual, historial = dict(self.last_slide_summary or {}), []
            transcripcion_reciente = []
        has_base = bool(slide_actual)
        jev_start = time.monotonic()
        try:
            from backend.presentation_api.utils import jev_client as jev_mod

            decision = await asyncio.to_thread(
                jev_mod.decide_slide_action,
                topic,
                list(keywords),
                self.current_audience,
                transcript,
                slide_actual,
                historial,
                transcripcion_reciente,
            )
        except Exception:  # noqa: BLE001
            decision = {"relevant": True,
                        "action": "keep" if has_base else "new",
                        "reason": "fail-open: gate-error", "raw": {}}
        jev_elapsed = time.monotonic() - jev_start
        if not isinstance(decision, dict):
            decision = {"relevant": True,
                        "action": "keep" if has_base else "new",
                        "reason": "fail-open: bad-decision", "raw": {}}
        # Stale version drops unchanged: never emit for an old version.
        if version != self.current_topic_version:
            return
        action = str(decision.get("action") or "new").strip().lower()
        if action not in ("keep", "update", "new"):
            action = "keep" if has_base else "new"
        if decision.get("relevant", True) is False:
            action = "keep"
        # Explicit update stands even without a base slide: update fuses
        # whatever context exists. Only fail-open paths are conservative
        # (keep with base, new without).
        if action == "keep":
            try:
                await self.send_front(
                    {"type": "slide_kept", "turnId": turn_id,
                     "seq": seq, "topicVersion": version}
                )
            except Exception:  # noqa: BLE001
                pass
            print(
                f"[bridge] seq={seq} version={version} jev_action=keep layout=kept "
                f"jev={jev_elapsed:.2f}s",
                flush=True,
            )
            return
        if action == "update":
            try:
                limit = int(self.config.get("slide_context_chars") or 0)
            except (TypeError, ValueError):
                limit = 0
            fused = (prev_tail + "\n" + transcript).strip()
            if limit > 0:
                fused = fused[-limit:]
            try:
                from backend.presentation_api.utils import live_sessions as _live2

                _e = _live2.get_or_create(self.user_id, self.live_session_id)
                _cur = _e.get("current_slide")
                replaces = None
                target_slide_id = None
                if isinstance(_cur, dict) and _cur:
                    _cid = str(_e.get("current_slide_id") or "")
                    if _cid:
                        target_slide_id = _cid
                        replaces = _cid.rsplit("-", 1)[0] if "-" in _cid else _cid
            except Exception:  # noqa: BLE001
                replaces, target_slide_id = None, None
            await self._run_slide_task(turn_id, seq, version, fused, topic,
                                       keywords, True, is_opening,
                                       kind="update", replaces=replaces,
                                       target_slide_id=target_slide_id)
            print(
                f"[bridge] seq={seq} version={version} jev_action=update "
                f"layout={self.last_layout or 'unknown'} jev={jev_elapsed:.2f}s",
                flush=True,
            )
            return
        await self._run_slide_task(turn_id, seq, version, transcript, topic,
                                   keywords, is_regen, is_opening, kind="new")
        print(
            f"[bridge] seq={seq} version={version} jev_action=new "
            f"layout={self.last_layout or 'unknown'} jev={jev_elapsed:.2f}s",
            flush=True,
        )

    def _window_params(self) -> tuple[int, float, int, float]:
        """Clamped (target_words, max_voice_s, min_content_words, grace_s)."""
        try:
            target = int(self.config.get("window_target_words") or 18)
        except (TypeError, ValueError):
            target = 18
        try:
            max_voice = float(self.config.get("window_max_voice_s") or 12.0)
        except (TypeError, ValueError):
            max_voice = 12.0
        try:
            min_content = int(self.config.get("window_min_content_words") or 5)
        except (TypeError, ValueError):
            min_content = 5
        try:
            grace = float(self.config.get("window_grace_s") or 0.0)
        except (TypeError, ValueError):
            grace = 0.0
        return (
            max(5, min(60, target)),
            max(5.0, min(60.0, max_voice)),
            max(1, min(20, min_content)),
            max(0.0, min(5.0, grace)),
        )

    @staticmethod
    def _delta_content_words(delta: str) -> tuple[int, int]:
        """Return (total words, content words) excluding filler words."""
        try:
            from backend.presentation_api.utils.topic_cleaner import _FILLER_WORDS
        except Exception:  # noqa: BLE001
            _FILLER_WORDS = frozenset()
        tokens = delta.split()
        content = 0
        for tok in tokens:
            word = tok.lower().strip(".,!?;:…\"'()[]¿¡")
            if word and word not in _FILLER_WORDS:
                content += 1
        return len(tokens), content

    async def _emit_window_slide(self, turn_id: str, full: str, delta: str) -> None:
        """Emit one window slide carrying only the not-yet-sent delta."""
        self.vad_window_s = 0.0
        self.window_grace_until = 0.0
        self.window_seq += 1
        win_turn = f"{turn_id}#w{self.window_seq}"
        self.seen_turnIds.add(win_turn)
        try:
            _latency().record_complete(win_turn, time.monotonic())
        except Exception:  # noqa: BLE001 - instrumentation never breaks the pipeline
            pass
        self.last_forced_text[turn_id] = full
        self.seq_counter += 1
        seq = self.seq_counter
        version = self.current_topic_version
        is_opening = seq == 1 or version not in self.opened_versions
        self.opened_versions.add(version)
        topic = self.current_topic or ""
        keywords = list(self.current_keywords or [])[:10]
        await self._spawn_gated_slide(win_turn, seq, version, delta, topic,
                                      keywords, False, is_opening)
        print(
            f"[window] turn={turn_id} full={len(full)} "
            f"delta={len(delta)} words={len(delta.split())} seq={seq}",
            flush=True,
        )

    async def _maybe_force_window(self) -> None:
        """Word-count window: force eval reusing the Jev gate + slide task.

        Never cuts the PCM stream; Meta endpointing stays primary. Each
        window sends only the delta since the previous window via a synthetic
        ``{turnId}#w{n}`` id, so a later speechComplete for the original turn
        only needs to evaluate the tail.
        """
        target, max_voice, min_content, grace = self._window_params()
        try:
            legacy_window = float(self.config.get("slide_window_s") or 0)
        except (TypeError, ValueError):
            legacy_window = 0.0
        turn_id = self.active_turn_id
        full = (self.partial_by_turn.get(turn_id) or "").strip() if turn_id else ""
        if not turn_id or not full:
            return
        sent = self.last_forced_text.get(turn_id, "")
        if sent and full.startswith(sent):
            delta = full[len(sent):].strip()
        else:
            delta = full.strip()
        if not delta:
            return
        w, content = self._delta_content_words(delta)
        now = asyncio.get_event_loop().time()
        if content < min_content:
            # Keep accumulating; avoid unbounded growth by forcing an
            # attempt anyway once voice time doubles the slow-speech cap.
            if self.vad_window_s < max_voice * 2:
                return
            await self._emit_window_slide(turn_id, full, delta)
            return
        if w >= target and delta.endswith((".", "?", "!", ";", ":", "…")):
            await self._emit_window_slide(turn_id, full, delta)
            return
        if self.vad_window_s >= max_voice or (
            legacy_window > 0 and self.vad_window_s >= legacy_window
        ):
            # Slow-speech cap (or legacy SLIDE_WINDOW_S compat): emit even
            # when the word target has not been reached yet.
            await self._emit_window_slide(turn_id, full, delta)
            return
        if w >= target:
            if not self.window_grace_until:
                self.window_grace_until = now + grace
                return
            if now >= self.window_grace_until:
                await self._emit_window_slide(turn_id, full, delta)
            return

    async def handle_speech_complete(self, event: dict) -> None:
        """Dedupe by turnId, assign arrival-order seq, emit pending, spawn task.

        Topic filter rule: topic comes ONLY from session config
        (``current_topic``); event topic is ignored for filtering.
        Every non-empty transcript goes to the LLM with that topic —
        the model alone decides ``relevant`` semantically.
        Only empty/short transcripts (<3 chars) short-circuit to
        ``slide_filtered`` without calling the LLM.

        Turns that already produced window slides only evaluate the tail
        (the transcript suffix not covered by any window); an empty tail
        short-circuits to ``slide_filtered`` so the full text is never
        evaluated twice.
        """
        turn_id = event.get("turnId")
        if not turn_id or turn_id in self.seen_turnIds:
            return
        try:
            _latency().record_complete(turn_id, time.monotonic())
        except Exception:  # noqa: BLE001 - instrumentation never breaks the pipeline
            pass
        transcript = event.get("transcript") or ""
        if not isinstance(transcript, str):
            transcript = ""
        if turn_id in self.last_forced_text:
            sent = self.last_forced_text.get(turn_id) or ""
            full = transcript
            if sent and full.startswith(sent):
                tail = full[len(sent):].strip()
            else:
                tail = full.strip()
            self.partial_by_turn.pop(turn_id, None)
            self.last_forced_text.pop(turn_id, None)
            if self.active_turn_id == turn_id:
                self.active_turn_id = None
            self.seen_turnIds.add(turn_id)
            self.seq_counter += 1
            seq = self.seq_counter
            version = self.current_topic_version
            is_opening = seq == 1 or version not in self.opened_versions
            self.opened_versions.add(version)
            if len(tail) < 3 or len(tail.split()) < 3:
                try:
                    await self.send_front(
                        {"type": "slide_filtered", "turnId": turn_id,
                         "seq": seq, "topicVersion": version}
                    )
                except Exception:  # noqa: BLE001
                    pass
                try:
                    _latency().mark_filtered(turn_id)
                except Exception:  # noqa: BLE001
                    pass
                return
            topic = self.current_topic or ""
            event_keywords = event.get("keywords") or []
            merged: list[str] = list(self.current_keywords or [])
            for kw in event_keywords:
                if kw not in merged:
                    merged.append(kw)
            keywords = merged[:10]
            tail_turn = f"{turn_id}#tail"
            self.seen_turnIds.add(tail_turn)
            try:
                _latency().record_complete(tail_turn, time.monotonic())
            except Exception:  # noqa: BLE001
                pass
            await self._spawn_gated_slide(tail_turn, seq, version, tail, topic,
                                          list(keywords), False, is_opening)
            return
        self.seen_turnIds.add(turn_id)
        self.seq_counter += 1
        seq = self.seq_counter
        version = self.current_topic_version
        is_opening = seq == 1 or version not in self.opened_versions
        self.opened_versions.add(version)
        topic = self.current_topic or ""
        event_keywords = event.get("keywords") or []
        merged = list(self.current_keywords or [])
        for kw in event_keywords:
            if kw not in merged:
                merged.append(kw)
        keywords = merged[:10]
        if len(transcript.strip()) < 3:
            try:
                await self.send_front(
                    {"type": "slide_filtered", "turnId": turn_id,
                     "seq": seq, "topicVersion": version}
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                _latency().mark_filtered(turn_id)
            except Exception:  # noqa: BLE001
                pass
            return
        await self._spawn_gated_slide(turn_id, seq, version, transcript, topic,
                                      list(keywords), False, is_opening)

    async def request_regen(
        self, turn_id: str, transcript: str, topic: str = "",
        keywords: list | None = None,
    ) -> bool:
        """Regen de un turno ya visto: nuevo seq, terminal slide_replaced/removed."""
        if not turn_id or turn_id not in self.seen_turnIds:
            return False
        self.seq_counter += 1
        seq = self.seq_counter
        version = self.current_topic_version
        is_opening = seq == 1 or version not in self.opened_versions
        self.opened_versions.add(version)
        task = asyncio.create_task(
            self._run_slide_task(
                turn_id, seq, version, transcript,
                topic or self.current_topic,
                list(keywords) if keywords is not None else list(self.current_keywords),
                True,
                is_opening,
                kind="regen",
                replaces=turn_id,
            )
        )
        self.pending_tasks[f"{turn_id}#regen{seq}"] = task

        def _drop_regen(_t: asyncio.Task, key: str = f"{turn_id}#regen{seq}") -> None:
            self.pending_tasks.pop(key, None)

        task.add_done_callback(_drop_regen)
        return True

    def _build_slide_event(
        self,
        event_type: str,
        turn_id: str,
        seq: int,
        version: int,
        slide: dict,
        layout: str,
        html_snippet: str,
        keywords: list,
        extra: dict | None = None,
    ) -> dict:
        """Full slide event payload shared by slide/slide_replaced."""

        def _str_list(value: object, limit: int = 4) -> list:
            if not isinstance(value, list):
                return []
            return [str(v) for v in value if isinstance(v, str) and str(v).strip()][:limit]

        cm = slide.get("codigo_matematica") if isinstance(slide.get("codigo_matematica"), dict) else None
        event = {
            "type": event_type,
            "turnId": turn_id,
            "seq": seq,
            "topicVersion": version,
            "layout": layout,
            "title": str(slide.get("title") or ""),
            "titulo": str(slide.get("titulo") or slide.get("title") or ""),
            "text": str(slide.get("text") or ""),
            "texto": str(slide.get("texto") or slide.get("text") or ""),
            "bullets": _str_list(slide.get("bullets")),
            "listado": _str_list(slide.get("listado") if isinstance(slide.get("listado"), list) else slide.get("bullets")),
            "keywords": _str_list(slide.get("keywords") or keywords, 5),
            "kicker": str(slide.get("kicker") or ""),
            "subtitle": str(slide.get("subtitle") or ""),
            "cards": list(slide.get("cards") or [])[:4] if isinstance(slide.get("cards"), list) else [],
            "conceptos": list(slide.get("conceptos") or [])[:4] if isinstance(slide.get("conceptos"), list) else [],
            "stats": list(slide.get("stats") or [])[:4] if isinstance(slide.get("stats"), list) else [],
            "chips": _str_list(slide.get("chips")),
            "steps": list(slide.get("steps") or [])[:4] if isinstance(slide.get("steps"), list) else [],
            "code": str(slide.get("code") or ""),
            "code_tipo": str(slide.get("code_tipo") or ""),
            "code_titulo": str(slide.get("code_titulo") or ""),
            "codigo_matematica": cm,
            "image": str(slide.get("image") or ""),
            "imagen_hashtag": str(slide.get("imagen_hashtag") or ""),
            "imagen_prompt": str(slide.get("imagen_prompt") or ""),
            "explanation": str(slide.get("explanation") or ""),
            "concept": str(slide.get("concept") or ""),
            "example": str(slide.get("example") or ""),
            "takeaway": str(slide.get("takeaway") or ""),
            "content_type": str(slide.get("content_type") or ""),
            "layout_reason": str(slide.get("layout_reason") or ""),
            "audience": self.current_audience,
            "html": html_snippet,
            "palette_id": self.presentation_palette_id or "",
            "palette": self.presentation_palette,
        }
        if extra:
            event.update(extra)
        return event

    def _commit_slide_store(self, kind: str, slide: dict, seq: int, slide_id: str) -> None:
        """Persist to live_sessions only after successful emit (seq-guarded)."""
        try:
            from backend.presentation_api.utils import live_sessions as _live

            entry = _live.get_or_create(self.user_id, self.live_session_id)
            if kind == "new":
                _live.record_new(entry, slide, seq, slide_id,
                                 self.current_topic_version)
            else:
                _live.record_update(entry, slide, seq, slide_id)
            self._sync_summary_from_store(entry)
        except Exception:  # noqa: BLE001 - store never breaks the live flow
            pass

    def _sync_summary_from_store(self, entry: dict) -> None:
        """Keep bridge-level Jev summary/palette in sync with the store entry."""
        try:
            current = entry.get("current_slide")
            if isinstance(current, dict) and current:
                self.last_layout = str(current.get("layout") or "") or self.last_layout
                self.last_slide_summary = {
                    "titulo": str(current.get("titulo") or current.get("title") or "")[:120],
                    "resumen": str(current.get("texto") or current.get("text") or "")[:300],
                }
            if entry.get("palette") is not None and self.presentation_palette is None:
                self.presentation_palette = entry.get("palette")
                self.presentation_palette_id = entry.get("palette_id")
        except Exception:  # noqa: BLE001
            pass

    async def _run_slide_task(
        self,
        turn_id: str,
        seq: int,
        version: int,
        transcript: str,
        topic: str,
        keywords: list,
        is_regen: bool = False,
        is_opening: bool = False,
        kind: str = "new",
        replaces: str | None = None,
        target_slide_id: str | None = None,
    ) -> None:
        try:
            async with self.slide_semaphore:
                from backend.presentation_api.utils import llm_client as llm_mod

                try:
                    _latency().record_llm_start(turn_id, time.monotonic())
                except Exception:  # noqa: BLE001
                    pass
                try:
                    from backend.presentation_api.utils import live_sessions as _live_llm

                    _entry_llm = _live_llm.get_or_create(self.user_id, self.live_session_id)
                    _hist = list(_entry_llm.get("history") or [])[-5:]
                    _cur = _entry_llm.get("current_slide")
                    previous_slides = list(_hist)
                    if isinstance(_cur, dict) and _cur:
                        previous_slides.append(_live_llm.summarize_slide(_cur))
                except Exception:  # noqa: BLE001
                    previous_slides = []
                slide = await asyncio.to_thread(
                    llm_mod.generate_slide,
                    transcript,
                    topic,
                    keywords,
                    self.current_audience,
                    self.last_layout,
                    is_opening,
                    previous_slides,
                )
                try:
                    _latency().record_llm_end(turn_id, time.monotonic())
                except Exception:  # noqa: BLE001
                    pass
                # Lazy palette: one random per bridge, reused for all tasks/regens.
                if self.presentation_palette is None:
                    from backend.presentation_api.utils.palettes import resolve_palette

                    self.presentation_palette = resolve_palette(None)
                    self.presentation_palette_id = str(
                        self.presentation_palette.get("id", "") or ""
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            if version != self.current_topic_version:
                return
            try:
                await self.send_front(
                    {"type": "slide_error", "turnId": turn_id, "seq": seq,
                     "topicVersion": version, "message": str(exc)[:300]}
                )
            except Exception:  # noqa: BLE001
                pass
            return
        # Pre-emit version check: stale results never emit.
        if version != self.current_topic_version:
            return
        try:
            if isinstance(slide, dict) and (
                slide.get("filtered") is True or slide.get("relevant") is False
            ):
                try:
                    _latency().mark_filtered(turn_id)
                except Exception:  # noqa: BLE001
                    pass
                await self.send_front(
                    {"type": "slide_removed" if is_regen else "slide_filtered",
                     "turnId": turn_id, "seq": seq, "topicVersion": version}
                )
                if is_regen:
                    # Regen filtered: drop the matching current slide from the
                    # store so later tasks never patch a removed ghost.
                    try:
                        from backend.presentation_api.utils import live_sessions as _live

                        _entry = _live.get_or_create(self.user_id, self.live_session_id)
                        _cid = str(_entry.get("current_slide_id") or "")
                        if _cid and _cid.startswith(f"{turn_id}-"):
                            _live.archive_current(_entry)
                            self._sync_summary_from_store(_entry)
                    except Exception:  # noqa: BLE001
                        pass
                return
            layout = (slide.get("layout") if isinstance(slide, dict) else None) or "title_text"
            from backend.presentation_api.utils.slide_designs import VALID_LAYOUTS

            if layout not in VALID_LAYOUTS:
                layout = "title_text"

            try:
                from backend.presentation_api.utils.slide_designs import (
                    render_slide_html,
                    validate_slide,
                )

                validated = validate_slide(slide if isinstance(slide, dict) else {}, is_opening=is_opening)
                html_snippet = render_slide_html(validated, self.presentation_palette, is_opening=is_opening)
                layout = validated.get("layout") or layout
                slide = validated
            except Exception:  # noqa: BLE001
                html_snippet = ""
            extra: dict = {}
            # Real previous slide id: the update path paints from a new turn,
            # whose turnId prefix alone never matches the painted slide, so
            # the frontend is told exactly which slide this replaces.
            if replaces:
                extra["replaces"] = replaces
            if target_slide_id:
                extra["targetSlideId"] = target_slide_id
            await self.send_front(
                self._build_slide_event(
                    "slide_replaced" if is_regen else "slide",
                    turn_id, seq, version, slide, layout, html_snippet,
                    keywords, extra or None,
                )
            )
            # Persist only after successful emit; stale seq never overwrites.
            self._commit_slide_store(kind if is_regen else "new", slide, seq,
                                     f"{turn_id}-{seq}")
            # Latency baseline: ASR(complete)->Jev->LLM->render(paint), p50/p95 log.
            try:
                _latency().record_paint(turn_id, time.monotonic())
                e2e = _latency().end_to_end(turn_id)
                s = _latency().summary()
                p50 = f"{s['p50']:.2f}s" if s["p50"] is not None else "-"
                p95 = f"{s['p95']:.2f}s" if s["p95"] is not None else "-"
                e2e_s = f"{e2e:.2f}s" if e2e is not None else "-"
                print(
                    f"[latency] turn={turn_id} e2e={e2e_s} n={s['n']} "
                    f"p50={p50} p95={p95} provisional={s['provisional']}",
                    flush=True,
                )
            except Exception:  # noqa: BLE001
                pass
            # Vivo progresivo: texto ya emitido; la imagen llega después por
            # patch sin bloquear. Fail-open: si no corresponde, nada se crea.
            try:
                from backend.presentation_api.utils.slide_designs import (
                    should_generate_image as _should_gen,
                )

                if _should_gen(layout, slide.get("imagen_prompt")):
                    img_task = asyncio.create_task(
                        self._run_image_task(
                            turn_id, seq, version,
                            str(slide.get("title") or ""),
                            str(slide.get("imagen_prompt") or ""),
                            str(slide.get("imagen_hashtag") or ""),
                            dict(slide) if isinstance(slide, dict) else {},
                            is_opening,
                        )
                    )
                    self.image_tasks.add(img_task)
                    img_task.add_done_callback(self.image_tasks.discard)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.last_layout = layout
                summary_text = str(slide.get("texto") or slide.get("text") or "")
                self.last_slide_summary = {
                    "titulo": str(slide.get("titulo") or slide.get("title") or "")[:120],
                    "resumen": summary_text[:300],
                }
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass

    async def _emit_kept(self, turn_id: str, seq: int, version: int) -> None:
        """Terminal keep (never downgraded to new)."""
        try:
            await self.send_front(
                {"type": "slide_kept", "turnId": turn_id,
                 "seq": seq, "topicVersion": version}
            )
        except Exception:  # noqa: BLE001
            pass

    async def _run_image_task(
        self,
        turn_id: str,
        seq: int,
        version: int,
        titulo: str,
        imagen_prompt: str,
        tags: str,
        slide: dict,
        is_opening: bool = False,
    ) -> None:
        """Genera la imagen en segundo plano y emite slide_image_updated.

        Nunca bloquea el vivo: fail-open a placeholder si falla. Antes de
        emitir chequea que la versión siga vigente (aborta si stale).
        """
        try:
            async with self.image_semaphore:
                from backend.presentation_api.utils.image_generation import (
                    generate_image,
                )
                from backend.presentation_api.utils.slide_designs import (
                    build_fast_prompt,
                    render_slide_html,
                )

                url = await generate_image(build_fast_prompt(titulo, imagen_prompt, tags))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            return
        if not url or version != self.current_topic_version:
            return
        try:
            html_snippet = ""
            try:
                patched = dict(slide)
                patched["image"] = url
                html_snippet = render_slide_html(
                    patched, self.presentation_palette, is_opening=is_opening
                )
            except Exception:  # noqa: BLE001
                html_snippet = ""
            await self.send_front(
                {
                    "type": "slide_image_updated",
                    "turnId": turn_id,
                    "seq": seq,
                    "topicVersion": version,
                    "image": url,
                    "html": html_snippet,
                }
            )
        except Exception:  # noqa: BLE001
            pass

    def _sync_session_meta(self) -> None:
        """Mirror bridge topic/audience/palette/version into the store entry."""
        try:
            from backend.presentation_api.utils import live_sessions as _live

            entry = _live.get_or_create(self.user_id, self.live_session_id)
            entry["topic"] = self.current_topic
            entry["audience"] = self.current_audience
            entry["palette"] = self.presentation_palette
            entry["palette_id"] = self.presentation_palette_id
            entry["topic_version"] = self.current_topic_version
            entry["updated_at"] = _live._now()
            entry["jev_context_cache"] = _live.build_context_cache(entry)
        except Exception:  # noqa: BLE001 - store never breaks the bridge
            pass

    def _adopt_live_session(self, live_session_id: str, resume: bool) -> bool:
        """Adopt a client-provided live_session_id (WS retries reuse it).

        With resume=True and a live stored session, bridge state (topic,
        audience, palette, seq, opened versions) is restored. Otherwise the
        id is adopted as a fresh session. Returns True when the id changed.
        """
        candidate = str(live_session_id or "").strip()
        if not candidate or candidate == self.live_session_id:
            return False
        try:
            from backend.presentation_api.utils import live_sessions as _live

            existing = _live.get(self.user_id, candidate) if resume else None
            self.live_session_id = candidate
            if existing is not None:
                self.current_topic = str(existing.get("topic") or "")
                self.current_audience = str(existing.get("audience") or "general") or "general"
                self.current_topic_version = int(existing.get("topic_version") or 1)
                if existing.get("palette") is not None:
                    self.presentation_palette = existing.get("palette")
                    self.presentation_palette_id = existing.get("palette_id")
                try:
                    self.seq_counter = max(
                        self.seq_counter,
                        int(existing.get("last_recorded_seq") or 0),
                    )
                except (TypeError, ValueError):
                    pass
                if existing.get("current_slide") or existing.get("history"):
                    self.opened_versions.add(self.current_topic_version)
                self._sync_summary_from_store(existing)
            else:
                _live.get_or_create(self.user_id, candidate)
                self._sync_session_meta()
            print(f"[bridge] live_session adopted id={candidate} resume={resume}",
                  flush=True)
        except Exception:  # noqa: BLE001
            pass
        return True

    def confirm_topic_version(self, new_version: int) -> None:
        """Bump version: cancel in-flight tasks; stale results drop at pre-emit."""
        try:
            new_version = int(new_version)
        except (TypeError, ValueError):
            return
        if new_version == self.current_topic_version:
            return
        self.current_topic_version = new_version
        try:
            from backend.presentation_api.utils import live_sessions as _live

            entry = _live.get_or_create(self.user_id, self.live_session_id)
            _live.reset_for_topic_version(entry, new_version, self.current_topic)
            self._sync_summary_from_store(entry)
        except Exception:  # noqa: BLE001 - store never breaks version bumps
            pass
        for task in list(self.pending_tasks.values()):
            if not task.done():
                task.cancel()
        for task in list(self.image_tasks):
            if not task.done():
                task.cancel()

    async def cancel_slide_tasks(self) -> None:
        for task in list(self.pending_tasks.values()):
            if not task.done():
                task.cancel()
        for task in list(self.image_tasks):
            if not task.done():
                task.cancel()
        if self.pending_tasks:
            await asyncio.gather(*list(self.pending_tasks.values()),
                                 return_exceptions=True)

    def _pre_roll_push(self, frame: bytes) -> None:
        if self.pre_roll_cap <= 0:
            return
        self.pre_roll.append(frame)
        self.pre_roll_bytes += len(frame)
        while self.pre_roll_bytes > self.pre_roll_cap and self.pre_roll:
            old = self.pre_roll.popleft()
            self.pre_roll_bytes -= len(old)

    def _pre_roll_drain(self) -> list[bytes]:
        frames = list(self.pre_roll)
        self.pre_roll.clear()
        self.pre_roll_bytes = 0
        return frames

    async def open_upstream(self) -> bool:
        """Abre una NUEVA sesion upstream (sin resume token) y hace handshake."""
        import websockets
        from websockets.exceptions import WebSocketException

        api_key = get_api_key()
        if not api_key:
            await self.send_front(
                {"type": "error", "message": "MODEL_API_KEY no configurada en el backend."}
            )
            return False
        session_id = uuid.uuid4().hex
        url = f"{self.config['url']}?sessionId={session_id}"
        try:
            # websockets>=13: extra_headers como dict; handshake dentro de 10s.
            ws = await websockets.connect(url, max_size=4 * 1024 * 1024)
            await ws.send(build_handshake(api_key, self.config["model"]))
        except WebSocketException as exc:
            logger.warning("No se pudo abrir upstream realtime: %s", exc)
            await self.send_front(
                {"type": "error", "message": f"No se pudo conectar con Meta ASR: {exc}"}
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error abriendo upstream realtime: %s", exc)
            await self.send_front(
                {"type": "error", "message": f"No se pudo conectar con Meta ASR: {exc}"}
            )
            return False
        self.upstream = ws
        self.upstream_session_id = session_id
        self.streaming = True
        self.last_voice_at = asyncio.get_event_loop().time()
        self.wake_counter = 0
        # Drena pre-roll primero para no cortar el inicio de la frase.
        for frame in self._pre_roll_drain():
            try:
                await ws.send(frame)
            except Exception:  # noqa: BLE001
                break
        self._start_relay()
        return True

    def _start_relay(self) -> None:
        if self.relay_task and not self.relay_task.done():
            return
        self.relay_task = asyncio.create_task(self._relay_loop())

    async def _relay_loop(self) -> None:
        """Reenvia eventos de Meta al frontend; detecta cierres y codigos."""
        ws = self.upstream
        if ws is None:
            return
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    continue  # eventos son JSON text; ignora binarios
                try:
                    enriched = enrich_event(json.loads(message))
                    self._note_meta_event(enriched)
                    await self.send_front(enriched)
                except Exception:  # noqa: BLE001
                    # Si el frontend se cerro, termina el relay.
                    break
                if isinstance(enriched, dict) and enriched.get("type") == "speechComplete":
                    try:
                        await self.handle_speech_complete(enriched)
                    except Exception:  # noqa: BLE001
                        logger.info("slide task spawn fallo; relay sigue")
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            logger.info("Upstream relay terminado code=%s err=%s", code, exc)
            if self.streaming and not self.closed:
                await self._handle_upstream_close(code, str(exc))
            return
        # El async-for termino: el servidor cerro. Extrae codigo si existe.
        code = None
        try:
            code = getattr(ws, "close_code", None)
        except Exception:  # noqa: BLE001
            code = None
        if self.streaming and not self.closed:
            await self._handle_upstream_close(code, "upstream cerrado por el servidor")

    async def _handle_upstream_close(self, code, reason: str) -> None:
        self.streaming = False
        try:
            await self.send_front({"type": "upstream_close", "code": code, "reason": reason})
        except Exception:  # noqa: BLE001
            pass
        # Politica de reintento segun codigo Meta:
        # 1008 = no reintentar la misma sesion; 1011/1013 = backoff + NUEVA sesion.
        if code in (1011, 1013):
            await asyncio.sleep(1.0)
            if not self.closed and not self.streaming:
                # Reabre solo si hay actividad de voz reciente o llega audio nuevo;
                # por ahora reabre de inmediato para no perder el turno.
                await self.open_upstream()
        elif code not in (1000, None):
            # 1008 u otros: no reintenta solo; el usuario reinicia.
            pass

    async def pause_upstream(self, reason: str = "idle_pause") -> None:
        """Pausa prolongada: endStream, drena eventos, cierra upstream 1000."""
        ws = self.upstream
        self.streaming = False
        if ws is None:
            return
        self.upstream = None
        try:
            await ws.send(json.dumps({"type": "endStream"}))
        except Exception:  # noqa: BLE001
            pass
        # Drena eventos pendientes (p. ej. speechComplete final) con timeout.
        try:
            async def _drain() -> None:
                try:
                    async for message in ws:
                        if isinstance(message, bytes):
                            continue
                        try:
                            enriched = enrich_event(json.loads(message))
                            self._note_meta_event(enriched)
                            await self.send_front(enriched)
                        except Exception:  # noqa: BLE001
                            break
                        if isinstance(enriched, dict) and enriched.get("type") == "speechComplete":
                            try:
                                await self.handle_speech_complete(enriched)
                            except Exception:  # noqa: BLE001
                                pass
                except Exception:  # noqa: BLE001
                    pass

            await asyncio.wait_for(_drain(), timeout=DRAIN_TIMEOUT_S)
        except asyncio.TimeoutError:
            pass
        except Exception:  # noqa: BLE001
            pass
        try:
            await ws.close(code=1000)
        except Exception:  # noqa: BLE001
            pass
        if self.relay_task and not self.relay_task.done():
            self.relay_task.cancel()
        try:
            await self.send_front({"type": "paused", "reason": reason})
        except Exception:  # noqa: BLE001
            pass

    async def _consumer_loop(self) -> None:
        """Saca frames de la cola acotada (5s) y los envia a Meta."""
        while not self.closed:
            try:
                frame = await self.audio_queue.get()
            except asyncio.CancelledError:
                break
            ws = self.upstream
            if not self.streaming or ws is None:
                continue  # en pausa: el reader ya gestiona pre-roll; descarta
            try:
                await ws.send(frame)
            except Exception as exc:  # noqa: BLE001
                logger.info("Fallo envio a upstream: %s", exc)
                self.streaming = False

    async def _watchdog_loop(self) -> None:
        """Detecta silencio continuo >= umbral y dispara la pausa prolongada."""
        threshold_ms = self.config["silence_pause_ms"]
        while not self.closed:
            await asyncio.sleep(WATCHDOG_INTERVAL_S)
            if not self.streaming or self.upstream is None:
                continue
            now = asyncio.get_event_loop().time()
            if (now - self.last_voice_at) * 1000 >= threshold_ms:
                logger.info("Pausa prolongada tras %d ms de silencio", threshold_ms)
                await self.pause_upstream(reason="prolonged_silence")

    def _enqueue_or_drop(self, frame: bytes) -> None:
        try:
            self.audio_queue.put_nowait(frame)
        except asyncio.QueueFull:
            try:
                self.audio_queue.get_nowait()  # descarta el mas viejo (max 5s)
                self.audio_queue.put_nowait(frame)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    async def on_audio_frame(self, frame: bytes) -> None:
        voiced = is_voiced(frame, self.config["vad_threshold"])
        now = asyncio.get_event_loop().time()
        if voiced:
            self.last_voice_at = now
        if not self.streaming or self.upstream is None:
            # En pausa: solo guarda pre-roll y espera voz confirmada (WAKE).
            self._pre_roll_push(frame)
            if voiced:
                self.wake_counter += 1
            else:
                self.wake_counter = 0
            if self.wake_counter >= WAKE_VOICED_FRAMES:
                self.wake_counter = 0
                ok = await self.open_upstream()
                if ok:
                    try:
                        await self.send_front({"type": "resumed", "reason": "voice"})
                    except Exception:  # noqa: BLE001
                        pass
            return
        self._enqueue_or_drop(frame)
        # VAD-time window: voiced frames only (not wall-clock). Never cuts PCM.
        if voiced and self._window_enabled() and self._duty_active(now):
            self.vad_window_s += FRAME_S
            await self._maybe_force_window()

    async def on_control(self, obj: dict) -> None:
        ctype = obj.get("type")
        if ctype == "idle_pause":
            if self.streaming:
                await self.pause_upstream(reason="idle_pause")
        elif ctype == "end":
            await self.pause_upstream(reason="end")
            self.closed = True
            try:
                await self.frontend.close(code=1000)
            except Exception:  # noqa: BLE001
                pass

    async def run(self) -> None:
        await self.frontend.accept()
        if not get_api_key():
            await self.send_front(
                {"type": "error", "message": "MODEL_API_KEY no configurada en el backend."}
            )
            await self.frontend.close(code=1008)
            return
        ok = await self.open_upstream()
        if not ok:
            try:
                await self.frontend.close(code=1011)
            except Exception:  # noqa: BLE001
                pass
            return
        # Reuse the same live_session_id across WS retries: the frontend
        # stores it and sends it back in the config frame (resume flag).
        try:
            await self.send_front({"type": "live_session",
                                   "live_session_id": self.live_session_id})
        except Exception:  # noqa: BLE001
            pass
        self.consumer_task = asyncio.create_task(self._consumer_loop())
        self.watchdog_task = asyncio.create_task(self._watchdog_loop())
        try:
            while not self.closed:
                message = await self.frontend.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("bytes") is not None:
                    data = message["bytes"]
                    # Acepta cualquier tamano; acumula por FRAME_BYTES para VAD estable.
                    # Normalmente el frontend ya envia ~80ms (3840 bytes).
                    offset = 0
                    while offset < len(data):
                        chunk = data[offset : offset + FRAME_BYTES]
                        offset += FRAME_BYTES
                        # Rellena frames cortos con silencio para RMS estable.
                        if len(chunk) < FRAME_BYTES:
                            chunk = chunk + b"\x00" * (FRAME_BYTES - len(chunk))
                        await self.on_audio_frame(chunk)
                elif message.get("text") is not None:
                    try:
                        obj = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        # Permite ajustar el umbral de pausa por sesion (5s-60s).
                        if obj.get("type") == "config":
                            if "silencePauseMs" in obj:
                                try:
                                    v = int(obj["silencePauseMs"])
                                    self.config["silence_pause_ms"] = max(5000, min(60000, v))
                                except (ValueError, TypeError):
                                    pass
                            if "topic" in obj and isinstance(obj["topic"], str):
                                self.current_topic = obj["topic"].strip()
                                if isinstance(obj.get("keywords"), list):
                                    self.current_keywords = [
                                        str(k).strip() for k in obj["keywords"]
                                        if str(k).strip()
                                    ][:10]
                            if "topicVersion" in obj:
                                self.confirm_topic_version(obj["topicVersion"])
                            if "audience" in obj and isinstance(obj["audience"], str):
                                cand = obj["audience"].strip().lower()
                                try:
                                    from backend.presentation_api.utils.llm_client import (
                                        VALID_AUDIENCES,
                                    )

                                    if cand in VALID_AUDIENCES:
                                        self.current_audience = cand
                                except Exception:  # noqa: BLE001
                                    pass
                            if "palette_id" in obj and isinstance(obj["palette_id"], str):
                                # First wins: adopt only if bridge has no palette yet.
                                if self.presentation_palette is None:
                                    try:
                                        from backend.presentation_api.utils.palettes import (
                                            get_palette_by_id,
                                        )

                                        found = get_palette_by_id(obj["palette_id"])
                                        if found is not None:
                                            self.presentation_palette = found
                                            self.presentation_palette_id = str(
                                                found.get("id", "") or ""
                                            )
                                            self._sync_session_meta()
                                    except Exception:  # noqa: BLE001
                                        pass
                            # Persist session meta (topic/audience/palette) for resume.
                            self._sync_session_meta()
                            if "liveSessionId" in obj and isinstance(obj["liveSessionId"], str):
                                adopted = self._adopt_live_session(
                                    obj["liveSessionId"],
                                    bool(obj.get("resume", False)),
                                )
                                if adopted:
                                    try:
                                        await self.send_front(
                                            {"type": "live_session",
                                             "live_session_id": self.live_session_id}
                                        )
                                    except Exception:  # noqa: BLE001
                                        pass
                            if "displayScale" in obj:
                                try:
                                    from backend.presentation_api.utils import (
                                        live_sessions as _live3,
                                    )

                                    _entry = _live3.get_or_create(
                                        self.user_id, self.live_session_id)
                                    # Clamped 0.8-1.3; invalid keeps previous.
                                    _live3.set_display_scale(
                                        _entry, obj["displayScale"])
                                except Exception:  # noqa: BLE001
                                    pass
                        else:
                            await self.on_control(obj)
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.info("Frontend WS terminado: %s", exc)
        finally:
            self.closed = True
            for task in (self.consumer_task, self.watchdog_task):
                if task and not task.done():
                    task.cancel()
            for task in list(self.pending_tasks.values()):
                if not task.done():
                    task.cancel()
            for task in list(self.image_tasks):
                if not task.done():
                    task.cancel()
            # Cierra upstream sin endStream ruidoso si ya estaba en pausa.
            ws = self.upstream
            self.upstream = None
            self.streaming = False
            if ws is not None:
                try:
                    await ws.send(json.dumps({"type": "endStream"}))
                except Exception:  # noqa: BLE001
                    pass
                try:
                    await ws.close(code=1000)
                except Exception:  # noqa: BLE001
                    pass


async def handle_frontend_socket(
    frontend: WebSocket,
    user_id: str = "dev-local",
    live_session_id: str | None = None,
) -> None:
    """Punto de entrada del endpoint WS /ws/transcribe.

    user_id comes from the verified Clerk JWT (never from the frontend).
    """
    bridge = RealtimeBridge(frontend, get_config(), user_id=user_id,
                            live_session_id=live_session_id)
    await bridge.run()
