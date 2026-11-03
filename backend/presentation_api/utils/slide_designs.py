"""Slide designs catalog: single source of truth for layouts.

Pure functions + html.escape. No secrets, no network calls.
"""
import html

GRID_RULE = {
    2: "md:grid-cols-2",
    3: "md:grid-cols-3",
    4: "md:grid-cols-2 xl:grid-cols-4",
}

SLIDE_DESIGNS = {
    "hero_cover": {
        "label": "Hero cover",
        "description_for_llm": "ONLY opening cover (first slide of session) or first slide after main topic change. NEVER for illustrative images mid-topic.",
        "fields": ["kicker", "title", "subtitle"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "cards_flex": {
        "label": "Cards grid",
        "description_for_llm": "Use when there are 2-4 parallel ideas, each with short title + text.",
        "fields": ["title", "cards"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "split_code": {
        "label": "Split code",
        "description_for_llm": "Use for code, command, formula or technical snippet next to explanation.",
        "fields": ["title", "text", "code"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "split_media": {
        "label": "Split media",
        "description_for_llm": "Default for any visualizable content mid-topic: title+text left, image placeholder right.",
        "fields": ["title", "text", "image"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "separator": {
        "label": "Separator",
        "description_for_llm": "Use for topic change, pause, or section break with one short line.",
        "fields": ["title", "text"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "compare_2": {
        "label": "Compare",
        "description_for_llm": "Use for 2-way comparison (vs, pros/cons, before/after); up to 3 max.",
        "fields": ["title", "cards"],
        "layout_mode": "fixed",
        "min_items": 2,
        "max_items": 3,
    },
    "checklist_flex": {
        "label": "Checklist",
        "description_for_llm": "Use for 2-4 tasks, steps to verify, or requirements list.",
        "fields": ["title", "bullets"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "stats_flex": {
        "label": "Stats",
        "description_for_llm": "Use for 2-4 metrics or numbers with short labels.",
        "fields": ["title", "stats"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "chips_flex": {
        "label": "Chips",
        "description_for_llm": "Use for 2-4 keywords, tags, or short concepts without long text.",
        "fields": ["title", "chips"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "bullets_flex": {
        "label": "Bullets",
        "description_for_llm": "Use for 2-4 short bullet points expanding one title (default list).",
        "fields": ["title", "text", "bullets"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "steps_flex": {
        "label": "Steps",
        "description_for_llm": "Use for 2-4 ordered steps of a process in sequence.",
        "fields": ["title", "steps"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "quote": {
        "label": "Quote",
        "description_for_llm": "Use for a single striking quote or key phrase.",
        "fields": ["title", "text"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "definition_guided": {
        "label": "Definition guided",
        "description_for_llm": "Use to define one concept: concept in 1 line, explanation in 1-2 sentences, plus a short real example. Professional deck tone; pick when the turn introduces or clarifies a single term.",
        "fields": ["title", "concept", "explanation", "example"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "concept_editorial": {
        "label": "Concept editorial",
        "description_for_llm": "Use for one big idea with editorial emphasis: concept as headline, explanation as short body, optional takeaway line. Pick when the turn states a key insight, not a process or list.",
        "fields": ["title", "concept", "explanation", "takeaway"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "pillars_3": {
        "label": "Pillars 3",
        "description_for_llm": "Use for exactly 3 parallel pillars or foundations of one idea, each card with short title + text. Pick when the turn lists three supporting ideas of equal weight.",
        "fields": ["title", "cards"],
        "layout_mode": "flexible",
        "min_items": 3,
        "max_items": 3,
    },
    "timeline_4": {
        "label": "Timeline 4",
        "description_for_llm": "Use for 2-4 chronological milestones or evolution stages in order. Pick when the turn describes a progression over time, not a how-to process (that is steps_flex).",
        "fields": ["title", "steps"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "takeaway": {
        "label": "Takeaway",
        "description_for_llm": "Use for one actionable closing message the audience should remember or do. Pick when the turn ends with a conclusion, call to action, or memorable lesson.",
        "fields": ["title", "takeaway"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "stat_hero": {
        "label": "Stat hero",
        "description_for_llm": "Use to spotlight a single explicit number from the transcript with a short label. Pick when one metric deserves the whole slide; never invent numbers.",
        "fields": ["title", "stats", "text"],
        "layout_mode": "fixed",
        "min_items": 1,
        "max_items": 1,
    },
    # Backward-compat aliases (old clients / LLM ids still valid).
    "title_text": {
        "label": "Title + text (compat)",
        "description_for_llm": "Simple title with 1-2 sentence explanation.",
        "fields": ["title", "text"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
    "title_bullets": {
        "label": "Title + bullets (compat)",
        "description_for_llm": "Alias of bullets_flex: title with 2-4 short bullets.",
        "fields": ["title", "text", "bullets"],
        "layout_mode": "flexible",
        "min_items": 2,
        "max_items": 4,
    },
    "text_image": {
        "label": "Text + image (compat)",
        "description_for_llm": "Alias of split_media: text describing something visualizable.",
        "fields": ["title", "text", "image"],
        "layout_mode": "fixed",
        "min_items": 0,
        "max_items": 0,
    },
}

VALID_LAYOUTS = tuple(SLIDE_DESIGNS.keys())

# Compat aliases resolve to their canonical layout for rendering.
ALIAS_MAP = {
    "title_bullets": "bullets_flex",
    "text_image": "split_media",
}

_LIST_FIELDS = ("bullets", "keywords", "chips", "steps")
_MAX_LIST = 4

# Closed icon vocabulary for conceptos. Only these names are accepted;
# free SVG/HTML in icono is rejected (fallback None). Each maps to inline SVG.
ICON_CATALOG = (
    "idea",
    "libro",
    "codigo",
    "grafico",
    "lupa",
    "lista",
    "check",
    "alerta",
    "estrella",
    "chat",
)

_ICON_SVGS = {
    "idea": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="9" r="5"/><path d="M9 14l-1 5h8l-1-5M10 21h4"/></svg>',
    "libro": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2V5z"/><path d="M4 19a2 2 0 012-2h13"/></svg>',
    "codigo": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 9l-4 3 4 3M16 9l4 3-4 3M13 5l-2 14"/></svg>',
    "grafico": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/></svg>',
    "lupa": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
    "lista": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1.2" fill="currentColor"/><circle cx="4" cy="12" r="1.2" fill="currentColor"/><circle cx="4" cy="18" r="1.2" fill="currentColor"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M4 12l5 5L20 6"/></svg>',
    "alerta": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3L2 20h20L12 3z"/><path d="M12 10v4M12 17.5v.5"/></svg>',
    "estrella": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-3-5.4 3 1.1-6L3.2 9.4l6.1-.8L12 3z"/></svg>',
    "chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 5h16v11H9l-5 4V5z"/></svg>',
}

_VALID_CODE_TIPOS = ("codigo", "matematica")


def _esc(value: object, limit: int) -> str:
    return html.escape(str(value or ""), quote=True)[:limit]


def _esc_icon(value: object) -> str | None:
    v = str(value or "").strip().lower()
    return v if v in ICON_CATALOG else None


def _esc_hashtag(value: object) -> str:
    # Tags EN, comma/space separated; strip HTML, keep plain tokens.
    raw = str(value or "").strip()
    if not raw:
        return ""
    cleaned = html.escape(raw, quote=True)[:200]
    return cleaned


def _sanitize_codigo_matematica(value: object) -> dict | None:
    """Sanitize {tipo, titulo, contenido}. Math is escaped, never executed."""
    if not isinstance(value, dict):
        return None
    tipo = str(value.get("tipo") or "").strip().lower()
    if tipo not in _VALID_CODE_TIPOS:
        return None
    contenido = str(value.get("contenido") or "").strip()
    if not contenido:
        return None
    titulo = str(value.get("titulo") or "").strip() or ("Ejemplo" if tipo == "codigo" else "Ejemplo")
    return {
        "tipo": tipo,
        "titulo": html.escape(titulo, quote=True)[:80],
        "contenido": html.escape(contenido, quote=True)[:1000],
    }


def _esc_list(items: object, limit_each: int = 140) -> list:
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        text = str(item).strip() if not isinstance(item, dict) else ""
        if isinstance(item, dict):
            # Cards/stats dicts: keep as escaped {title/text} or {value/label}.
            # Extended: preserve icon (closed enum) and per-card code dict.
            cleaned: dict = {}
            for key in ("title", "text", "value", "label"):
                if key in item and str(item[key]).strip():
                    cleaned[key] = html.escape(str(item[key]).strip(), quote=True)[:limit_each]
            icon = _esc_icon(item.get("icon") or item.get("icono"))
            if icon and ("title" in cleaned or "text" in cleaned):
                cleaned["icon"] = icon
            code_block = _sanitize_codigo_matematica(
                item.get("code") if isinstance(item.get("code"), dict)
                else item.get("codigo_matematica")
            )
            if code_block and ("title" in cleaned or "text" in cleaned):
                cleaned["code"] = code_block["contenido"]
                cleaned["code_tipo"] = code_block["tipo"]
                cleaned["code_titulo"] = code_block["titulo"]
            elif isinstance(item.get("code"), str) and str(item.get("code")).strip():
                if "title" in cleaned or "text" in cleaned:
                    cleaned["code"] = html.escape(str(item.get("code")).strip(), quote=True)[:1000]
            if cleaned:
                out.append(cleaned)
            continue
        if text:
            out.append(html.escape(text, quote=True)[:limit_each])
        if len(out) >= _MAX_LIST:
            break
    return out[:_MAX_LIST]


def list_designs_for_prompt() -> str:
    """Extended catalog for the LLM prompt: id + when-to-use + fields + items range."""
    parts = []
    for lid, spec in SLIDE_DESIGNS.items():
        fields = ",".join(spec["fields"])
        parts.append(
            f"{lid}: {spec['description_for_llm']} | fields: {fields} "
            f"| items: {spec['min_items']}-{spec['max_items']}"
        )
    return "; ".join(parts)


def list_designs() -> list:
    """Full catalog for GET /presentations/layouts."""
    return [
        {
            "id": lid,
            "label": spec["label"],
            "description": spec["description_for_llm"],
            "layout_mode": spec["layout_mode"],
            "min_items": spec["min_items"],
            "max_items": spec["max_items"],
            "fields": list(spec["fields"]),
            "grid_rule": dict(GRID_RULE),
        }
        for lid, spec in SLIDE_DESIGNS.items()
    ]


def _count_support(n_conceptos: int, n_listado: int, has_code: bool, has_image: bool) -> int:
    return (1 if n_conceptos > 0 else 0) + (1 if n_listado > 0 else 0) + (1 if has_code else 0) + (1 if has_image else 0)


def derive_layout(blocks: dict, is_opening: bool = False) -> str:
    """Deterministic layout from filled blocks (Spanish composite).

    blocks: {n_conceptos, has_concept_code, n_listado, has_code, has_image, has_texto}.
    Priority: opening-empty -> hero; conceptos+code -> compare/cards;
    conceptos -> cards; code alone -> split_code; image -> split_media;
    listado -> checklist; else title_text. Never hero unless opening.
    """
    try:
        n_con = int(blocks.get("n_conceptos") or 0)
    except (TypeError, ValueError):
        n_con = 0
    try:
        n_lis = int(blocks.get("n_listado") or 0)
    except (TypeError, ValueError):
        n_lis = 0
    has_concept_code = bool(blocks.get("has_concept_code"))
    has_code = bool(blocks.get("has_code"))
    has_image = bool(blocks.get("has_image"))
    if is_opening and n_con == 0 and n_lis == 0 and not has_code and not has_concept_code:
        return "hero_cover"
    if n_con >= 2 and has_concept_code:
        return "compare_2" if n_con == 2 else "cards_flex"
    if 2 <= n_con <= 4:
        return "cards_flex"
    if n_con == 1 and (has_code or has_concept_code or n_lis >= 2 or has_image):
        # Single concepto still rides with a richer section layout.
        if has_code or has_concept_code:
            return "split_code" if n_lis < 2 else "checklist_flex"
        if n_lis >= 2:
            return "checklist_flex"
        if has_image:
            return "split_media"
    if has_code and n_con == 0 and n_lis == 0:
        return "split_code"
    if has_code and n_lis >= 2:
        return "split_code"
    if has_image and n_con == 0 and n_lis == 0 and not has_code:
        return "split_media"
    if has_image and (n_con > 0 or n_lis >= 2 or has_code):
        # Image placeholder attaches as secondary section; base layout wins.
        if n_con >= 2:
            return "compare_2" if (n_con == 2 and has_concept_code) else "cards_flex"
        if has_code:
            return "split_code"
        if n_lis >= 2:
            return "checklist_flex"
        return "split_media"
    if n_lis >= 2:
        return "checklist_flex"
    return "title_text"


def _normalize_spanish(data: dict) -> dict:
    """Accept new Spanish composite keys + old English keys (compat)."""
    d = dict(data or {})
    # titulo -> title
    if not str(d.get("title") or "").strip() and str(d.get("titulo") or "").strip():
        d["title"] = d.get("titulo")
    # texto -> text / explanation
    if not str(d.get("text") or "").strip() and str(d.get("texto") or "").strip():
        d["text"] = d.get("texto")
    if not str(d.get("explanation") or "").strip() and str(d.get("texto") or "").strip():
        d["explanation"] = d.get("texto")
    # listado -> bullets
    if not isinstance(d.get("bullets"), list) or len([b for b in d["bullets"] if str(b).strip()]) == 0:
        if isinstance(d.get("listado"), list) and any(str(x).strip() for x in d["listado"]):
            d["bullets"] = d.get("listado")
    # conceptos -> cards (preserve icon + per-card codigo_matematica)
    raw_conceptos = d.get("conceptos")
    if isinstance(raw_conceptos, list) and raw_conceptos:
        cards: list = []
        for c in raw_conceptos[:4]:
            if isinstance(c, dict):
                cards.append({
                    "title": c.get("subtitulo") or c.get("title") or "",
                    "text": c.get("texto") or c.get("text") or "",
                    "icon": c.get("icono") if c.get("icono") is not None else c.get("icon"),
                    "codigo_matematica": c.get("codigo_matematica") if isinstance(c.get("codigo_matematica"), dict) else None,
                    "code": c.get("codigo_matematica") if isinstance(c.get("codigo_matematica"), dict) else c.get("code"),
                })
            elif str(c).strip():
                cards.append({"title": str(c).strip(), "text": ""})
        if cards and (not isinstance(d.get("cards"), list) or len(d.get("cards")) == 0):
            d["cards"] = cards
    # codigo_matematica (footer) -> code (+ metadata)
    if (not str(d.get("code") or "").strip()) and isinstance(d.get("codigo_matematica"), dict):
        cm = d.get("codigo_matematica")
        if isinstance(cm.get("contenido"), str) and cm.get("contenido").strip():
            d["code"] = cm.get("contenido")
            d["_code_tipo_raw"] = cm.get("tipo")
            d["_code_titulo_raw"] = cm.get("titulo")
    # imagen_hashtag stays as-is (sanitized later); English image stays for compat.
    return d


def validate_slide(data: dict, is_opening: bool = False) -> dict:
    """Validate + sanitize a slide dict. Never raises on bad input."""
    if not isinstance(data, dict):
        data = {}
    data = _normalize_spanish(data)
    raw_layout = data.get("layout")
    layout = raw_layout if raw_layout in SLIDE_DESIGNS else None
    title = _esc((data.get("title") or ""), 120).strip() or "En vivo"
    # Developed explanation: 3-5 sentences per audience (was 500/700).
    text = _esc(data.get("text") or "", 900)
    bullets = _esc_list(data.get("bullets"))
    keywords = _esc_list(data.get("keywords"), 60)
    keywords = keywords[:5]
    kicker = _esc(data.get("kicker") or "", 80) or ""
    subtitle = _esc(data.get("subtitle") or "", 200) or ""
    cards = _esc_list(data.get("cards"))
    stats = _esc_list(data.get("stats"))
    chips = _esc_list(data.get("chips"), 60)
    steps = _esc_list(data.get("steps"))
    image = _esc(data.get("image") or "", 500) or ""
    concept = _esc(data.get("concept") or "", 200) or ""
    explanation = _esc(data.get("explanation") or "", 900) or ""
    example = _esc(data.get("example") or "", 400) or ""
    takeaway = _esc(data.get("takeaway") or "", 200) or ""
    content_type = _esc(data.get("content_type") or "", 40) or ""
    layout_reason = _esc(data.get("layout_reason") or "", 200) or ""
    imagen_hashtag = _esc_hashtag(data.get("imagen_hashtag"))
    # Footer codigo_matematica: sanitize dict, keep code string for compat.
    codigo_block = _sanitize_codigo_matematica(data.get("codigo_matematica"))
    if codigo_block is None and str(data.get("code") or "").strip():
        raw_tipo = str(data.get("_code_tipo_raw") or data.get("code_tipo") or "").strip().lower()
        raw_titulo = str(data.get("_code_titulo_raw") or data.get("code_titulo") or "").strip()
        if raw_tipo in _VALID_CODE_TIPOS:
            codigo_block = {
                "tipo": raw_tipo,
                "titulo": html.escape(raw_titulo or "Ejemplo", quote=True)[:80],
                "contenido": html.escape(str(data.get("code")).strip(), quote=True)[:1000],
            }
    code = _esc(data.get("code") or "", 1000) or ""
    code_tipo = ""
    code_titulo = ""
    if codigo_block is not None:
        code = codigo_block["contenido"]
        code_tipo = codigo_block["tipo"]
        code_titulo = codigo_block["titulo"]
    elif code:
        code_tipo = "codigo"
        code_titulo = "Ejemplo"
        codigo_block = {"tipo": "codigo", "titulo": "Ejemplo", "contenido": code}
    relevant = False if data.get("relevant") is False else True
    filtered = data.get("filtered") is True
    # Max 2 support blocks besides titulo+texto: drop lowest-priority extra.
    # Priority keep: conceptos > listado(bullets) > codigo > imagen_hashtag/image.
    def _has_cards() -> bool:
        return len(cards) > 0
    def _has_bul() -> bool:
        return len(bullets) > 0
    def _has_code() -> bool:
        return bool(code.strip()) or any(isinstance(c, dict) and str(c.get("code") or "").strip() for c in cards)
    def _has_img() -> bool:
        return bool(imagen_hashtag.strip() or image.strip())
    support = sum([_has_cards(), _has_bul(), _has_code(), _has_img()])
    if support > 2:
        # Drop imagen first.
        if _has_img():
            imagen_hashtag = ""
            image = ""
            support -= 1
        if support > 2 and _has_code():
            code = ""
            code_tipo = ""
            code_titulo = ""
            codigo_block = None
            # Strip per-card code as well (keep card text/icon).
            stripped = []
            for c in cards:
                if isinstance(c, dict):
                    nc = {k: v for k, v in c.items() if k not in ("code", "code_tipo", "code_titulo")}
                    stripped.append(nc)
                else:
                    stripped.append(c)
            cards = stripped
            support -= 1
        if support > 2 and _has_bul():
            bullets = []
            support -= 1
    # Fallback derivation when layout missing/invalid or ambiguous title_text with blocks.
    if layout is None:
        n_con = len(cards)
        has_concept_code = any(isinstance(c, dict) and str(c.get("code") or "").strip() for c in cards)
        blocks = {
            "n_conceptos": n_con,
            "has_concept_code": has_concept_code,
            "n_listado": len(bullets),
            "has_code": bool(code.strip()),
            "has_image": bool(imagen_hashtag.strip() or image.strip()),
            "has_texto": bool(text.strip() or explanation.strip()),
        }
        # Ambiguous title_text with heavy blocks also derives; pure title_text stays.
        if raw_layout not in SLIDE_DESIGNS or raw_layout in (None, "", "title_text"):
            derived = derive_layout(blocks, is_opening=is_opening)
            # Only upgrade from title_text when there is something to show.
            if raw_layout in SLIDE_DESIGNS and raw_layout != "title_text":
                layout = raw_layout
            else:
                layout = derived
        else:
            layout = "title_text"
    # Hero gate: only opening cover or first slide after main topic change.
    if layout == "hero_cover" and not is_opening:
        _t = str(data.get("text") or data.get("texto") or "").strip()
        _img = str(data.get("image") or "").strip() or imagen_hashtag.strip()
        _bul = data.get("bullets") if isinstance(data.get("bullets"), list) else []
        if not _bul and isinstance(data.get("listado"), list):
            _bul = data.get("listado")
        _has = bool(_t or _img or len([b for b in _bul if str(b).strip()]) > 0)
        layout = "split_media" if _has else "title_text"
    # Content-dependent degradation: never render an empty flexible layout.
    if layout in ("cards_flex", "compare_2"):
        if len(cards) < 2:
            layout = "bullets_flex" if len(bullets) >= 2 else "title_text"
    elif layout == "steps_flex":
        if len(steps) < 2:
            layout = "title_text"
    elif layout == "stats_flex":
        if len(stats) < 2:
            layout = "title_text"
    elif layout in ("chips_flex", "checklist_flex"):
        items = chips if layout == "chips_flex" else bullets
        if len(items) < 2:
            layout = "title_text"
    elif layout == "split_code":
        if not code.strip():
            layout = "title_text"
    elif layout in ("split_media", "text_image"):
        has_text = bool(text.strip() or explanation.strip())
        has_bullets = len(bullets) > 0
        has_image = bool(image.strip() or imagen_hashtag.strip())
        if not (has_text or has_bullets or has_image):
            layout = "title_text"
    elif layout == "definition_guided":
        if not concept.strip() or not explanation.strip():
            layout = "title_text"
    elif layout == "concept_editorial":
        if not concept.strip() or not explanation.strip():
            layout = "title_text"
    elif layout == "pillars_3":
        if len(cards) < 3:
            layout = "bullets_flex" if len(bullets) >= 2 else "title_text"
    elif layout == "timeline_4":
        if len(steps) < 2:
            layout = "title_text"
    elif layout == "takeaway":
        if not takeaway.strip():
            layout = "title_text"
    elif layout == "stat_hero":
        if len(stats) < 1:
            layout = "title_text"
    # Spanish aliases (compat): mirror English internal with Spanish keys.
    conceptos_es = []
    for c in cards:
        if isinstance(c, dict):
            cm = None
            if str(c.get("code") or "").strip():
                cm = {
                    "tipo": str(c.get("code_tipo") or "codigo"),
                    "titulo": str(c.get("code_titulo") or "Ejemplo"),
                    "contenido": str(c.get("code") or ""),
                }
            conceptos_es.append({
                "subtitulo": str(c.get("title") or ""),
                "icono": str(c.get("icon") or "") or None,
                "texto": str(c.get("text") or ""),
                "codigo_matematica": cm,
            })
    out = {
        "layout": layout,
        "title": title,
        "text": text,
        "bullets": bullets,
        "keywords": keywords,
        "kicker": kicker,
        "subtitle": subtitle,
        "cards": cards,
        "stats": stats,
        "chips": chips,
        "steps": steps,
        "code": code,
        "code_tipo": code_tipo,
        "code_titulo": code_titulo,
        "codigo_matematica": codigo_block,
        "image": image,
        "imagen_hashtag": imagen_hashtag,
        "concept": concept,
        "explanation": explanation,
        "example": example,
        "takeaway": takeaway,
        "content_type": content_type,
        "layout_reason": layout_reason,
        "relevant": relevant,
        "filtered": filtered,
        # Spanish aliases for transport compat.
        "titulo": title,
        "texto": text,
        "listado": list(bullets),
        "conceptos": conceptos_es,
    }
    if not relevant or filtered:
        out.update({
            "title": "", "text": "", "titulo": "", "texto": "",
            "filtered": True, "relevant": False,
        })
    return out


# --- HTML rendering (dispatcher per layout) ---

def _palette_style(palette: dict | None) -> str:
    """Map palette roles to CSS vars. Falls back to resolve_palette(None)."""
    if palette is None:
        try:
            from backend.presentation_api.utils.palettes import resolve_palette

            palette = resolve_palette(None)
        except Exception:
            palette = {}
    p = palette or {}
    base = p.get("background", "#FAF7F0")
    base2 = p.get("background_alt", "#0F2E24")
    accent = p.get("primary", "#0E7C5B")
    accent2 = p.get("secondary", "#D6A84A")
    text = p.get("text", "#1A1A1A")
    text2 = p.get("text_alt", "#FFFFFF")
    muted = p.get("muted", "#6B7280")
    return (
        f"--base:{base};--base-2:{base2};--accent:{accent};"
        f"--accent-2:{accent2};--text:{text};--text-2:{text2};--muted:{muted}"
    )


def _is_safe_image(image: str) -> bool:
    """Only allow plain https URLs without spaces/quotes/angle brackets."""
    if not isinstance(image, str) or not image:
        return False
    if not image.startswith("https://"):
        return False
    if len(image) >= 500:
        return False
    for bad in (" ", '"', "'", "<", ">", "`", "&lt;", "&gt;", "&quot;", "&#x27;", "&#x60;"):
        if bad in image:
            return False
    return True


def _img_or_placeholder(image: str, alt: str, dark: bool = False) -> str:
    cls = "img chip-dark" if dark else "img"
    if _is_safe_image(image):
        return f'<img class="{cls}" src="{image}" alt="{alt}" loading="lazy" />'
    return f'<div class="{cls} placeholder" aria-hidden="true"><span class="dot"></span></div>'


def _icon_svg(name: object) -> str:
    key = str(name or "").strip().lower()
    if key not in _ICON_SVGS:
        return ""
    return f'<span class="icon-badge icon-svg" aria-hidden="true">{_ICON_SVGS[key]}</span>'


def _card_title_text(card: object) -> tuple[str, str]:
    if isinstance(card, dict):
        t = str(card.get("title", "") or "")
        x = str(card.get("text", "") or "")
        return t, x
    return str(card or ""), ""


def _card_code(card: object) -> str:
    if not isinstance(card, dict):
        return ""
    content = str(card.get("code") or "").strip()
    if not content:
        return ""
    titulo = str(card.get("code_titulo") or "Ejemplo")
    return (
        f'<pre class="code code-sm"><code>{content}</code></pre>'
        if not titulo
        else f'<div class="code-wrap"><p class="kicker accent">{titulo}</p><pre class="code code-sm"><code>{content}</code></pre></div>'
    )


def _header_html(s: dict) -> str:
    kicker = f'<p class="kicker">{s.get("kicker", "")}</p>' if s.get("kicker") else ""
    text = f'<p class="body-lg">{s.get("text", "")}</p>' if s.get("text") else ""
    explanation = ""
    if s.get("explanation") and s.get("explanation") != s.get("text"):
        explanation = f'<p class="body-lg">{s.get("explanation", "")}</p>'
    return (
        f'<div class="head">{kicker}<h2 class="h-slide">{s.get("title", "")}</h2>'
        f'<div class="rule"></div></div>{text}{explanation}'
    )


def _conceptos_html(cards: list) -> str:
    items = []
    for c in (cards or [])[:4]:
        if isinstance(c, dict):
            t = str(c.get("title", "") or "")
            x = str(c.get("text", "") or "")
            if not (t or x):
                continue
            icon = _icon_svg(c.get("icon"))
            code = _card_code(c)
            items.append(
                f'<div class="card concepto">{icon}'
                f'<p class="kicker accent">{t}</p><p class="body-lg">{x}</p>{code}</div>'
                if t or x else ""
            )
        elif str(c or "").strip():
            items.append(
                f'<div class="card concepto"><p class="body-lg">{c}</p></div>'
            )
    if not items:
        return ""
    n = max(2, min(4, len(items)))
    return f'<div class="conceptos grid-{n}">{"".join(items)}</div>'


def _code_footer_html(s: dict) -> str:
    content = str(s.get("code") or "").strip()
    if not content:
        return ""
    titulo = str(s.get("code_titulo") or "Ejemplo")
    tipo = str(s.get("code_tipo") or "codigo")
    label = f'<p class="kicker accent">{titulo} · {tipo}</p>' if titulo else ""
    return f'<div class="code-footer">{label}<pre class="code"><code>{content}</code></pre></div>'


def _media_placeholder_html(s: dict) -> str:
    # Placeholder-only for split_media (keeps text-only contract + existing tests).
    # _is_safe_image stays for future real-image use and hero covers.
    tags = str(s.get("imagen_hashtag") or "").strip()
    if tags:
        return (
            f'<div class="media"><div class="placeholder" data-tags="{tags}" '
            f'aria-hidden="true"><span class="dot"></span></div></div>'
        )
    return '<div class="media"><div class="placeholder" aria-hidden="true"><span class="dot"></span></div></div>'


def _composed_extras(s: dict, exclude: set | None = None) -> str:
    """Attach secondary sections not already rendered as primary layout."""
    exclude = exclude or set()
    parts: list[str] = []
    if "conceptos" not in exclude and isinstance(s.get("cards"), list) and len(s.get("cards")) > 0:
        # Only attach when cards exist; primary cards layouts exclude this.
        parts.append(_conceptos_html(s.get("cards", [])))
    if "listado" not in exclude and isinstance(s.get("bullets"), list) and len(s.get("bullets")) > 0:
        parts.append(_bullets_html([b for b in s.get("bullets", []) if isinstance(b, str)]))
    if "codigo" not in exclude and str(s.get("code") or "").strip():
        parts.append(_code_footer_html(s))
    if "media" not in exclude and (str(s.get("imagen_hashtag") or "").strip() or str(s.get("image") or "").strip()):
        parts.append(_media_placeholder_html(s))
    return "".join(p for p in parts if p)


def _stat_value_label(stat: object) -> tuple[str, str]:
    if isinstance(stat, dict):
        return str(stat.get("value", "") or ""), str(stat.get("label", "") or "")
    return str(stat or ""), ""


def _step_text(step: object) -> str:
    if isinstance(step, dict):
        t = str(step.get("title", "") or "")
        x = str(step.get("text", "") or "")
        return (t + (" — " + x if x else "")) if t else x
    return str(step or "")


def _bullets_html(bullets: list) -> str:
    items = "".join(f"<li>{b}</li>" for b in bullets[:4] if isinstance(b, str))
    return f"<ul>{items}</ul>" if items else ""


def _hero_cover(s: dict) -> str:
    kicker = f'<p class="kicker">{s["kicker"]}</p>' if s.get("kicker") else ""
    subtitle = f'<p class="subtitle">{s["subtitle"]}</p>' if s.get("subtitle") else ""
    if not subtitle and s.get("text"):
        subtitle = f'<p class="subtitle">{s.get("text", "")}</p>'
    chips = "".join(f'<span class="chip chip-dark">{c}</span>' for c in s.get("chips", [])[:4])
    chips_html = f'<div class="chips">{chips}</div>' if chips else ""
    stats = s.get("stats", [])[:3]
    stats_html = ""
    if len(stats) >= 2:
        items = "".join(
            f'<div><p class="stat-value">{v}</p><p class="muted">{lb}</p></div>'
            for v, lb in (_stat_value_label(x) for x in stats)
        )
        stats_html = f'<div class="stats-row">{items}</div>'
    media = _img_or_placeholder(s.get("image", ""), s.get("title", ""), dark=True)
    return (
        f'<div class="hero">{media}<div class="scrim"></div>'
        f'<div class="hero-body">{kicker}<h1 class="h-display">{s["title"]}</h1>'
        f'{subtitle}{chips_html}{stats_html}</div></div>'
    )


def _cards_flex(s: dict) -> str:
    header = _header_html(s)
    conceptos = _conceptos_html(s.get("cards", []))
    extras = _code_footer_html(s) + (
        _media_placeholder_html(s)
        if str(s.get("imagen_hashtag") or "").strip() or str(s.get("image") or "").strip()
        else ""
    )
    return f"{header}{conceptos}{extras}"


def _split_code(s: dict) -> str:
    bullets = _bullets_html(s.get("bullets", []))
    text = f'<p class="body-lg">{s["text"]}</p>' if s.get("text") else ""
    explanation = ""
    if s.get("explanation") and s.get("explanation") != s.get("text"):
        explanation = f'<p class="body-lg">{s.get("explanation", "")}</p>'
    code = _code_footer_html(s)
    return (
        f'<div class="split"><div><h2 class="h-slide">{s["title"]}</h2>'
        f'{text}{explanation}{bullets}</div>'
        f'<div>{code}</div></div>'
    )


def _split_media(s: dict) -> str:
    kicker = f'<p class="kicker">{s["kicker"]}</p>' if s.get("kicker") else ""
    explanation = ""
    if s.get("explanation") and s.get("explanation") != s.get("text"):
        explanation = f'<p class="body-lg">{s.get("explanation", "")}</p>'
    text = f'<p class="body-lg">{s["text"]}</p>' if s.get("text") else ""
    bullets = _bullets_html(s.get("bullets", [])[:3])
    conceptos = _conceptos_html(s.get("cards", [])) if s.get("cards") else ""
    code = _code_footer_html(s)
    media = _media_placeholder_html(s)
    return (
        f'<div class="split"><div>{kicker}<h2 class="h-slide">{s["title"]}</h2>'
        f'{text}{explanation}{bullets}{conceptos}{code}</div>'
        f'{media}</div>'
    )


def _separator(s: dict) -> str:
    media = _img_or_placeholder(s.get("image", ""), s.get("title", ""), dark=True)
    text = f'<p class="subtitle">{s["text"]}</p>' if s.get("text") else ""
    return (
        f'<div class="hero">{media}<div class="scrim-side"></div>'
        f'<div class="hero-body"><h1 class="h-display">{s["title"]}</h1>{text}</div></div>'
    )


def _compare_2(s: dict) -> str:
    cards = list(s.get("cards", [])[:3])
    items = []
    for c in cards:
        t, x = _card_title_text(c)
        if not (t or x):
            continue
        icon = _icon_svg(c.get("icon") if isinstance(c, dict) else None)
        code = _card_code(c)
        items.append(
            f'<div class="card card-compare">{icon}<p class="kicker accent">{t}</p><p class="body-lg">{x}</p>{code}</div>'
        )
    header = _header_html(s)
    code_footer = _code_footer_html(s)
    return f'{header}<div class="grid-2">{"".join(items)}</div>{code_footer}'


def _checklist_flex(s: dict) -> str:
    header = _header_html(s)
    items = "".join(
        f'<li class="check"><span class="icon-badge">✓</span><span>{b}</span></li>'
        for b in s.get("bullets", [])[:4] if isinstance(b, str)
    )
    checks = f'<ul class="grid-2 checks">{items}</ul>' if items else ""
    extras = ""
    if s.get("cards"):
        extras += _conceptos_html(s.get("cards", []))
    extras += _code_footer_html(s)
    if str(s.get("imagen_hashtag") or "").strip() or str(s.get("image") or "").strip():
        extras += _media_placeholder_html(s)
    return f"{header}{checks}{extras}"


def _stats_flex(s: dict) -> str:
    n = max(2, min(4, len(s.get("stats", []))))
    items = "".join(
        f'<div class="card"><p class="stat-value">{v}</p><p class="muted">{lb}</p></div>'
        for v, lb in (_stat_value_label(x) for x in s.get("stats", [])[:4])
    )
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<div class="grid-{n}">{items}</div>'
    )


def _chips_flex(s: dict) -> str:
    chips = "".join(f'<span class="chip">{c}</span>' for c in s.get("chips", [])[:4])
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<div class="chips">{chips}</div>'
    )


def _steps_flex(s: dict) -> str:
    n = max(2, min(4, len(s.get("steps", []))))
    items = "".join(
        f'<div class="card"><p class="step-number">{i:02d}</p><p class="body-lg">{_step_text(st)}</p></div>'
        for i, st in enumerate(s.get("steps", [])[:4], start=1)
    )
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<div class="grid-{n}">{items}</div>'
        f'<div class="bar"><span></span></div>'
    )


def _bullets_flex(s: dict) -> str:
    header = _header_html(s)
    bullets = _bullets_html(s.get("bullets", []))
    extras = _conceptos_html(s.get("cards", [])) if s.get("cards") else ""
    extras += _code_footer_html(s)
    if str(s.get("imagen_hashtag") or "").strip() or str(s.get("image") or "").strip():
        extras += _media_placeholder_html(s)
    return f"{header}{bullets}{extras}"


def _quote(s: dict) -> str:
    text = s.get("text") or s.get("title")
    cite = f'<p class="muted">— {s["title"]}</p>' if s.get("text") else ""
    return f'<blockquote class="quote"><p class="h-slide">“{text}”</p>{cite}</blockquote>'


def _title_text(s: dict) -> str:
    header = _header_html(s)
    extras = _composed_extras(s, exclude={"listado"})
    bullets = _bullets_html(s.get("bullets", []))
    return f"{header}{bullets}{extras}"


def _definition_guided(s: dict) -> str:
    concept = f'<p class="concept">{s.get("concept", "")}</p>' if s.get("concept") else ""
    explanation = f'<p class="explanation">{s.get("explanation", "")}</p>' if s.get("explanation") else ""
    example = (
        f'<div class="example"><p class="kicker accent">Example</p><p class="body-lg">{s.get("example", "")}</p></div>'
        if s.get("example") else ""
    )
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f"{concept}{explanation}{example}"
    )


def _concept_editorial(s: dict) -> str:
    concept = f'<p class="concept-hero">{s.get("concept", "")}</p>' if s.get("concept") else ""
    explanation = f'<p class="explanation">{s.get("explanation", "")}</p>' if s.get("explanation") else ""
    takeaway = (
        f'<p class="takeaway-line">{s.get("takeaway", "")}</p>' if s.get("takeaway") else ""
    )
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<div class="editorial">{concept}{explanation}{takeaway}</div>'
    )


def _pillars_3(s: dict) -> str:
    parts = []
    for i, c in enumerate(s.get("cards", [])[:3], start=1):
        t, x = _card_title_text(c)
        if not (t or x):
            continue
        icon = _icon_svg(c.get("icon") if isinstance(c, dict) else None)
        code = _card_code(c)
        parts.append(
            f'<div class="card pillar"><p class="step-number">0{i}</p>{icon}'
            f'<p class="kicker accent">{t}</p><p class="body-lg">{x}</p>{code}</div>'
        )
    header = _header_html(s)
    extras = _code_footer_html(s)
    return f'{header}<div class="pillars grid-3">{"".join(parts)}</div>{extras}'


def _timeline_4(s: dict) -> str:
    items = "".join(
        f'<li class="timeline-item"><span class="dot"></span><span>{_step_text(st)}</span></li>'
        for st in s.get("steps", [])[:4]
    )
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<ol class="timeline">{items}</ol>'
    )


def _takeaway(s: dict) -> str:
    takeaway = s.get("takeaway", "") or s.get("text", "")
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f'<blockquote class="takeaway"><p class="h-slide">“{takeaway}”</p></blockquote>'
    )


def _stat_hero(s: dict) -> str:
    value, label = _stat_value_label((s.get("stats", [])[:1] or [""])[0])
    stat = (
        f'<div class="stat-hero"><p class="stat-hero-value">{value}</p>'
        f'<p class="stat-hero-label">{label}</p></div>'
    )
    text = f'<p class="body-lg">{s["text"]}</p>' if s.get("text") else ""
    return (
        f'<div class="head"><h2 class="h-slide">{s["title"]}</h2>'
        f'<div class="rule"></div></div>'
        f"{stat}{text}"
    )


_LAYOUT_RENDERERS = {
    "hero_cover": _hero_cover,
    "cards_flex": _cards_flex,
    "split_code": _split_code,
    "split_media": _split_media,
    "separator": _separator,
    "compare_2": _compare_2,
    "checklist_flex": _checklist_flex,
    "stats_flex": _stats_flex,
    "chips_flex": _chips_flex,
    "steps_flex": _steps_flex,
    "bullets_flex": _bullets_flex,
    "quote": _quote,
    "title_text": _title_text,
    "definition_guided": _definition_guided,
    "concept_editorial": _concept_editorial,
    "pillars_3": _pillars_3,
    "timeline_4": _timeline_4,
    "takeaway": _takeaway,
    "stat_hero": _stat_hero,
}


def render_slide_html(slide: dict, palette: dict | None = None, is_opening: bool = False) -> str:
    """Render a sanitized snippet (section only, no html/head)."""
    s = validate_slide(slide, is_opening=is_opening)
    layout = s["layout"]
    canonical = ALIAS_MAP.get(layout, layout)
    renderer = _LAYOUT_RENDERERS.get(canonical, _title_text)
    body = renderer(s)
    style = _palette_style(palette)
    return (
        f'<section class="slide slide-{canonical}" style="{style}">'
        f'<div class="grid-texture"></div>{body}</section>'
    )
