"""Tests for the slide designs catalog (single source of truth)."""
from backend.presentation_api.utils.slide_designs import (
    SLIDE_DESIGNS,
    VALID_LAYOUTS,
    list_designs,
    list_designs_for_prompt,
    render_slide_html,
    validate_slide,
)


def test_catalog_stable():
    expected = {
        "hero_cover", "cards_flex", "split_code", "split_media",
        "separator", "compare_2", "checklist_flex", "stats_flex",
        "chips_flex", "bullets_flex", "steps_flex", "quote",
        "title_text", "title_bullets", "text_image",
    }
    assert expected.issubset(set(SLIDE_DESIGNS.keys()))
    assert set(VALID_LAYOUTS) == set(SLIDE_DESIGNS.keys())
    for lid, spec in SLIDE_DESIGNS.items():
        assert spec["layout_mode"] in ("fixed", "flexible"), lid
        assert isinstance(spec["fields"], list) and spec["fields"], lid


def test_max_4_truncation():
    data = validate_slide({
        "layout": "bullets_flex",
        "title": "T",
        "text": "x",
        "bullets": ["a", "b", "c", "d", "e", "f"],
        "chips": ["1", "2", "3", "4", "5"],
        "steps": ["1", "2", "3", "4", "5", "6"],
    })
    assert len(data["bullets"]) == 4
    assert len(data["chips"]) == 4
    assert len(data["steps"]) == 4


def test_escape_script():
    data = validate_slide({
        "layout": "title_text",
        "title": "<script>alert(1)</script>",
        "text": "hi",
    })
    assert "<script>" not in data["title"]
    assert "&lt;script&gt;" in data["title"]
    html = render_slide_html({"layout": "title_text", "title": "<b>x</b>", "text": "y"})
    assert "<b>" not in html
    assert "<section" in html
    assert "<html" not in html and "<head" not in html


def test_invalid_layout_fallback():
    data = validate_slide({"layout": "nope", "title": "T", "text": "x"})
    assert data["layout"] == "title_text"


def test_prompt_compact():
    prompt = list_designs_for_prompt()
    assert "cards_flex" in prompt
    assert isinstance(list_designs(), list)
    assert any(d["id"] == "stats_flex" for d in list_designs())


def test_prompt_lists_all_layouts_no_old_enumeration():
    from backend.presentation_api.utils.llm_client import SLIDE_SYSTEM_PROMPT

    for lid in (
        "hero_cover", "cards_flex", "split_code", "split_media", "separator",
        "compare_2", "checklist_flex", "stats_flex", "chips_flex",
        "bullets_flex", "steps_flex", "quote", "title_text",
    ):
        assert lid in SLIDE_SYSTEM_PROMPT, lid
    assert '"layout": "title_text|title_bullets|text_image|quote"' not in SLIDE_SYSTEM_PROMPT


def test_degrade_empty_cards_to_title_text():
    data = validate_slide({"layout": "cards_flex", "title": "T", "text": "x", "cards": []})
    assert data["layout"] == "title_text"


def test_degrade_empty_compare_without_bullets_fallback():
    data = validate_slide({"layout": "compare_2", "title": "T", "text": "x"})
    assert data["layout"] == "title_text"


def test_degrade_compare_to_bullets_when_bullets_present():
    data = validate_slide({
        "layout": "compare_2", "title": "T", "text": "x",
        "bullets": ["a", "b", "c"],
    })
    assert data["layout"] == "bullets_flex"


def test_degrade_empty_stats_and_chips_and_code():
    assert validate_slide({"layout": "stats_flex", "title": "T"})["layout"] == "title_text"
    assert validate_slide({"layout": "chips_flex", "title": "T"})["layout"] == "title_text"
    assert validate_slide({"layout": "split_code", "title": "T", "code": ""})["layout"] == "title_text"
    assert validate_slide({"layout": "split_media", "title": "T", "image": ""})["layout"] == "title_text"


def test_degrade_empty_steps():
    assert validate_slide({"layout": "steps_flex", "title": "T"})["layout"] == "title_text"


def test_valid_steps_stays():
    data = validate_slide({
        "layout": "steps_flex", "title": "T", "text": "x",
        "steps": ["uno", "dos", "tres"],
    })
    assert data["layout"] == "steps_flex"
    assert len(data["steps"]) == 3


def test_prompt_targets_students():
    from backend.presentation_api.utils.llm_client import SLIDE_SYSTEM_PROMPT

    assert "estudiantes" in SLIDE_SYSTEM_PROMPT


def test_prompt_classifies_procedural_vs_conceptual():
    from backend.presentation_api.utils.llm_client import SLIDE_SYSTEM_PROMPT

    assert "PROCEDIMENTAL" in SLIDE_SYSTEM_PROMPT
    assert "CONCEPTUAL" in SLIDE_SYSTEM_PROMPT


def test_max_completion_tokens_allows_student_explanations():
    from backend.presentation_api.utils.llm_client import MAX_COMPLETION_TOKENS

    assert MAX_COMPLETION_TOKENS >= 800


def test_prompt_includes_all_layouts_with_fields():
    prompt = list_designs_for_prompt()
    for lid, spec in SLIDE_DESIGNS.items():
        assert lid in prompt, lid
        for field in spec["fields"]:
            assert field in prompt, f"{lid}:{field}"
        assert f"{spec['min_items']}-{spec['max_items']}" in prompt, lid


def test_render_structural_per_layout():
    hero = render_slide_html({
        "layout": "hero_cover", "title": "Hola", "kicker": "Intro",
        "subtitle": "Sub", "chips": ["a", "b"],
        "stats": [{"value": "10", "label": "x"}, {"value": "20", "label": "y"}],
        "image": "https://example.com/a.jpg",
    }, None, True)
    assert "kicker" in hero and "Hola" in hero
    assert "h-display" in hero
    code = render_slide_html({
        "layout": "split_code", "title": "T", "text": "exp",
        "code": "print('hi')", "bullets": ["a", "b"],
    })
    assert "<pre" in code and "print" in code
    media = render_slide_html({
        "layout": "split_media", "title": "T", "text": "lugar bonito",
        "bullets": ["a", "b"], "image": "https://example.com/b.jpg",
    })
    assert "<img" in media and "h-slide" in media
    assert 'class="media"' in media and 'fetchpriority="high"' in media
    sep = render_slide_html({"layout": "separator", "title": "Pausa", "text": "descanso"})
    assert "Pausa" in sep and "scrim-side" in sep
    comp = render_slide_html({
        "layout": "compare_2", "title": "VS",
        "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}],
    })
    assert "card-compare" in comp
    check = render_slide_html({
        "layout": "checklist_flex", "title": "T", "bullets": ["uno", "dos"],
    })
    assert "icon-badge" in check
    stats = render_slide_html({
        "layout": "stats_flex", "title": "T",
        "stats": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}],
    })
    assert "stat-value" in stats
    chips = render_slide_html({
        "layout": "chips_flex", "title": "T", "chips": ["a", "b"],
    })
    assert "chip" in chips
    steps = render_slide_html({
        "layout": "steps_flex", "title": "T", "steps": ["uno", "dos", "tres"],
    })
    assert "step-number" in steps
    bullets = render_slide_html({
        "layout": "bullets_flex", "title": "T", "text": "x", "bullets": ["a", "b"],
    })
    assert "<ul>" in bullets
    quote = render_slide_html({"layout": "quote", "title": "A", "text": "frase"})
    assert "quote" in quote
    cards = render_slide_html({
        "layout": "cards_flex", "title": "T",
        "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}],
    })
    assert "grid-2" in cards
    title = render_slide_html({"layout": "title_text", "title": "T", "text": "x"})
    assert "h-slide" in title
    for snippet in (hero, code, media, sep, comp, check, stats, chips, steps, bullets, quote, cards, title):
        assert snippet.startswith("<section") and "<html" not in snippet and "<head" not in snippet


def test_render_explicit_palette_hex():
    palette = {
        "id": "test", "background": "#111111", "background_alt": "#222222",
        "primary": "#333333", "secondary": "#444444", "text": "#555555",
        "text_alt": "#666666", "muted": "#777777",
    }
    snippet = render_slide_html({"layout": "title_text", "title": "T", "text": "x"}, palette)
    for hx in ("#111111", "#222222", "#333333", "#444444", "#555555", "#666666", "#777777"):
        assert hx in snippet
    assert "--base:" in snippet and "--accent:" in snippet


def test_render_same_palette_stable():
    palette = {
        "id": "test", "background": "#111111", "background_alt": "#222222",
        "primary": "#333333", "secondary": "#444444", "text": "#555555",
        "text_alt": "#666666", "muted": "#777777",
    }
    slide = {"layout": "title_text", "title": "T", "text": "x"}
    assert render_slide_html(slide, palette) == render_slide_html(slide, palette)


def test_render_xss_escaped():
    snippet = render_slide_html({
        "layout": "title_text", "title": "<script>alert(1)</script>", "text": "<img src=x onerror=y>",
    })
    assert "<script>" not in snippet
    assert "<img src=x" not in snippet
    assert "&lt;script&gt;" in snippet


def test_render_non_https_image_yields_no_img():
    snippet = render_slide_html({
        "layout": "split_media", "title": "T", "text": "x",
        "image": "http://example.com/a.jpg",
    })
    # Degraded (no https image) or placeholder without <img>.
    assert "<img" not in snippet
    evil = render_slide_html({
        "layout": "split_media", "title": "T", "text": "x",
        "image": "https://example.com/a b.jpg",
    })
    assert "<img" not in evil


def test_aliases_render_same_as_canonical():
    palette = {
        "id": "test", "background": "#111111", "background_alt": "#222222",
        "primary": "#333333", "secondary": "#444444", "text": "#555555",
        "text_alt": "#666666", "muted": "#777777",
    }
    a = render_slide_html({"layout": "title_bullets", "title": "T", "bullets": ["a", "b"]}, palette)
    b = render_slide_html({"layout": "bullets_flex", "title": "T", "bullets": ["a", "b"]}, palette)
    assert a == b
    c = render_slide_html({
        "layout": "text_image", "title": "T", "text": "x", "image": "https://example.com/a.jpg",
    }, palette)
    d = render_slide_html({
        "layout": "split_media", "title": "T", "text": "x", "image": "https://example.com/a.jpg",
    }, palette)
    assert c == d


def test_catalog_includes_new_layouts():
    for lid in (
        "definition_guided", "concept_editorial", "pillars_3",
        "timeline_4", "takeaway", "stat_hero",
    ):
        assert lid in SLIDE_DESIGNS, lid
        assert lid in VALID_LAYOUTS, lid
    assert SLIDE_DESIGNS["pillars_3"]["min_items"] == 3
    assert SLIDE_DESIGNS["pillars_3"]["max_items"] == 3
    assert SLIDE_DESIGNS["timeline_4"]["min_items"] == 2
    assert SLIDE_DESIGNS["stat_hero"]["min_items"] == 1


def test_degrade_new_layouts_missing_data():
    assert validate_slide(
        {"layout": "definition_guided", "title": "T", "concept": "", "explanation": ""}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "definition_guided", "title": "T", "concept": "C", "explanation": ""}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "concept_editorial", "title": "T", "concept": "", "explanation": "E"}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "pillars_3", "title": "T",
         "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}]}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "timeline_4", "title": "T", "steps": ["solo uno"]}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "takeaway", "title": "T", "takeaway": ""}
    )["layout"] == "title_text"
    assert validate_slide(
        {"layout": "stat_hero", "title": "T", "stats": []}
    )["layout"] == "title_text"


def test_valid_new_layouts_stay():
    ok_def = validate_slide({
        "layout": "definition_guided", "title": "T",
        "concept": "Fotosintesis", "explanation": "Las plantas convierten luz en energia.",
        "example": "Un girasol siguiendo el sol.",
    })
    assert ok_def["layout"] == "definition_guided"
    assert ok_def["concept"] == "Fotosintesis"
    ok_pillars = validate_slide({
        "layout": "pillars_3", "title": "T",
        "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}, {"title": "C", "text": "z"}],
    })
    assert ok_pillars["layout"] == "pillars_3"
    ok_timeline = validate_slide({
        "layout": "timeline_4", "title": "T", "steps": ["uno", "dos"],
    })
    assert ok_timeline["layout"] == "timeline_4"
    ok_takeaway = validate_slide({
        "layout": "takeaway", "title": "T", "takeaway": "Riega tus plantas hoy.",
    })
    assert ok_takeaway["layout"] == "takeaway"
    ok_stat = validate_slide({
        "layout": "stat_hero", "title": "T",
        "stats": [{"value": "42%", "label": "humedad"}],
    })
    assert ok_stat["layout"] == "stat_hero"


def test_new_fields_sanitized_and_capped():
    data = validate_slide({
        "layout": "definition_guided", "title": "T",
        "concept": "<b>" + "x" * 300,
        "explanation": "e" * 900,
        "example": "a" * 600,
        "takeaway": "<script>alert(1)</script>",
        "content_type": "<img src=x>",
        "layout_reason": "<b>razon</b>",
    })
    assert "<script>" not in data["takeaway"] and "<b>" not in data["concept"]
    assert len(data["concept"]) <= 200
    assert len(data["explanation"]) <= 900
    assert len(data["example"]) <= 400
    assert len(data["takeaway"]) <= 200
    assert len(data["content_type"]) <= 40
    assert len(data["layout_reason"]) <= 200
    assert data["layout"] == "definition_guided"


def test_render_structural_new_layouts():
    dg = render_slide_html({
        "layout": "definition_guided", "title": "T",
        "concept": "Fotosintesis", "explanation": "Las plantas convierten luz.",
        "example": "Girasol.",
    })
    assert "concept" in dg and "Fotosintesis" in dg
    ce = render_slide_html({
        "layout": "concept_editorial", "title": "T",
        "concept": "Idea clave", "explanation": "Explicacion breve.",
        "takeaway": "Recuerda esto.",
    })
    assert "editorial" in ce and "Idea clave" in ce
    pillars = render_slide_html({
        "layout": "pillars_3", "title": "T",
        "cards": [{"title": "A", "text": "x"}, {"title": "B", "text": "y"}, {"title": "C", "text": "z"}],
    })
    assert "pillars" in pillars
    timeline = render_slide_html({
        "layout": "timeline_4", "title": "T", "steps": ["uno", "dos", "tres"],
    })
    assert "timeline" in timeline
    takeaway = render_slide_html({
        "layout": "takeaway", "title": "T", "takeaway": "Hazlo hoy.",
    })
    assert "takeaway" in takeaway and "Hazlo hoy" in takeaway
    stat = render_slide_html({
        "layout": "stat_hero", "title": "T",
        "stats": [{"value": "99%", "label": "exito"}],
    })
    assert "stat-hero" in stat and "99%" in stat
    for snippet in (dg, ce, pillars, timeline, takeaway, stat):
        assert snippet.startswith("<section") and "<html" not in snippet and "<head" not in snippet


def test_render_xss_new_fields():
    snippet = render_slide_html({
        "layout": "definition_guided", "title": "T",
        "concept": "<script>alert(1)</script>",
        "explanation": "<img src=x onerror=y>",
        "example": "<b>hola</b>",
    })
    assert "<script>" not in snippet
    assert "<img src=x" not in snippet
    assert "&lt;script&gt;" in snippet


def test_prompt_hard_table_and_new_fields():
    from backend.presentation_api.utils.llm_client import SLIDE_SYSTEM_PROMPT

    for token in (
        "definition_guided", "concept_editorial", "pillars_3",
        "timeline_4", "takeaway", "stat_hero",
    ):
        assert token in SLIDE_SYSTEM_PROMPT, token
    assert "title_text SOLO como ultimo recurso" in SLIDE_SYSTEM_PROMPT
    assert "layout anterior" in SLIDE_SYSTEM_PROMPT or "anterior" in SLIDE_SYSTEM_PROMPT
    for field in ("content_type", "explanation", "concept", "example", "takeaway", "layout_reason"):
        assert field in SLIDE_SYSTEM_PROMPT, field


def test_audience_normalization_fallback():
    from backend.presentation_api.utils.llm_client import normalize_audience

    assert normalize_audience(" Expertos ") == "expertos"
    assert normalize_audience("NINOS") == "ninos"
    assert normalize_audience("") == "general"
    assert normalize_audience(None) == "general"
    assert normalize_audience("aliens") == "general"
    for valid in ("ninos", "estudiantes", "general", "profesionales", "expertos"):
        assert normalize_audience(valid) == valid


def test_language_normalization_fallback():
    from backend.presentation_api.utils.llm_client import normalize_language

    assert normalize_language(" EN ") == "en"
    assert normalize_language("es") == "es"
    assert normalize_language("") == "es"
    assert normalize_language(None) == "es"
    assert normalize_language("fr") == "es"
    assert normalize_language("pt") == "es"


def test_prompt_spanish_and_english_output_language():
    from backend.presentation_api.utils.llm_client import (
        SLIDE_SYSTEM_PROMPT,
        build_system_prompt,
    )

    es_prompt = build_system_prompt("es")
    en_prompt = build_system_prompt("en")
    assert es_prompt == SLIDE_SYSTEM_PROMPT
    assert "Solo espanol" in es_prompt
    assert "Output language: English" in en_prompt
    assert "English only" in en_prompt
    # Image tags stay English in both variants.
    assert "imagen_hashtag" in en_prompt
    assert "imagen_prompt" in en_prompt
    # Unknown locale falls back to Spanish.
    assert build_system_prompt("fr") == SLIDE_SYSTEM_PROMPT


def test_hero_kept_only_when_opening():
    base = {"layout": "hero_cover", "title": "T", "text": "apertura",
            "bullets": ["a"], "image": "https://example.com/a.jpg"}
    assert validate_slide(dict(base), is_opening=True)["layout"] == "hero_cover"
    assert validate_slide(dict(base), is_opening=False)["layout"] == "split_media"
    assert validate_slide(dict(base))["layout"] == "split_media"
    assert validate_slide({"layout": "hero_cover", "title": "T"})["layout"] == "title_text"


def test_split_placeholder_no_img():
    snippet = render_slide_html({
        "layout": "split_media", "title": "T", "text": "lugar bonito",
        "bullets": ["a", "b", "c", "d"],
        "imagen_hashtag": "beach, sunset",
    })
    assert "<img" not in snippet
    assert 'class="media"' in snippet and 'class="placeholder"' in snippet
    assert "h-slide" in snippet


def test_split_real_image_renders_img():
    snippet = render_slide_html({
        "layout": "split_media", "title": "T", "text": "lugar bonito",
        "bullets": ["a", "b", "c", "d"],
        "image": "https://example.com/b.jpg",
    })
    assert "<img" in snippet
    assert 'src="https://example.com/b.jpg"' in snippet
    assert 'loading="lazy"' in snippet and 'fetchpriority="high"' in snippet
    assert 'class="media"' in snippet


def test_prompt_opening_only_and_negative_rule():
    from backend.presentation_api.utils.llm_client import SLIDE_SYSTEM_PROMPT

    assert "Never choose hero_cover just because there is an image" in SLIDE_SYSTEM_PROMPT
    assert "Es apertura" in SLIDE_SYSTEM_PROMPT or "hero_cover solo permitido" in SLIDE_SYSTEM_PROMPT
    assert "hero_cover" in SLIDE_SYSTEM_PROMPT
    assert "split_media" in SLIDE_SYSTEM_PROMPT


# --- Spanish composite contract: derivation fixtures (6 captures) ---

def test_derive_title_text_only():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 0, "has_concept_code": False, "n_listado": 0,
              "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "title_text"


def test_derive_icon_grid_3_conceptos():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 3, "has_concept_code": False, "n_listado": 0,
              "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "cards_flex"
    v = validate_slide({
        "titulo": "T", "texto": "desarrollo",
        "conceptos": [
            {"subtitulo": "A", "icono": "idea", "texto": "x", "codigo_matematica": None},
            {"subtitulo": "B", "icono": "libro", "texto": "y", "codigo_matematica": None},
            {"subtitulo": "C", "icono": "lupa", "texto": "z", "codigo_matematica": None},
        ],
        "listado": None, "codigo_matematica": None, "imagen_hashtag": None,
    })
    assert v["layout"] == "cards_flex"
    assert len(v["cards"]) == 3


def test_derive_listado_plus_code_goes_split():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 0, "has_concept_code": False, "n_listado": 3,
              "has_code": True, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "split_code"


def test_derive_conceptos_with_code_cards():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 3, "has_concept_code": True, "n_listado": 0,
              "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "cards_flex"


def test_derive_compare_2_conceptos_with_code():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 2, "has_concept_code": True, "n_listado": 0,
              "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "compare_2"


def test_derive_checklist_listado():
    from backend.presentation_api.utils.slide_designs import derive_layout

    blocks = {"n_conceptos": 0, "has_concept_code": False, "n_listado": 4,
              "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(blocks) == "checklist_flex"


def test_derive_hero_opening_and_split_media_image():
    from backend.presentation_api.utils.slide_designs import derive_layout

    empty = {"n_conceptos": 0, "has_concept_code": False, "n_listado": 0,
             "has_code": False, "has_image": False, "has_texto": True}
    assert derive_layout(empty, is_opening=True) == "hero_cover"
    assert derive_layout(empty, is_opening=False) == "title_text"
    img = {"n_conceptos": 0, "has_concept_code": False, "n_listado": 0,
           "has_code": False, "has_image": True, "has_texto": True}
    assert derive_layout(img, is_opening=False) == "split_media"
    assert derive_layout(img, is_opening=True) == "hero_cover"


def test_nulls_render_no_empty_blocks():
    v = validate_slide({
        "titulo": "T", "texto": "desarrollo de la idea",
        "conceptos": None, "listado": None,
        "codigo_matematica": None, "imagen_hashtag": None,
    })
    assert v["layout"] == "title_text"
    snippet = render_slide_html(v)
    assert "concepto" not in snippet or "Fotosintesis" not in snippet
    assert "<pre" not in snippet
    assert 'data-tags' not in snippet


def test_xss_spanish_fields_escaped():
    v = validate_slide({
        "titulo": "<script>alert(1)</script>",
        "texto": "texto",
        "conceptos": [
            {"subtitulo": "<img src=x onerror=y>", "icono": "<script>evil</script>",
             "texto": "t", "codigo_matematica": None},
        ],
        "listado": ["<b>hola</b>"],
        "codigo_matematica": {"tipo": "codigo", "titulo": "<i>E</i>", "contenido": "<script>code()</script>"},
        "imagen_hashtag": '"><script>alert(2)</script>',
    })
    assert "<script>" not in v["title"]
    assert v["cards"][0].get("icon") is None
    raw_snippet = render_slide_html({
        "titulo": "<script>alert(1)</script>",
        "texto": "texto",
        "conceptos": [
            {"subtitulo": "<img src=x onerror=y>", "icono": "<script>evil</script>",
             "texto": "t", "codigo_matematica": None},
        ],
        "listado": ["<b>hola</b>"],
        "codigo_matematica": {"tipo": "codigo", "titulo": "<i>E</i>", "contenido": "<script>code()</script>"},
        "imagen_hashtag": '"><script>alert(2)</script>',
    })
    assert "<script>" not in raw_snippet
    assert "<img src=x" not in raw_snippet
    assert "&lt;script&gt;" in raw_snippet


def test_math_escaped_not_executed():
    v = validate_slide({
        "titulo": "T", "texto": "x",
        "codigo_matematica": {"tipo": "matematica", "titulo": "Ejemplo", "contenido": "E = mc^2 <b>bold</b>"},
    })
    assert v["code_tipo"] == "matematica"
    snippet = render_slide_html({"layout": "split_code", "title": "T", "text": "x",
                                 "code": v["code"], "code_tipo": "matematica", "code_titulo": "Ejemplo"})
    assert "E = mc^2" in snippet
    assert "<b>" not in snippet


def test_placeholder_imagen_hashtag_no_img():
    v = validate_slide({
        "titulo": "T", "texto": "lugar bonito",
        "imagen_hashtag": "beach, sunset",
    })
    assert v["imagen_hashtag"] == "beach, sunset"
    snippet = render_slide_html(v)
    assert "<img" not in snippet
    assert 'data-tags="beach, sunset"' in snippet


def test_compat_old_english_still_passes():
    v = validate_slide({"layout": "bullets_flex", "title": "T", "text": "x",
                        "bullets": ["a", "b"]})
    assert v["layout"] == "bullets_flex"
    assert v["titulo"] == "T" and v["texto"] == "x"
    assert v["listado"] == ["a", "b"]


def test_max_two_support_blocks_enforced():
    v = validate_slide({
        "titulo": "T", "texto": "x",
        "conceptos": [
            {"subtitulo": "A", "icono": "idea", "texto": "x", "codigo_matematica": None},
            {"subtitulo": "B", "icono": "libro", "texto": "y", "codigo_matematica": None},
        ],
        "listado": ["uno", "dos"],
        "codigo_matematica": {"tipo": "codigo", "titulo": "Ejemplo", "contenido": "print(1)"},
        "imagen_hashtag": "tags, here",
    })
    support = sum([
        len(v["cards"]) > 0, len(v["bullets"]) > 0,
        bool(v["code"].strip()), bool(v["imagen_hashtag"].strip()),
    ])
    assert support <= 2


def test_icon_catalog_closed_enum():
    from backend.presentation_api.utils.slide_designs import ICON_CATALOG, _esc_icon

    assert len(ICON_CATALOG) >= 10
    assert _esc_icon("idea") == "idea"
    assert _esc_icon("<svg>") is None
    assert _esc_icon("inexistente") is None


def test_prompt_spanish_composite_and_tokens():
    from backend.presentation_api.utils.llm_client import MAX_COMPLETION_TOKENS, SLIDE_SYSTEM_PROMPT

    assert MAX_COMPLETION_TOKENS >= 1500
    for token in ("titulo", "texto", "imagen_hashtag", "conceptos", "listado", "codigo_matematica", "icono"):
        assert token in SLIDE_SYSTEM_PROMPT, token


# --- Imágenes generativas progresivas (vivo efímero) ---

def test_supports_image_catalog():
    from backend.presentation_api.utils.slide_designs import SLIDE_DESIGNS

    assert SLIDE_DESIGNS["split_media"]["supports_image"] is True
    assert SLIDE_DESIGNS["hero_cover"]["supports_image"] is True
    for lid in ("title_text", "bullets_flex", "split_code", "quote", "cards_flex"):
        assert SLIDE_DESIGNS[lid]["supports_image"] is False, lid


def test_should_generate_image_por_layout():
    from backend.presentation_api.utils.slide_designs import should_generate_image

    assert should_generate_image("split_media", "a red bicycle") is True
    assert should_generate_image("hero_cover", "a red bicycle") is True
    assert should_generate_image("text_image", "a red bicycle") is True  # alias visual
    assert should_generate_image("split_media", "") is False
    assert should_generate_image("split_media", "   ") is False
    assert should_generate_image("split_media", None) is False
    assert should_generate_image("title_text", "a red bicycle") is False
    assert should_generate_image("split_code", "a red bicycle") is False
    assert should_generate_image("quote", "a red bicycle") is False


def test_imagen_prompt_sanitizado_y_nulificado():
    v = validate_slide({
        "layout": "split_media", "title": "T", "text": "x",
        "imagen_prompt": '<script>alert(1)</script> a red bicycle',
    })
    assert "<script>" not in v["imagen_prompt"]
    assert "&lt;script&gt;" in v["imagen_prompt"]
    long_prompt = "a " + "x" * 500
    assert len(validate_slide({
        "layout": "split_media", "title": "T", "text": "x",
        "imagen_prompt": long_prompt,
    })["imagen_prompt"]) <= 300
    # Layout no visual nulifica el prompt.
    assert validate_slide({
        "layout": "title_text", "title": "T", "text": "x",
        "imagen_prompt": "a red bicycle",
    })["imagen_prompt"] == ""


def test_build_fast_prompt_con_sufijo():
    from backend.presentation_api.utils.slide_designs import build_fast_prompt

    prompt = build_fast_prompt("Fotosintesis", "a green leaf", "photosynthesis")
    assert "Fotosintesis" in prompt
    assert "a green leaf" in prompt
    assert prompt.endswith("flat vector illustration, no text, simple background")
    assert len(build_fast_prompt("t" * 500, "p" * 500, "g" * 500)) <= 500 + 60


def test_prompt_indica_imagen_visual():
    prompt = list_designs_for_prompt()
    assert "imagen_prompt" in prompt


def test_fallback_slide_localized_defaults():
    from backend.presentation_api.utils.llm_client import _fallback_slide

    es = _fallback_slide("hola mundo", [], "", language="es")
    assert es["title"] == "En vivo" or es["title"]
    assert es["text"] == "Contenido en vivo." or es["text"]
    empty_es = _fallback_slide("", [], "", language="es")
    assert empty_es["title"] == "En vivo"
    assert empty_es["text"] == "Contenido en vivo."
    empty_en = _fallback_slide("", [], "", language="en")
    assert empty_en["title"] == "Live"
    assert empty_en["text"] == "Live content."
    assert empty_en["titulo"] == "Live"
    assert empty_en["texto"] == "Live content."


def test_validate_slide_localized_defaults():
    en = validate_slide({}, language="en")
    assert en["title"] == "Live"
    es = validate_slide({}, language="es")
    assert es["title"] == "En vivo"
    unknown = validate_slide({})
    assert unknown["title"] == "En vivo"


def test_topic_cleaner_language_keywords():
    from backend.presentation_api.utils.topic_cleaner import (
        analyze_topic,
        extract_keywords,
        is_relevant,
        normalize_language,
    )

    assert normalize_language("en") == "en"
    assert normalize_language("xx") == "es"
    en = analyze_topic("hello, um this is about photosynthesis and light energy", language="en")
    assert "photosynthesis" in en["keywords"]
    assert "um" not in en["keywords"]
    es = analyze_topic("eh bueno la fotosíntesis y la energía de la luz", language="es")
    assert "fotosíntesis" in es["keywords"]
    assert "eh" not in es["keywords"]
    assert is_relevant("photosynthesis converts light", "photosynthesis", language="en") is True
    assert is_relevant("hola mundo", "photosynthesis", language="en") is False
