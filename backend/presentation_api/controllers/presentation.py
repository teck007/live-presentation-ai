"""Controller presentation: genera slides JSON desde transcripción + LLM."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.presentation_api.utils.auth import require_auth

from backend.presentation_api.utils.image_generation import generate_image
from backend.presentation_api.utils.llm_client import (
    VALID_LAYOUTS,
    generate_slide,
    normalize_audience,
)
from backend.presentation_api.utils.palettes import resolve_palette
from backend.presentation_api.utils.slide_designs import (
    build_fast_prompt,
    list_designs,
    render_slide_html,
    should_generate_image,
    validate_slide,
)
from backend.presentation_api.utils.topic_cleaner import analyze_topic

router = APIRouter(prefix="/presentations", tags=["presentations"])


class GenerateSlideRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=2000)
    topic: str = Field(default="", max_length=300)
    keywords: list[str] = Field(default_factory=list, max_length=10)
    palette_id: str | None = None
    audience: str | None = None
    is_opening: bool | None = None


class GenerateSlideResponse(BaseModel):
    layout: str
    title: str
    text: str
    bullets: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    filtered: bool = False
    kicker: str = ""
    subtitle: str = ""
    cards: list = Field(default_factory=list)
    stats: list = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
    steps: list = Field(default_factory=list)
    code: str = ""
    code_tipo: str = ""
    code_titulo: str = ""
    codigo_matematica: dict | None = None
    image: str = ""
    imagen_hashtag: str = ""
    imagen_prompt: str = ""
    explanation: str = ""
    concept: str = ""
    example: str = ""
    takeaway: str = ""
    content_type: str = ""
    layout_reason: str = ""
    titulo: str = ""
    texto: str = ""
    listado: list[str] = Field(default_factory=list)
    conceptos: list = Field(default_factory=list)
    html: str = ""
    palette_id: str = ""
    palette: dict | None = None


@router.get("/health")
def health():
    return {"status": "ok", "domain": "presentations"}


@router.get("/live-session")
def live_session_status(user: dict = Depends(require_auth)):
    """Resume check for the current user (no UI yet, minimal for slice 1)."""
    from datetime import datetime, timezone

    from backend.presentation_api.utils.live_sessions import (
        get_display_scale,
        get_latest_for_user,
        slide_count,
    )

    entry = get_latest_for_user(user.get("user_id") or "dev-local")
    if entry is None:
        return {
            "has_saved": False,
            "live_session_id": None,
            "topic": "",
            "slide_count": 0,
            "displayScale": 1.0,
            "updated_at": None,
        }
    try:
        updated_at = datetime.fromtimestamp(
            float(entry.get("updated_at") or 0), tz=timezone.utc
        ).isoformat()
    except (TypeError, ValueError, OSError):
        updated_at = None
    return {
        "has_saved": True,
        "live_session_id": entry.get("live_session_id"),
        "topic": entry.get("topic") or "",
        "slide_count": slide_count(entry),
        "displayScale": get_display_scale(entry),
        "updated_at": updated_at,
    }


@router.get("/live-session/{live_session_id}/slides")
def live_session_slides(live_session_id: str, user: dict = Depends(require_auth)):
    """Full ordered slides for visual restore (Continuar paints canvas).

    Ownership is (user_id from JWT, live_session_id path) only.
    Returns {live_session_id, topic, slides:[...], updated_at}.
    404 when unknown or expired. No user_id is ever echoed.
    """
    from datetime import datetime, timezone

    from backend.presentation_api.utils.live_sessions import get as live_get, get_display_scale, ordered_slides

    user_id = str(user.get("user_id") or "dev-local")
    entry = live_get(user_id, str(live_session_id or "").strip())
    if entry is None:
        raise HTTPException(status_code=404, detail="Live session not found or expired.")
    try:
        updated_at = datetime.fromtimestamp(
            float(entry.get("updated_at") or 0), tz=timezone.utc
        ).isoformat()
    except (TypeError, ValueError, OSError):
        updated_at = None
    palette = entry.get("palette") if isinstance(entry.get("palette"), dict) else None
    palette_id = str(entry.get("palette_id") or "")
    if not palette_id and isinstance(palette, dict):
        palette_id = str(palette.get("id") or "")
    audience = str(entry.get("audience") or "general") or "general"
    topic = str(entry.get("topic") or "")

    def _str_list(value: object, limit: int = 4) -> list:
        if not isinstance(value, list):
            return []
        return [str(v) for v in value if isinstance(v, str) and str(v).strip()][:limit]

    slides: list[dict] = []
    for env in ordered_slides(entry):
        raw = env.get("slide") if isinstance(env, dict) else None
        if not isinstance(raw, dict):
            continue
        sid = str(env.get("id") or "")
        try:
            seq = int(env.get("seq") or 0)
        except (TypeError, ValueError):
            seq = 0
        try:
            version = int(env.get("topic_version")
                          or entry.get("topic_version") or 1)
        except (TypeError, ValueError):
            version = 1
        html = str(raw.get("html") or "")
        if not html:
            try:
                html = render_slide_html(raw, palette) or ""
            except Exception:  # noqa: BLE001 - fail-open without html
                html = ""
        cm = raw.get("codigo_matematica")
        if not isinstance(cm, dict):
            cm = None
        title = str(raw.get("title") or raw.get("titulo") or "")
        text = str(raw.get("text") or raw.get("texto") or "")
        bullets = _str_list(raw.get("bullets"))
        listado_raw = raw.get("listado") if isinstance(raw.get("listado"), list) else raw.get("bullets")
        slides.append({
            "id": sid,
            "seq": seq,
            "topicVersion": version,
            "layout": str(raw.get("layout") or "title_text"),
            "title": title,
            "titulo": str(raw.get("titulo") or title),
            "text": text,
            "texto": str(raw.get("texto") or text),
            "bullets": bullets,
            "listado": _str_list(listado_raw),
            "keywords": _str_list(raw.get("keywords"), 5),
            "kicker": str(raw.get("kicker") or ""),
            "subtitle": str(raw.get("subtitle") or ""),
            "cards": list(raw.get("cards") or [])[:4] if isinstance(raw.get("cards"), list) else [],
            "conceptos": list(raw.get("conceptos") or [])[:4] if isinstance(raw.get("conceptos"), list) else [],
            "stats": list(raw.get("stats") or [])[:4] if isinstance(raw.get("stats"), list) else [],
            "chips": _str_list(raw.get("chips")),
            "steps": list(raw.get("steps") or [])[:4] if isinstance(raw.get("steps"), list) else [],
            "code": str(raw.get("code") or ""),
            "code_tipo": str(raw.get("code_tipo") or ""),
            "code_titulo": str(raw.get("code_titulo") or ""),
            "codigo_matematica": cm,
            "image": str(raw.get("image") or ""),
            "imagen_hashtag": str(raw.get("imagen_hashtag") or ""),
            "imagen_prompt": str(raw.get("imagen_prompt") or ""),
            "explanation": str(raw.get("explanation") or ""),
            "concept": str(raw.get("concept") or ""),
            "example": str(raw.get("example") or ""),
            "takeaway": str(raw.get("takeaway") or ""),
            "content_type": str(raw.get("content_type") or ""),
            "layout_reason": str(raw.get("layout_reason") or ""),
            "audience": audience,
            "html": html,
            "palette_id": palette_id,
            "palette": palette,
        })
    return {
        "live_session_id": str(entry.get("live_session_id") or live_session_id),
        "topic": topic,
        "slides": slides,
        "displayScale": get_display_scale(entry),
        "updated_at": updated_at,
    }


@router.delete("/live-session/{live_session_id}")
def discard_live_session(live_session_id: str, user: dict = Depends(require_auth)):
    """Discard one saved live session for the current user."""
    from backend.presentation_api.utils.live_sessions import discard

    removed = discard(user.get("user_id") or "dev-local", live_session_id or "")
    return {"discarded": bool(removed)}


@router.get("/layouts")
def layouts():
    return {"layouts": list_designs()}


@router.post("/generate", response_model=GenerateSlideResponse)
async def generate(req: GenerateSlideRequest, user: dict = Depends(require_auth)):
    from backend.presentation_api.utils.trial import is_trial_active, trial_expires_at

    if not is_trial_active(user):
        raise HTTPException(
            status_code=403,
            detail=(
                "Tu prueba gratuita finalizó "
                f"(venció {trial_expires_at(user).isoformat()}). "
                "Escríbenos por el formulario de contacto y la extendemos."
            ),
        )
    transcript = req.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript vacío.")
    topic = (req.topic or "").strip()
    keywords = [k.strip() for k in (req.keywords or []) if k.strip()][:10]

    # Palette: one random per session unless the client pins an id.
    palette = resolve_palette(req.palette_id)
    palette_id = str(palette.get("id", "") or "")

    # Si no hay keywords, derivarlas del transcript para el LLM.
    if not keywords:
        keywords = analyze_topic(transcript).get("keywords", [])

    audience = normalize_audience(req.audience)

    # El LLM decide en esta misma respuesta si corresponde al tema principal.
    # Non-blocking: sync OpenAI client runs in a worker thread (same as WS path),
    # so the event loop stays free. Client timeout (LLM_TIMEOUT_S, default 15s)
    # bounds the call; elapsed is logged by generate_slide itself.
    is_open = bool(req.is_opening)
    slide = await asyncio.to_thread(
        generate_slide, transcript, topic, keywords, audience, None, is_open
    )
    if slide.get("filtered") is True or slide.get("relevant") is False:
        return GenerateSlideResponse(
            layout="title_text",
            title="",
            text="",
            bullets=[],
            keywords=keywords,
            filtered=True,
            html="",
            palette_id=palette_id,
            palette=palette,
        )
    v = validate_slide(slide, is_opening=is_open)
    layout = v.get("layout") if v.get("layout") in VALID_LAYOUTS else "title_text"
    html_snippet = render_slide_html(v, palette, is_opening=is_open)
    # Vivo efímero: si corresponde imagen, intento corto fail-open y re-render.
    # REST returns the text slide fast: short outer timeout (<10s, inner is 25s)
    # so the response never blocks on image generation. WS stays progressive
    # via background _run_image_task + slide_image_updated patch instead.
    if should_generate_image(layout, v.get("imagen_prompt")):
        try:
            fast_prompt = build_fast_prompt(
                v.get("title"), v.get("imagen_prompt"), v.get("imagen_hashtag")
            )
            url = await asyncio.wait_for(generate_image(fast_prompt), timeout=8.0)
            if url:
                v["image"] = url
                html_snippet = render_slide_html(v, palette, is_opening=is_open)
        except Exception:  # noqa: BLE001 - placeholder inmediato si falla
            pass
    cm = v.get("codigo_matematica") if isinstance(v.get("codigo_matematica"), dict) else None
    return GenerateSlideResponse(
        layout=layout,
        title=str(v.get("title") or "En vivo")[:120],
        text=str(v.get("text") or "")[:900],
        bullets=[b for b in list(v.get("bullets") or []) if isinstance(b, str)][:4],
        keywords=[str(k) for k in list(v.get("keywords") or keywords)][:5],
        filtered=False,
        kicker=str(v.get("kicker") or ""),
        subtitle=str(v.get("subtitle") or ""),
        cards=list(v.get("cards") or [])[:4],
        stats=list(v.get("stats") or [])[:4],
        chips=[str(c) for c in list(v.get("chips") or []) if isinstance(c, str)][:4],
        steps=list(v.get("steps") or [])[:4],
        code=str(v.get("code") or ""),
        code_tipo=str(v.get("code_tipo") or ""),
        code_titulo=str(v.get("code_titulo") or ""),
        codigo_matematica=cm,
        image=str(v.get("image") or ""),
        imagen_hashtag=str(v.get("imagen_hashtag") or ""),
        imagen_prompt=str(v.get("imagen_prompt") or ""),
        explanation=str(v.get("explanation") or "")[:900],
        concept=str(v.get("concept") or ""),
        example=str(v.get("example") or ""),
        takeaway=str(v.get("takeaway") or ""),
        content_type=str(v.get("content_type") or ""),
        layout_reason=str(v.get("layout_reason") or ""),
        titulo=str(v.get("titulo") or v.get("title") or "")[:120],
        texto=str(v.get("texto") or v.get("text") or "")[:900],
        listado=[b for b in list(v.get("listado") or v.get("bullets") or []) if isinstance(b, str)][:4],
        conceptos=list(v.get("conceptos") or [])[:4],
        html=html_snippet,
        palette_id=palette_id,
        palette=palette,
    )
