"""Controller presentation: genera slides JSON desde transcripción + LLM."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


@router.get("/layouts")
def layouts():
    return {"layouts": list_designs()}


@router.post("/generate", response_model=GenerateSlideResponse)
async def generate(req: GenerateSlideRequest):
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
    is_open = bool(req.is_opening)
    slide = generate_slide(transcript, topic, keywords, audience, None, is_opening=is_open)
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
    if should_generate_image(layout, v.get("imagen_prompt")):
        try:
            fast_prompt = build_fast_prompt(
                v.get("title"), v.get("imagen_prompt"), v.get("imagen_hashtag")
            )
            url = await asyncio.wait_for(generate_image(fast_prompt), timeout=20.0)
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
