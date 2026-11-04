"""In-memory per-user live session store (process memory only, no DB).

One entry per (user_id, live_session_id) holds the current slide (full
validated dict), a short history (max 8 summaries for Jev + max 8 full
validated dicts with ids/seqs/versions for visual restore), a prebuilt Jev
context cache (<~2500 chars), session metadata (topic/audience/palette/
topicVersion) and displayScale. Entries expire after SESSION_TTL_S (2h) of
inactivity.

Seq guard: every committed slide carries the bridge arrival-order seq;
commits with seq <= last_recorded_seq are stale and rejected, so two
concurrent slide tasks can never overwrite newer state with older state.
"""

import time
import uuid

SESSION_TTL_S = 2 * 3600
HISTORY_MAX = 8
JEV_CACHE_MAX_CHARS = 2500

# MVP en memoria: historial de transcripciones por sesion para dar contexto
# a Jev y evitar repetir temas ya cubiertos. Sin DB, mismo TTL (2h) que slides.
TRANSCRIPT_HISTORY_MAX = 20
TRANSCRIPT_TURN_MAX_CHARS = 500
TRANSCRIPT_TOTAL_MAX_CHARS = 4000
TRANSCRIPT_CONTEXT_MAX_CHARS = 1500
TRANSCRIPT_CONTEXT_MAX_ITEMS = 10

# User text scale for the slide stage (80-130%, stored as 0.8-1.3 factor).
DISPLAY_SCALE_MIN = 0.8
DISPLAY_SCALE_MAX = 1.3
DISPLAY_SCALE_DEFAULT = 1.0

_store: dict[tuple[str, str], dict] = {}


def _now() -> float:
    return time.time()


def new_session_id() -> str:
    return uuid.uuid4().hex


def _blank_entry(user_id: str, live_session_id: str) -> dict:
    now = _now()
    return {
        "user_id": user_id,
        "live_session_id": live_session_id,
        "current_slide": None,
        "current_slide_id": None,
        "current_created_at": 0.0,
        "current_created_seq": 0,
        "current_created_version": 1,
        "history": [],
        "history_full": [],
        "history_ids": [],
        "history_seqs": [],
        "history_versions": [],
        "transcript_history": [],
        "topic": "",
        "audience": "general",
        "palette": None,
        "palette_id": None,
        "topic_version": 1,
        "displayScale": 1.0,
        "last_recorded_seq": 0,
        "jev_context_cache": "",
        "created_at": now,
        "updated_at": now,
    }


def is_expired(entry: dict) -> bool:
    try:
        return (_now() - float(entry.get("updated_at") or 0)) > SESSION_TTL_S
    except (TypeError, ValueError):
        return True


def cleanup_expired() -> int:
    """Drop expired entries. Returns the number of removed entries."""
    dead = [k for k, e in _store.items() if is_expired(e)]
    for key in dead:
        _store.pop(key, None)
    return len(dead)


def get_or_create(user_id: str, live_session_id: str | None = None) -> dict:
    """Return the live entry, creating it when missing or expired."""
    user_id = str(user_id or "dev-local").strip() or "dev-local"
    live_session_id = str(live_session_id or "").strip() or new_session_id()
    key = (user_id, live_session_id)
    entry = _store.get(key)
    if entry is None or is_expired(entry):
        entry = _blank_entry(user_id, live_session_id)
        _store[key] = entry
    return entry


def get(user_id: str, live_session_id: str) -> dict | None:
    """Return the entry or None (missing/expired entries read as absent)."""
    key = (str(user_id or ""), str(live_session_id or ""))
    entry = _store.get(key)
    if entry is None:
        return None
    if is_expired(entry):
        _store.pop(key, None)
        return None
    return entry


def get_latest_for_user(user_id: str) -> dict | None:
    """Most recently updated live entry for resume check, or None."""
    user_id = str(user_id or "")
    best: dict | None = None
    for (uid, _), entry in list(_store.items()):
        if uid != user_id or is_expired(entry):
            if uid == user_id and is_expired(entry):
                _store.pop((uid, str(entry.get("live_session_id") or "")), None)
            continue
        if best is None or float(entry.get("updated_at") or 0) > float(best.get("updated_at") or 0):
            best = entry
    return best


def discard(user_id: str, live_session_id: str) -> bool:
    """Drop one live session. Returns True when something was removed."""
    return _store.pop((str(user_id or ""), str(live_session_id or "")), None) is not None


def clamp_display_scale(value: object) -> float | None:
    """Clamp a displayScale candidate to [0.8, 1.3]. None when unparseable."""
    try:
        scale = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if scale != scale or scale in (float("inf"), float("-inf")):
        return None
    return max(DISPLAY_SCALE_MIN, min(DISPLAY_SCALE_MAX, scale))


def get_display_scale(entry: dict) -> float:
    """Validated displayScale for an entry (legacy entries read as 1.0)."""
    clamped = clamp_display_scale((entry or {}).get("displayScale"))
    return clamped if clamped is not None else DISPLAY_SCALE_DEFAULT


def set_display_scale(entry: dict, value: object) -> bool:
    """Persist a clamped displayScale. False when invalid (keeps previous)."""
    clamped = clamp_display_scale(value)
    if clamped is None or not isinstance(entry, dict):
        return False
    entry["displayScale"] = clamped
    entry["updated_at"] = _now()
    return True


def _ensure_history_fields(entry: dict) -> None:
    """Backfill full-history fields for entries created before this slice."""
    for key in ("history", "history_full", "history_ids", "history_seqs",
                "history_versions", "transcript_history"):
        if not isinstance(entry.get(key), list):
            entry[key] = []
    try:
        entry["current_created_version"] = int(
            entry.get("current_created_version")
            or entry.get("topic_version")
            or 1
        )
    except (TypeError, ValueError):
        entry["current_created_version"] = 1


def _trim_histories(entry: dict) -> None:
    entry["history"] = list(entry.get("history") or [])[-HISTORY_MAX:]
    entry["history_full"] = list(entry.get("history_full") or [])[-HISTORY_MAX:]
    entry["history_ids"] = list(entry.get("history_ids") or [])[-HISTORY_MAX:]
    entry["history_seqs"] = list(entry.get("history_seqs") or [])[-HISTORY_MAX:]
    entry["history_versions"] = list(
        entry.get("history_versions") or []
    )[-HISTORY_MAX:]


def _push_current_to_history(entry: dict) -> None:
    """Archive current slide: summary + full copy with id/seq/version."""
    _ensure_history_fields(entry)
    current = entry.get("current_slide")
    if not isinstance(current, dict) or not current:
        return
    entry["history"].append(summarize_slide(current))
    entry["history_full"].append(dict(current))
    entry["history_ids"].append(str(entry.get("current_slide_id") or ""))
    try:
        seq = int(entry.get("current_created_seq") or 0)
    except (TypeError, ValueError):
        seq = 0
    entry["history_seqs"].append(seq)
    try:
        ver = int(
            entry.get("current_created_version")
            or entry.get("topic_version")
            or 1
        )
    except (TypeError, ValueError):
        ver = 1
    entry["history_versions"].append(ver)
    _trim_histories(entry)


def archive_current(entry: dict) -> bool:
    """Move current to history (summary + full) and clear current.

    Used when a painted slide is removed (regen filtered) so later
    tasks never patch a removed ghost. Returns True when archived.
    """
    _ensure_history_fields(entry)
    current = entry.get("current_slide")
    if not isinstance(current, dict) or not current:
        return False
    _push_current_to_history(entry)
    entry["current_slide"] = None
    entry["current_slide_id"] = None
    entry["current_created_at"] = 0.0
    entry["current_created_seq"] = 0
    try:
        entry["current_created_version"] = int(entry.get("topic_version") or 1)
    except (TypeError, ValueError):
        entry["current_created_version"] = 1
    entry["updated_at"] = _now()
    entry["jev_context_cache"] = build_context_cache(entry)
    return True


def ordered_slides(entry: dict) -> list[dict]:
    """Paint-ordered envelopes for visual restore.

    Each item is {"id": str, "seq": int, "topic_version": int,
    "slide": full validated dict}. History oldest-first, current last.
    Legacy entries with only summaries synthesize minimal slides so the
    count stays consistent with slide_count().
    """
    _ensure_history_fields(entry)
    try:
        default_version = int(entry.get("topic_version") or 1)
    except (TypeError, ValueError):
        default_version = 1
    out: list[dict] = []
    full = entry.get("history_full") or []
    ids = entry.get("history_ids") or []
    seqs = entry.get("history_seqs") or []
    vers = entry.get("history_versions") or []
    if full:
        for i, item in enumerate(full):
            if not isinstance(item, dict):
                continue
            sid = str(ids[i]) if i < len(ids) and ids[i] else f"h-{i + 1}"
            try:
                seq = int(seqs[i]) if i < len(seqs) else i + 1
            except (TypeError, ValueError):
                seq = i + 1
            try:
                ver = int(vers[i]) if i < len(vers) else default_version
            except (TypeError, ValueError):
                ver = default_version
            out.append({"id": sid, "seq": seq,
                        "topic_version": ver, "slide": dict(item)})
    else:
        for idx, summ in enumerate(entry.get("history") or []):
            if not isinstance(summ, dict):
                continue
            title = str(summ.get("titulo") or summ.get("title") or "")
            text = str(summ.get("resumen") or summ.get("text") or "")
            kws = summ.get("keywords")
            out.append({
                "id": f"legacy-{idx + 1}",
                "seq": idx + 1,
                "topic_version": default_version,
                "slide": {
                    "layout": str(summ.get("layout") or "title_text"),
                    "title": title,
                    "titulo": title,
                    "text": text,
                    "texto": text,
                    "bullets": [],
                    "keywords": ([str(k) for k in kws if str(k).strip()][:5]
                                 if isinstance(kws, list) else []),
                },
            })
    current = entry.get("current_slide")
    if isinstance(current, dict) and current:
        try:
            seq = int(entry.get("current_created_seq")
                      or entry.get("last_recorded_seq") or 0)
        except (TypeError, ValueError):
            seq = 0
        try:
            ver = int(entry.get("current_created_version")
                      or entry.get("topic_version") or 1)
        except (TypeError, ValueError):
            ver = default_version
        out.append({"id": str(entry.get("current_slide_id") or ""),
                    "seq": seq, "topic_version": ver,
                    "slide": dict(current)})
    return out


def reset_for_topic_version(entry: dict, new_version: int, new_topic: str = "") -> None:
    """Cleanup on topicVersion change: archive current, clear base state."""
    try:
        new_version = int(new_version)
    except (TypeError, ValueError):
        return
    if new_version == int(entry.get("topic_version") or 1):
        return
    _push_current_to_history(entry)
    entry["current_slide"] = None
    entry["current_slide_id"] = None
    entry["current_created_at"] = 0.0
    entry["current_created_seq"] = 0
    entry["current_created_version"] = new_version
    entry["topic_version"] = new_version
    if isinstance(new_topic, str) and new_topic.strip():
        entry["topic"] = new_topic.strip()
    # El contexto viejo contamina: con tema nuevo, transcripciones previas fuera.
    _ensure_history_fields(entry)
    entry["transcript_history"] = []
    entry["updated_at"] = _now()
    entry["jev_context_cache"] = build_context_cache(entry)


def summarize_slide(slide: dict) -> dict:
    """Short summary for history and Jev payload (no PII beyond content)."""
    if not isinstance(slide, dict):
        return {"titulo": "", "layout": "", "resumen": "", "keywords": []}
    kws = slide.get("keywords")
    return {
        "titulo": str(slide.get("titulo") or slide.get("title") or "")[:120],
        "layout": str(slide.get("layout") or "")[:40],
        "resumen": str(slide.get("texto") or slide.get("text") or "")[:300],
        "keywords": [str(k) for k in kws if str(k).strip()][:5]
        if isinstance(kws, list)
        else [],
    }


def append_transcript(entry: dict, turn_id: str, seq: int, text: str) -> bool:
    """Guarda un turno transcrito en memoria (dedupe por turn_id).

    Solo MVP en memoria: sin DB, mismo TTL que la sesion. Trunca cada turno
    a TRANSCRIPT_TURN_MAX_CHARS y el total a TRANSCRIPT_TOTAL_MAX_CHARS
    (ultimos TRANSCRIPT_HISTORY_MAX turnos). False cuando vacio o duplicado.
    """
    _ensure_history_fields(entry)
    tid = str(turn_id or "").strip()
    cleaned = str(text or "").strip()
    if not tid or not cleaned:
        return False
    for item in entry.get("transcript_history") or []:
        if isinstance(item, dict) and str(item.get("turn_id") or "") == tid:
            return False
    try:
        seq_n = int(seq)
    except (TypeError, ValueError):
        seq_n = 0
    entry["transcript_history"].append({
        "turn_id": tid,
        "seq": seq_n,
        "texto": cleaned[:TRANSCRIPT_TURN_MAX_CHARS],
        "ts": _now(),
    })
    # Cap por cantidad y por chars totales (saca los mas viejos primero).
    trimmed = list(entry["transcript_history"] or [])[-TRANSCRIPT_HISTORY_MAX:]
    total = sum(len(str(i.get("texto") or "")) for i in trimmed if isinstance(i, dict))
    while len(trimmed) > 1 and total > TRANSCRIPT_TOTAL_MAX_CHARS:
        dropped = trimmed.pop(0)
        if isinstance(dropped, dict):
            total -= len(str(dropped.get("texto") or ""))
    entry["transcript_history"] = trimmed
    entry["updated_at"] = _now()
    return True


def build_transcript_context(
    entry: dict,
    exclude_turn_id: str | None = None,
    max_chars: int = TRANSCRIPT_CONTEXT_MAX_CHARS,
    max_items: int = TRANSCRIPT_CONTEXT_MAX_ITEMS,
) -> list[dict]:
    """Contexto de transcripciones previas para Jev (sin el turno actual).

    Devuelve los ultimos turnos saneados [{"turno": id, "texto": ...}],
    excluyendo exclude_turn_id (el turno en curso ya viaja en texto_turno).
    Cap ~1500 chars / 10 items para no inflar el payload.
    """
    _ensure_history_fields(entry)
    excluded = str(exclude_turn_id or "").strip()
    items = []
    for item in list(entry.get("transcript_history") or []):
        if not isinstance(item, dict):
            continue
        tid = str(item.get("turn_id") or "")
        if excluded and tid == excluded:
            continue
        texto = str(item.get("texto") or "").strip()
        if not texto:
            continue
        items.append({"turno": tid[:64], "texto": texto[:TRANSCRIPT_TURN_MAX_CHARS]})
    items = items[-max_items:]
    # Recorta por chars totales desde los mas recientes.
    total = 0
    kept: list[dict] = []
    for item in reversed(items):
        total += len(item["texto"])
        if total > max_chars and kept:
            break
        kept.append(item)
    kept.reverse()
    return kept


def _touch(entry: dict) -> None:
    entry["updated_at"] = _now()
    entry["jev_context_cache"] = build_context_cache(entry)


def record_new(
    entry: dict,
    slide: dict,
    seq: int,
    slide_id: str,
    topic_version: int | None = None,
) -> bool:
    """Push current to history, set the new slide. False when stale."""
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        return False
    try:
        if seq <= int(entry.get("last_recorded_seq") or 0):
            return False
    except (TypeError, ValueError):
        return False
    _ensure_history_fields(entry)
    _push_current_to_history(entry)
    entry["current_slide"] = dict(slide) if isinstance(slide, dict) else {}
    entry["current_slide_id"] = str(slide_id or "")
    entry["current_created_at"] = _now()
    entry["current_created_seq"] = seq
    if topic_version is None:
        topic_version = entry.get("topic_version") or 1
    try:
        entry["current_created_version"] = int(topic_version)
    except (TypeError, ValueError):
        try:
            entry["current_created_version"] = int(entry.get("topic_version") or 1)
        except (TypeError, ValueError):
            entry["current_created_version"] = 1
    entry["last_recorded_seq"] = seq
    _touch(entry)
    return True


def record_update(entry: dict, slide: dict, seq: int, slide_id: str) -> bool:
    """Replace current without pushing history. False when stale."""
    try:
        seq = int(seq)
    except (TypeError, ValueError):
        return False
    try:
        if seq <= int(entry.get("last_recorded_seq") or 0):
            return False
    except (TypeError, ValueError):
        return False
    _ensure_history_fields(entry)
    entry["current_slide"] = dict(slide) if isinstance(slide, dict) else {}
    entry["current_slide_id"] = str(slide_id or entry.get("current_slide_id") or "")
    entry["last_recorded_seq"] = seq
    _touch(entry)
    return True


def build_jev_context(entry: dict) -> tuple[dict, list]:
    """Return (slide_actual, historial_reciente) for the Jev payload."""
    current = entry.get("current_slide")
    history = list(entry.get("history") or [])[-HISTORY_MAX:]
    if not isinstance(current, dict) or not current:
        return {}, history
    try:
        segundos = int(_now() - float(entry.get("current_created_at") or _now()))
    except (TypeError, ValueError):
        segundos = 0
    try:
        turnos = int(entry.get("last_recorded_seq") or 0) - int(
            entry.get("current_created_seq") or 0
        )
    except (TypeError, ValueError):
        turnos = 0
    slide_actual = {
        "layout": str(current.get("layout") or ""),
        "titulo": str(current.get("titulo") or current.get("title") or ""),
        "resumen": str(current.get("texto") or current.get("text") or ""),
        "segundos_desde_creacion": max(0, segundos),
        "turnos_desde_creacion": max(0, turnos),
        "keywords": list(current.get("keywords") or [])[:5],
    }
    return slide_actual, history


def build_context_cache(entry: dict) -> str:
    """Prebuilt Jev context (<~2500 chars): current + recent history."""
    parts: list[str] = []
    current = entry.get("current_slide")
    if isinstance(current, dict) and current:
        summary = summarize_slide(current)
        parts.append(
            f"Current: {summary['titulo']} [{summary['layout']}] "
            f"{summary['resumen']}"
        )
    else:
        parts.append("Current: none")
    for item in list(entry.get("history") or [])[-HISTORY_MAX:]:
        if isinstance(item, dict):
            parts.append(
                f"Prev: {str(item.get('titulo') or '')[:80]} "
                f"[{str(item.get('layout') or '')[:20]}] "
                f"{str(item.get('resumen') or '')[:120]}"
            )
    cache = " || ".join(parts)
    return cache[:JEV_CACHE_MAX_CHARS]


def slide_count(entry: dict) -> int:
    """Number of retrievable slides, consistent with ordered_slides()."""
    try:
        full = entry.get("history_full")
        if isinstance(full, list) and full:
            total = len(full)
        else:
            total = len(entry.get("history") or [])
    except (TypeError, AttributeError):
        total = 0
    if isinstance(entry.get("current_slide"), dict) and entry.get("current_slide"):
        total += 1
    return total
