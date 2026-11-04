"""Jev gate client: one decision request per turn/window via OpenRouter Decisions.

Endpoint: POST https://openrouter.ai/api/alpha/decisions (NOT chat completions).
Model is configured via JEV_MODEL (default typesafe/jev-1.13). The API key
lives server-side only (OPENROUTER_API_KEY) and never leaves the backend.

Split into pure helpers (build_payload, parse_decision_payload) and a single
network boundary (decide_slide_action). decide_slide_action never raises: any
error, timeout or schema mismatch returns a fail-open marker that preserves
the current slide flow (relevant=True, action="new").
"""

import logging
import os
import time

import httpx

logger = logging.getLogger("jev_gate")

JEV_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL_DEFAULT = "typesafe/jev-1.13"

_VALID_ACTIONS = ("keep", "update", "new")

ON_TOPIC_QUESTION = (
    "Does the turn text contribute real content to the main topic? "
    "Answer yes only if it develops the topic (synonyms, paraphrases or "
    "specific aspects count). Answer no for greetings, filler words, a "
    "different topic, or a tangential mention with no real contribution. "
    "If the main topic is empty or '(sin definir)', always answer yes."
)

SLIDE_ACTION_QUESTION = (
    "Given the current slide, the recent slide history (titulo/resumen), "
    "the recent transcript history (texto of previous turns) and the turn "
    "text, choose: keep if the turn is already covered by the current slide "
    "OR by any recent slide/transcript (repetition, paraphrase or same idea "
    "already painted, even if it is not the current slide) and there is "
    "nothing new to paint; update if the turn refines, corrects or extends "
    "the current slide and it is worth regenerating it fusing context; new "
    "ONLY if the turn brings new content whose title or main idea must "
    "change and deserves its own slide, not covered by history."
)


def _read_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def _read_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))


def get_jev_config() -> dict:
    """Read Jev gate config from env (server-side only, no secrets in code)."""
    timeout_ms = _read_int("JEV_TIMEOUT_MS", 4000, 250, 30000)
    return {
        "model": os.getenv("JEV_MODEL", JEV_MODEL_DEFAULT).strip() or JEV_MODEL_DEFAULT,
        "api_key": os.getenv("OPENROUTER_API_KEY", "").strip(),
        "topic_p": _read_float("JEV_TOPIC_P", 0.6, 0.0, 1.0),
        "action_conf": _read_float("JEV_ACTION_CONF", 0.55, 0.0, 1.0),
        "new_conf": _read_float("JEV_NEW_CONF", 0.68, 0.0, 1.0),
        "timeout_s": timeout_ms / 1000.0,
    }


def _sanitize_history(items: object) -> list:
    """Keep last up to 8 slide summaries (titulo/layout/resumen/keywords)."""
    if not isinstance(items, list):
        return []
    out = []
    for item in items[-8:]:
        if not isinstance(item, dict):
            continue
        kws = item.get("keywords")
        out.append(
            {
                "titulo": str(item.get("titulo") or item.get("title") or "")[:120],
                "layout": str(item.get("layout") or "")[:40],
                "resumen": str(item.get("resumen") or item.get("text") or "")[:300],
                "keywords": [str(k) for k in kws if str(k).strip()][:5]
                if isinstance(kws, list)
                else [],
            }
        )
    return out


def _sanitize_transcripts(items: object, max_chars: int = 1500, max_items: int = 10) -> list:
    """Keep last up to max_items transcript turns within max_chars (no PII beyond content)."""
    if isinstance(items, str):
        items = [{"texto": items}]
    if not isinstance(items, list):
        return []
    cleaned: list[dict] = []
    for item in items[-max_items:]:
        if isinstance(item, dict):
            texto = str(item.get("texto") or item.get("text") or "")[:500]
            turno = str(item.get("turno") or item.get("turn_id") or "")[:64]
        elif isinstance(item, str):
            texto, turno = item[:500], ""
        else:
            continue
        texto = texto.strip()
        if not texto:
            continue
        cleaned.append({"turno": turno, "texto": texto} if turno else {"texto": texto})
    total = 0
    kept: list[dict] = []
    for item in reversed(cleaned):
        total += len(str(item.get("texto") or ""))
        if total > max_chars and kept:
            break
        kept.append(item)
    kept.reverse()
    return kept


def build_payload(
    topic: str,
    keywords: list | None,
    audience: str,
    texto_turno: str,
    slide_actual: dict | None,
    model: str = JEV_MODEL_DEFAULT,
    historial_reciente: list | None = None,
    transcripcion_reciente: list | str | None = None,
) -> dict:
    """Build the Decisions request payload (pure, no IO, no env).

    Official schema: ``questions`` is a DICT keyed by id, each entry uses
    the ``type`` field (``noul`` or ``choice``), and choice options come
    only from the keys of the ``criteria`` dict (no ``options`` array).
    """
    actual = slide_actual if isinstance(slide_actual, dict) else {}
    if historial_reciente is None:
        historial_reciente = actual.get("historial_reciente")
    if transcripcion_reciente is None:
        transcripcion_reciente = actual.get("transcripcion_reciente")
    try:
        segundos = int(actual.get("segundos_desde_creacion", 0))
    except (TypeError, ValueError):
        segundos = 0
    try:
        turnos = int(actual.get("turnos_desde_creacion", 0))
    except (TypeError, ValueError):
        turnos = 0
    return {
        "model": model or JEV_MODEL_DEFAULT,
        "state": {
            "tema_principal": topic or "",
            "keywords": list(keywords or [])[:10],
            "audiencia": (audience or "general").strip() or "general",
            "texto_turno": texto_turno or "",
            "slide_actual": {
                "layout": str(actual.get("layout") or "")[:40],
                "titulo": str(actual.get("titulo") or actual.get("title") or "")[:120],
                "resumen": str(actual.get("resumen") or actual.get("text") or "")[:300],
                "segundos_desde_creacion": max(0, segundos),
                "turnos_desde_creacion": max(0, turnos),
            },
            "historial_reciente": _sanitize_history(historial_reciente),
            "transcripcion_reciente": _sanitize_transcripts(transcripcion_reciente),
        },
        "questions": {
            "on_topic": {
                "type": "noul",
                "instructions": ON_TOPIC_QUESTION,
                "criteria": {
                    "true": "The turn text develops the main topic.",
                    "false": "Greetings, filler, another topic, or no real contribution.",
                },
            },
            "slide_action": {
                "type": "choice",
                "instructions": SLIDE_ACTION_QUESTION,
                "criteria": {
                    "keep": "The turn is already covered by the current slide or any recent slide/transcript (repetition or paraphrase); nothing new to paint.",
                    "update": "The turn refines, corrects or extends the current slide; regenerate fused.",
                    "new": "ONLY when the title or main idea must change, not covered by history, and the turn deserves its own slide.",
                },
            },
        },
    }


def _as_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "si", "sí", "1", "relevant", "on_topic"):
            return True
        if v in ("false", "no", "0", "irrelevant", "off_topic"):
            return False
    return None


def _fail_open(reason: str, raw: object, has_current_slide: bool = False) -> dict:
    """Conservative fail-open: no current slide -> new; with one -> keep."""
    return {
        "relevant": True,
        "action": "keep" if has_current_slide else "new",
        "reason": f"fail-open: {reason}",
        "raw": raw if isinstance(raw, dict) else {},
    }


def _extract_action_scores(slide_action: object) -> tuple[float | None, dict]:
    """Return (confidence, probabilities) from a slide_action answer."""
    confidence: float | None = None
    probs: dict = {}
    if isinstance(slide_action, dict):
        for key in ("confidence", "conf", "score"):
            val = slide_action.get(key)
            if isinstance(val, (int, float)):
                confidence = float(val)
                break
        raw_probs = slide_action.get("probabilities")
        if isinstance(raw_probs, dict):
            probs = {
                str(k): float(v)
                for k, v in raw_probs.items()
                if isinstance(v, (int, float))
            }
            if probs:
                best = max(probs.values())
                confidence = best if confidence is None else max(confidence, best)
    return confidence, probs


def parse_decision_payload(
    raw: object,
    topic_p: float = 0.6,
    action_conf: float = 0.55,
    new_conf: float = 0.68,
    has_current_slide: bool = False,
) -> dict:
    """Parse a Decisions response into {relevant, action, reason, raw, ...}.

    Pure function: no IO, no env, never raises. Anything unexpected degrades
    to conservative fail-open (no current slide -> new, with one -> keep)
    so the live flow never stalls.

    Thresholds are differentiated: keep/update need ``action_conf`` while
    new needs the stricter ``new_conf``. A below-threshold new downgrades
    to keep when there is a base slide, else to new.
    Calibration fields (on_topic_p, confidence, probabilities) ride along
    for logs without any PII.
    """
    try:
        if not isinstance(raw, dict):
            return _fail_open("invalid-schema", raw, has_current_slide)
        answers = raw.get("answers")
        if not isinstance(answers, dict):
            answers = raw

        # --- on_topic -> relevant (noul probability threshold or boolean) ---
        # Official shape: answers.on_topic = {type, noul: prob 0-1}.
        on_topic = answers.get("on_topic")
        relevant = True
        on_topic_p: float | None = None
        if isinstance(on_topic, bool):
            relevant = on_topic
            on_topic_p = 1.0 if on_topic else 0.0
        elif isinstance(on_topic, dict):
            prob: float | None = None
            if "noul" in on_topic and isinstance(on_topic.get("noul"), (int, float)):
                prob = float(on_topic["noul"])
            else:
                for key in ("probability", "p", "score"):
                    val = on_topic.get(key)
                    if isinstance(val, (int, float)):
                        prob = float(val)
                        break
            if prob is not None:
                on_topic_p = prob
                relevant = prob >= topic_p
            else:
                voted: bool | None = None
                for key in ("noul", "relevant", "on_topic", "value", "answer", "is_relevant"):
                    if key in on_topic:
                        voted = _as_optional_bool(on_topic[key])
                        if voted is not None:
                            break
                relevant = voted if voted is not None else True
        elif on_topic is not None:
            voted = _as_optional_bool(on_topic)
            relevant = voted if voted is not None else True

        # --- slide_action -> keep/update/new (confidence thresholds) ---
        slide_action = answers.get("slide_action")
        choice = "new"
        confidence: float | None = None
        probs: dict = {}
        if isinstance(slide_action, str):
            choice = slide_action.strip().lower()
        elif isinstance(slide_action, dict):
            for key in ("choice", "action", "value", "answer"):
                val = slide_action.get(key)
                if isinstance(val, str) and val.strip():
                    choice = val.strip().lower()
                    break
            confidence, probs = _extract_action_scores(slide_action)
        if choice not in _VALID_ACTIONS:
            return _fail_open("invalid-choice", raw, has_current_slide)
        if confidence is not None and confidence < action_conf:
            return _fail_open("low-confidence", raw, has_current_slide)
        if not relevant:
            return {"relevant": False, "action": "keep", "reason": "off-topic",
                    "raw": raw, "on_topic_p": on_topic_p,
                    "confidence": confidence, "probabilities": probs}
        if choice == "new" and confidence is not None and confidence < new_conf:
            if not has_current_slide:
                return {"relevant": True, "action": "new",
                        "reason": "jev:new-weak-no-base", "raw": raw,
                        "on_topic_p": on_topic_p, "confidence": confidence,
                        "probabilities": probs}
            return {"relevant": True, "action": "keep",
                    "reason": "jev:keep-downgraded", "raw": raw,
                    "on_topic_p": on_topic_p, "confidence": confidence,
                    "probabilities": probs}
        return {"relevant": True, "action": choice, "reason": f"jev:{choice}",
                "raw": raw, "on_topic_p": on_topic_p,
                "confidence": confidence, "probabilities": probs}
    except Exception:  # noqa: BLE001 - parse must never raise
        return _fail_open("parse-error", raw, has_current_slide)


def _has_base_slide(slide_actual: object) -> bool:
    """True when there is a current slide to keep/update onto."""
    if not isinstance(slide_actual, dict):
        return False
    for key in ("titulo", "title", "resumen", "text", "layout"):
        if str(slide_actual.get(key) or "").strip():
            return True
    return False


def _extract_scores(raw: object) -> tuple[str, str, str]:
    """Return (on_topic_p, confidence, probs) as short strings without PII."""
    on_p, conf, probs_s = "n/a", "n/a", "n/a"
    try:
        answers = raw.get("answers") if isinstance(raw, dict) else None
        if not isinstance(answers, dict):
            answers = raw if isinstance(raw, dict) else {}
        on_topic = answers.get("on_topic")
        if isinstance(on_topic, bool):
            on_p = "1" if on_topic else "0"
        elif isinstance(on_topic, dict):
            for key in ("noul", "probability", "p", "score"):
                val = on_topic.get(key)
                if isinstance(val, (int, float)):
                    on_p = f"{float(val):.2f}"
                    break
        slide_action = answers.get("slide_action")
        if isinstance(slide_action, dict):
            for key in ("confidence", "conf", "score"):
                val = slide_action.get(key)
                if isinstance(val, (int, float)):
                    conf = f"{float(val):.2f}"
                    break
            else:
                probs = slide_action.get("probabilities")
                if isinstance(probs, dict) and probs:
                    nums = [float(v) for v in probs.values() if isinstance(v, (int, float))]
                    if nums:
                        conf = f"{max(nums):.2f}"
            probs = slide_action.get("probabilities")
            if isinstance(probs, dict) and probs:
                parts = []
                for key in ("keep", "update", "new"):
                    val = probs.get(key)
                    if isinstance(val, (int, float)):
                        parts.append(f"{key}={float(val):.2f}")
                if parts:
                    probs_s = ",".join(parts)
    except Exception:  # noqa: BLE001 - logging never breaks the gate
        pass
    return on_p, conf, probs_s


def _emit_jev_line(
    action: str, on_p: str, conf: str, latency_ms: int, cost: object,
    probs_s: str = "n/a",
) -> None:
    print(
        f"[jev] action={action} on_topic_p={on_p} confidence={conf} "
        f"probs={probs_s} latency_ms={latency_ms} cost={cost}",
        flush=True,
    )


def _emit_fail_open(
    reason: str,
    latency_ms: int,
    action: str = "new",
    conf: str = "n/a",
    probs_s: str = "n/a",
) -> None:
    short = str(reason or "error")[:40].replace("\n", " ")
    print(
        f"[jev] fail-open action={action} reason={short} "
        f"confidence={conf} probs={probs_s} latency_ms={latency_ms}",
        flush=True,
    )


def decide_slide_action(
    topic: str,
    keywords: list | None,
    audience: str,
    texto_turno: str,
    slide_actual: dict | None,
    historial_reciente: list | None = None,
    transcripcion_reciente: list | str | None = None,
) -> dict:
    """Ask Jev for one gate decision. Never raises (fail-open on any issue).

    Fail-open is conservative: without a current slide it returns new,
    with one it returns keep, so the live flow never stalls nor wipes.
    """
    cfg = get_jev_config()
    start = time.perf_counter()
    has_base = _has_base_slide(slide_actual)
    if historial_reciente is None and isinstance(slide_actual, dict):
        historial_reciente = slide_actual.get("historial_reciente")
    if transcripcion_reciente is None and isinstance(slide_actual, dict):
        transcripcion_reciente = slide_actual.get("transcripcion_reciente")
    if not cfg["api_key"]:
        _emit_fail_open("missing-key", 0, "keep" if has_base else "new")
        return _fail_open("missing-key", {}, has_base)
    payload = build_payload(topic, keywords, audience, texto_turno, slide_actual,
                            model=cfg["model"], historial_reciente=historial_reciente,
                            transcripcion_reciente=transcripcion_reciente)
    try:
        resp = httpx.post(
            JEV_DECISIONS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            timeout=cfg["timeout_s"],
        )
    except Exception as exc:  # noqa: BLE001 - timeouts/network map to fail-open
        latency_ms = int((time.perf_counter() - start) * 1000)
        exc_name = type(exc).__name__
        kind = "timeout" if "imeout" in exc_name else f"net-{exc_name.lower()}"[:40]
        _emit_fail_open(kind, latency_ms, "keep" if has_base else "new")
        return _fail_open(kind, {}, has_base)
    if resp.status_code >= 400:
        reason = f"http_{resp.status_code}"
        _emit_fail_open(reason, int((time.perf_counter() - start) * 1000),
                        "keep" if has_base else "new")
        return _fail_open(reason, {}, has_base)
    try:
        raw = resp.json()
    except Exception:  # noqa: BLE001
        _emit_fail_open("invalid-json", int((time.perf_counter() - start) * 1000),
                        "keep" if has_base else "new")
        return _fail_open("invalid-json", {}, has_base)
    result = parse_decision_payload(raw, cfg["topic_p"], cfg["action_conf"],
                                    cfg["new_conf"], has_base)
    latency_ms = int((time.perf_counter() - start) * 1000)
    try:
        usage = raw.get("usage") if isinstance(raw, dict) else None
        cost = usage.get("cost") if isinstance(usage, dict) else None
        reason = str(result.get("reason") or "")
        if reason.startswith("fail-open:"):
            suffix = reason.split("fail-open:", 1)[1].strip() or "error"
            on_p, conf, probs_s = _extract_scores(raw)
            _emit_fail_open(suffix, latency_ms, str(result.get("action") or "new"),
                            conf, probs_s)
        else:
            on_p, conf, probs_s = _extract_scores(raw)
            _emit_jev_line(str(result.get("action") or "new"), on_p, conf,
                           latency_ms, cost, probs_s)
    except Exception:  # noqa: BLE001 - logging never breaks the gate
        pass
    return result
