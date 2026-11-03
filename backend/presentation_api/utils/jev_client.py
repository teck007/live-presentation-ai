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
    "Given the current slide and the turn text, choose: keep if the current "
    "slide already covers the turn and there is nothing new to paint; update "
    "if the turn refines, corrects or extends the current slide and it is "
    "worth regenerating it fusing context; new if the turn brings new content "
    "that deserves its own slide."
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
    timeout_ms = _read_int("JEV_TIMEOUT_MS", 2500, 250, 30000)
    return {
        "model": os.getenv("JEV_MODEL", JEV_MODEL_DEFAULT).strip() or JEV_MODEL_DEFAULT,
        "api_key": os.getenv("OPENROUTER_API_KEY", "").strip(),
        "topic_p": _read_float("JEV_TOPIC_P", 0.6, 0.0, 1.0),
        "action_conf": _read_float("JEV_ACTION_CONF", 0.65, 0.0, 1.0),
        "timeout_s": timeout_ms / 1000.0,
    }


def build_payload(
    topic: str,
    keywords: list | None,
    audience: str,
    texto_turno: str,
    slide_actual: dict | None,
    model: str = JEV_MODEL_DEFAULT,
) -> dict:
    """Build the Decisions request payload (pure, no IO, no env).

    Official schema: ``questions`` is a DICT keyed by id, each entry uses
    the ``type`` field (``noul`` or ``choice``), and choice options come
    only from the keys of the ``criteria`` dict (no ``options`` array).
    """
    actual = slide_actual if isinstance(slide_actual, dict) else {}
    return {
        "model": model or JEV_MODEL_DEFAULT,
        "state": {
            "tema_principal": topic or "",
            "keywords": list(keywords or [])[:10],
            "audiencia": (audience or "general").strip() or "general",
            "texto_turno": texto_turno or "",
            "slide_actual": {
                "titulo": str(actual.get("titulo") or "")[:120],
                "resumen": str(actual.get("resumen") or "")[:300],
            },
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
                    "keep": "The current slide already covers the turn; nothing new to paint.",
                    "update": "The turn refines, corrects or extends the current slide; regenerate fused.",
                    "new": "The turn brings new content that deserves its own slide.",
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


def _fail_open(reason: str, raw: object) -> dict:
    return {
        "relevant": True,
        "action": "new",
        "reason": f"fail-open: {reason}",
        "raw": raw if isinstance(raw, dict) else {},
    }


def parse_decision_payload(
    raw: object,
    topic_p: float = 0.6,
    action_conf: float = 0.65,
) -> dict:
    """Parse a Decisions response into {relevant, action, reason, raw}.

    Pure function: no IO, no env, never raises. Anything unexpected degrades
    to fail-open (relevant=True, action="new") so the live flow never stalls.
    """
    try:
        if not isinstance(raw, dict):
            return _fail_open("invalid-schema", raw)
        answers = raw.get("answers")
        if not isinstance(answers, dict):
            answers = raw

        # --- on_topic -> relevant (noul probability threshold or boolean) ---
        # Official shape: answers.on_topic = {type, noul: prob 0-1}.
        on_topic = answers.get("on_topic")
        relevant = True
        if isinstance(on_topic, bool):
            relevant = on_topic
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

        # --- slide_action -> keep/update/new (confidence threshold) ---
        slide_action = answers.get("slide_action")
        choice = "new"
        confidence: float | None = None
        if isinstance(slide_action, str):
            choice = slide_action.strip().lower()
        elif isinstance(slide_action, dict):
            for key in ("choice", "action", "value", "answer"):
                val = slide_action.get(key)
                if isinstance(val, str) and val.strip():
                    choice = val.strip().lower()
                    break
            for key in ("confidence", "conf", "score"):
                val = slide_action.get(key)
                if isinstance(val, (int, float)):
                    confidence = float(val)
                    break
            probs = slide_action.get("probabilities")
            if isinstance(probs, dict) and probs:
                nums = [float(v) for v in probs.values() if isinstance(v, (int, float))]
                if nums:
                    best = max(nums)
                    confidence = best if confidence is None else max(confidence, best)
        if choice not in _VALID_ACTIONS:
            return _fail_open("invalid-choice", raw)
        if confidence is not None and confidence < action_conf:
            return _fail_open("low-confidence", raw)
        if not relevant:
            return {"relevant": False, "action": "keep", "reason": "off-topic", "raw": raw}
        return {"relevant": True, "action": choice, "reason": f"jev:{choice}", "raw": raw}
    except Exception:  # noqa: BLE001 - parse must never raise
        return _fail_open("parse-error", raw)


def _extract_scores(raw: object) -> tuple[str, str]:
    """Return (on_topic_p, confidence) as short strings without PII."""
    on_p, conf = "n/a", "n/a"
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
    except Exception:  # noqa: BLE001 - logging never breaks the gate
        pass
    return on_p, conf


def _emit_jev_line(
    action: str, on_p: str, conf: str, latency_ms: int, cost: object
) -> None:
    print(
        f"[jev] action={action} on_topic_p={on_p} confidence={conf} "
        f"latency_ms={latency_ms} cost={cost}",
        flush=True,
    )


def _emit_fail_open(reason: str, latency_ms: int) -> None:
    short = str(reason or "error")[:40].replace("\n", " ")
    print(f"[jev] fail-open reason={short} latency_ms={latency_ms}", flush=True)


def decide_slide_action(
    topic: str,
    keywords: list | None,
    audience: str,
    texto_turno: str,
    slide_actual: dict | None,
) -> dict:
    """Ask Jev for one gate decision. Never raises (fail-open on any issue)."""
    cfg = get_jev_config()
    start = time.perf_counter()
    if not cfg["api_key"]:
        _emit_fail_open("missing-key", 0)
        return _fail_open("missing-key", {})
    payload = build_payload(topic, keywords, audience, texto_turno, slide_actual, model=cfg["model"])
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
        _emit_fail_open(kind, latency_ms)
        return _fail_open("request-error", {})
    if resp.status_code >= 400:
        _emit_fail_open(f"http_{resp.status_code}", int((time.perf_counter() - start) * 1000))
        return _fail_open("http-status", {})
    try:
        raw = resp.json()
    except Exception:  # noqa: BLE001
        _emit_fail_open("schema", int((time.perf_counter() - start) * 1000))
        return _fail_open("invalid-json", {})
    result = parse_decision_payload(raw, cfg["topic_p"], cfg["action_conf"])
    latency_ms = int((time.perf_counter() - start) * 1000)
    try:
        usage = raw.get("usage") if isinstance(raw, dict) else None
        cost = usage.get("cost") if isinstance(usage, dict) else None
        reason = str(result.get("reason") or "")
        if reason.startswith("fail-open:"):
            suffix = reason.split("fail-open:", 1)[1].strip() or "error"
            if "invalid" in suffix or "schema" in suffix or "parse" in suffix:
                suffix = "schema"
            elif "timeout" in suffix or "low-confidence" in suffix:
                suffix = suffix if "timeout" in suffix else "error"
            _emit_fail_open(suffix, latency_ms)
        else:
            on_p, conf = _extract_scores(raw)
            _emit_jev_line(str(result.get("action") or "new"), on_p, conf, latency_ms, cost)
    except Exception:  # noqa: BLE001 - logging never breaks the gate
        pass
    return result
