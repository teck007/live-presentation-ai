"""Cliente LLM, para llamar a la API de Meta."""

import json
import os
import time
import dotenv
from openai import OpenAI

dotenv.load_dotenv()


def _read_llm_timeout_s() -> float:
    """Explicit client timeout (s); env LLM_TIMEOUT_S, default 15, clamped 1-60."""
    try:
        v = float(os.getenv("LLM_TIMEOUT_S", "15"))
    except ValueError:
        v = 15.0
    return min(60.0, max(1.0, v))


def _read_max_completion_tokens() -> int:
    """Max output tokens; env MAX_COMPLETION_TOKENS, default 1600 (tests assert >=800)."""
    try:
        v = int(os.getenv("MAX_COMPLETION_TOKENS", "1600"))
    except ValueError:
        v = 1600
    return min(8000, max(1, v))


client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.getenv("MODEL_API_KEY"),
    timeout=_read_llm_timeout_s(),
)
from backend.presentation_api.utils.slide_designs import (
    SLIDE_DESIGNS,
    VALID_LAYOUTS,
    list_designs_for_prompt,
    validate_slide,
)

# Max output tokens for a single live slide JSON response.
# Sized for tight texto (2-3 sentences) + up to 2 support blocks.
MAX_COMPLETION_TOKENS = _read_max_completion_tokens()


_DESIGNS_PROMPT_CACHE: str | None = None


def _designs_for_prompt_cached() -> str:
    """Cached design catalog: SLIDE_DESIGNS is static, build once per process."""
    global _DESIGNS_PROMPT_CACHE
    if _DESIGNS_PROMPT_CACHE is None:
        _DESIGNS_PROMPT_CACHE = list_designs_for_prompt()
    return _DESIGNS_PROMPT_CACHE

VALID_AUDIENCES = ("ninos", "estudiantes", "general", "profesionales", "expertos")

AUDIENCE_GUIDANCE = {
    "ninos": (
        "AUDIENCIA ninos: vocabulario muy simple, frases cortas, un ejemplo "
        "cotidiano y concreto, tono amable y curioso, sin tecnicismos."
    ),
    "estudiantes": (
        "AUDIENCIA estudiantes: usa lenguaje claro y didactico, define cada termino "
        "antes de usarlo, explica paso a paso sin asumir dominio avanzado, sigue el "
        "ritmo explicacion->ejemplo->sintesis."
    ),
    "general": (
        "AUDIENCIA general: tono profesional y accesible para publico mixto, "
        "evita jerga sin explicar, una idea central por slide, ejemplo breve solo "
        "si aclara, coherencia con el Tema principal."
    ),
    "profesionales": (
        "AUDIENCIA profesionales: tono ejecutivo, enfasis en implicancias practicas, "
        "decision o proximo paso, preciso y sin rodeos, sin simplificar en exceso."
    ),
    "expertos": (
        "AUDIENCIA expertos: densidad tecnica alta, terminologia precisa, matices y "
        "trade-offs, sin definiciones basicas salvo ambiguedad real."
    ),
}


def normalize_audience(value: object) -> str:
    """Normalize audience id; unknown or empty falls back to general."""
    v = str(value or "").strip().lower()
    return v if v in VALID_AUDIENCES else "general"


VALID_LANGUAGES = ("es", "en")

LANGUAGE_NAMES = {
    "es": "Spanish (espanol)",
    "en": "English",
}


def normalize_language(value: object) -> str:
    """Normalize UI locale id; unknown or empty falls back to Spanish."""
    v = str(value or "").strip().lower()
    return v if v in VALID_LANGUAGES else "es"

SLIDE_SYSTEM_PROMPT = (
    "Generas contenido para una presentacion en vivo. "
    "Responde SOLO con JSON valido, sin markdown ni texto extra. "
    "Esquema (contrato espanol compuesto; null lo no pedido): "
    "{\"relevant\": true|false, \"layout\": \"<id de layout o null: el backend deriva si es null>\", "
    "\"content_type\": \"<definicion|idea|proceso|comparacion|dato|mensaje|cierre>\", "
    "\"layout_reason\": \"<1 frase tecnica: por que este layout>\", "
    "\"titulo\": \"titulo en espanol, 8-10 palabras, estilo afirmacion (1 idea dominante)\", "
    "\"texto\": \"texto en espanol, 2-3 frases cortas (35-45 palabras max), "
    "prioriza la idea dominante sin muro de texto\", "
    "\"imagen_hashtag\": \"tags en INGLES separados por comas para imagen futura o null\", "
    "\"imagen_prompt\": \"frase visual en INGLES (1 frase, max 300 chars) solo si layout visual o null\", "
    "\"conceptos\": [{\"subtitulo\": \"titulo corto\", \"icono\": \"<idea|libro|codigo|grafico|lupa|lista|check|alerta|estrella|chat>\", "
    "\"texto\": \"1 linea acotada\", \"codigo_matematica\": null|{\"tipo\": \"codigo|matematica\", \"titulo\": \"Ejemplo|Ejercicio\", \"contenido\": \"...\"}}] "
    "maximo 4 o null, "
    "\"listado\": [\"maximo 4 strings cortos, ~12 palabras cada uno\"] o null, "
    "\"codigo_matematica\": null|{\"tipo\": \"codigo|matematica\", \"titulo\": \"Ejemplo|Ejercicio\", \"contenido\": \"...\"}, "
    "\"title\": \"alias ingles de titulo (compat)\", "
    "\"text\": \"alias ingles de texto (compat)\", "
    "\"bullets\": \"alias ingles de listado (compat)\", "
    "\"cards\": \"alias ingles de conceptos (compat)\", "
    "\"code\": \"alias ingles de codigo_matematica.contenido (compat)\", "
    "\"image\": \"alias ingles: solo URL https real o vacio (compat)\", "
    "\"concept\": \"opcional, 1 linea: termino o idea central\", "
    "\"explanation\": \"opcional, espejo de texto\", "
    "\"example\": \"opcional, caso real breve mencionado o ejemplo corto\", "
    "\"takeaway\": \"opcional, 1 linea accionable o mensaje a recordar\", "
    "\"stats\": [{\"value\": \"...\", \"label\": \"...\"}], "
    "\"chips\": [\"opcional, maximo 4 conceptos cortos\"], "
    "\"steps\": [\"opcional, maximo 4 pasos en orden\"], "
    "\"kicker\": \"opcional, contexto breve\", "
    "\"subtitle\": \"opcional, subtitulo breve\", "
    "\"keywords\": [\"opcional, maximo 5\"]}. "
    "Modo libre: si el Tema principal es \"(sin definir)\" o viene vacio, "
    "relevant=true siempre y genera el slide desde la transcripcion. "
    "Con tema definido, filtro semantico estricto: relevant=true SOLO si la "
    "transcripcion aporta al Tema principal (acepta sinonimos, parafrasis o "
    "aspectos especificos del tema); relevant=false si es saludo, muletilla, "
    "otro tema o mencion tangencial sin aporte real al Tema. "
    "La evaluacion es semantica, no literal. "
    "Si relevant=false, devuelve layout title_text con titulo y texto vacios. "
    "Si relevant=true, texto NO repite literal la transcripcion: explica la tematica "
    "contextualizada al Tema principal, 2-3 frases cortas (35-45 palabras max) segun audiencia. "
    "Rellena SOLO lo que el tema pida; el resto va en null (nunca strings vacios inventados). "
    "Maximo 2 bloques de apoyo ademas de titulo+texto (conceptos, listado, codigo_matematica, imagen_hashtag); "
    "si hay mas, deja los 2 mas importantes y el resto en null. "
    "imagen_prompt solo se llena si el layout es visual (split_media o hero_cover); "
    "en cualquier otro layout va en null. imagen_hashtag queda como fallback. "
    "Regla anti-muro: prioriza la idea dominante en texto; los detalles van a conceptos o listado. "
    "Regla anti-invencion: no inventes numeros ni codigo; "
    "icono SOLO de la lista cerrada (idea, libro, codigo, grafico, lupa, lista, check, alerta, estrella, chat); "
    "si dudas, usa null y el backend lo omite. "
    "explica antes de ejemplificar, sin parrafos largos; "
    "AUDIENCIA estudiantes: usa lenguaje claro y didactico, define cada termino "
    "antes de usarlo, explica paso a paso sin asumir dominio avanzado, sigue el "
    "ritmo explicacion->ejemplo->sintesis. "
    "Contrato de redaccion: concept=1 linea, explanation=1-2 frases, "
    "example=caso real breve, takeaway=1 linea accionable. "
    "Clasificacion por turno: PROCEDIMENTAL si es proceso, tutorial, algoritmo o "
    "receta -> usa steps_flex con cada paso con objetivo, accion y ejemplo; si es "
    "el arranque del tema usa hero_cover como mapa de lo que viene. "
    "CONCEPTUAL si es idea o teoria -> usa title_text o cards_flex con 1 idea "
    "dominante, definicion mas ejemplo academico simple. "
    "Tabla dura contenido->layout (title_text SOLO como ultimo recurso): "
    "definicion de un termino->definition_guided (concept+explanation+example); "
    "idea central con enfasis editorial->concept_editorial; "
    "exactamente 3 pilares o fundamentos->pillars_3 con 3 cards; "
    "progresion temporal o hitos en orden->timeline_4 con 2-4 steps; "
    "cierre o mensaje accionable->takeaway con takeaway; "
    "un numero destacado explicito->stat_hero con 1 stat; "
    "idea simple sin datos extra->title_text; "
    "2-4 subpuntos presentes->cards_flex o bullets_flex; "
    "pasos o secuencia ordenada->steps_flex; codigo o sintaxis real->split_code (solo con codigo real); "
    "comparacion de 2 (vs, pros/contras, antes/despues)->compare_2; "
    "2-4 numeros explicitos mencionados->stats_flex; "
    "conceptos cortos o etiquetas->chips_flex; "
    "frase memorable para destacar->quote; "
    "pausa o cambio de seccion->separator; "
    "apertura o primer slide tras cambio de tema principal->hero_cover (solo si Es apertura: si); "
    "cualquier contenido visualizable mid-topic->split_media (placeholder, nunca hero). "
    "Never choose hero_cover just because there is an image. "
    "stats_flex y stat_hero solo con numeros explicitos de la transcripcion, "
    "split_code solo con codigo real mencionado, "
    "si faltan los datos usa title_text. "
    "Regla anti-repeticion: evita el layout anterior salvo que sea claramente el "
    "mejor ajuste; justifica tu eleccion en layout_reason. "
    "Ejemplo pasos: transcripcion \"primero prendemos el servidor, luego corremos migraciones, "
    "despues desplegamos\" -> layout steps_flex con steps de 3 items. "
    "Ejemplo comparacion: transcripcion \"Postgres versus SQLite para este MVP\" -> "
    "layout compare_2 con cards de 2 items. "
    "Ejemplo compuesto: transcripcion \"la fotosintesis convierte luz en energia con clorofila\" -> "
    "{\"titulo\": \"Fotosintesis\", \"texto\": \"...2-3 frases, 35-45 palabras...\", "
    "\"conceptos\": [{\"subtitulo\": \"Clorofila\", \"icono\": \"libro\", \"texto\": \"...\", \"codigo_matematica\": null}], "
    "\"listado\": null, \"codigo_matematica\": null, \"imagen_hashtag\": \"photosynthesis, leaf\"}. "
    "Ejemplo codigo: transcripcion \"para sumar usamos def suma(a, b): return a + b\" -> "
    "{\"titulo\": \"Funcion suma\", \"texto\": \"...\", \"codigo_matematica\": "
    "{\"tipo\": \"codigo\", \"titulo\": \"Ejemplo\", \"contenido\": \"def suma(a, b): return a + b\"}, "
    "\"conceptos\": null, \"listado\": null, \"imagen_hashtag\": null}. "
    "Solo espanol (salvo imagen_hashtag en ingles). "
    "Catalogo de layouts: " + list_designs_for_prompt() + ". "
    "Regla: elige flexible solo si hay 2-4 items reales (pillars_3 exige 3, "
    "timeline_4 exige 2-4, stat_hero exige 1), si no usa title_text. Trunca a 4."
)


def build_system_prompt(language: str = "es") -> str:
    """Return the slide system prompt for the requested output language.

    Spanish is the canonical prompt (SLIDE_SYSTEM_PROMPT). English reuses the
    same contract with the text fields mandated in English; image tags stay
    in English in both variants.
    """
    lang = normalize_language(language)
    if lang == "es":
        return SLIDE_SYSTEM_PROMPT
    prompt = SLIDE_SYSTEM_PROMPT
    replacements = (
        ("titulo en espanol", "titulo in English"),
        ("texto en espanol", "texto in English"),
        ("titulo\" en espanol", "titulo\" in English"),
        ("Solo espanol (salvo imagen_hashtag en ingles)",
         "English only (imagen_hashtag stays in English)"),
        ("Solo espanol", "English only"),
    )
    for old, new in replacements:
        prompt = prompt.replace(old, new)
    prefix = (
        "Output language: English. Every human-readable slide field "
        "(titulo/title, texto/text, listado/bullets, conceptos/cards, "
        "concept, explanation, example, takeaway, kicker, subtitle, chips, "
        "steps, stats labels) MUST be in English. "
        "imagen_hashtag and imagen_prompt stay in English. "
    )
    return prefix + prompt


def _fallback_slide(
    transcript: str,
    keywords: list[str] | None,
    topic: str = "",
    language: str = "es",
) -> dict:
    """Slide mínimo cuando el LLM falla o devuelve JSON inválido."""
    from backend.presentation_api.utils.topic_cleaner import is_relevant

    lang = normalize_language(language)
    text = (transcript or "").strip()
    words = text.split()
    short = " ".join(words[:30]) if len(words) > 30 else text
    # Respaldo barato: si el LLM falló, usa el filtro literal para no generar basura.
    relevant = is_relevant(text, topic or "", list(keywords or []), language=lang)
    if lang == "en":
        title = " ".join(words[:8]) if words else "Live"
        body = short or "Live content."
    else:
        title = " ".join(words[:8]) if words else "En vivo"
        body = short or "Contenido en vivo."
    return {
        "layout": "title_text",
        "title": title,
        "text": body,
        "bullets": [],
        "keywords": list(keywords or [])[:5],
        "kicker": "",
        "subtitle": "",
        "cards": [],
        "stats": [],
        "chips": [],
        "steps": [],
        "code": "",
        "code_tipo": "",
        "code_titulo": "",
        "codigo_matematica": None,
        "image": "",
        "imagen_hashtag": "",
        "imagen_prompt": "",
        "concept": "",
        "explanation": "",
        "example": "",
        "takeaway": "",
        "content_type": "",
        "layout_reason": "",
        "relevant": relevant,
        "filtered": not relevant,
        "titulo": title,
        "texto": body,
        "listado": [],
        "conceptos": [],
    }


def _format_previous_slides(previous_slides: list | None) -> str:
    """Compact previous slides context (max 5) to avoid repeating titles/ideas."""
    if not isinstance(previous_slides, list) or not previous_slides:
        return "(ninguna)"
    parts: list[str] = []
    for item in previous_slides[-5:]:
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("titulo") or item.get("title") or "").strip()[:80]
        resumen = str(item.get("resumen") or item.get("text") or "").strip()[:160]
        if not titulo and not resumen:
            continue
        parts.append(f"- {titulo}: {resumen}".strip())
    return "\n".join(parts[:5]) if parts else "(ninguna)"


def generate_slide(
    transcript: str,
    topic: str,
    keywords: list[str] | None = None,
    audience: str = "general",
    previous_layout: str | None = None,
    is_opening: bool = False,
    previous_slides: list | None = None,
    language: str = "es",
) -> dict:
    """Generate slide content as plain JSON (no HTML).

    The LLM only chooses content + layout id. Design lives in the frontend.
    Always returns a valid dict with layout/title/text/bullets/keywords.
    """
    kws = list(keywords or [])[:5]
    audience = normalize_audience(audience)
    language = normalize_language(language)
    previous_layout = str(previous_layout or "").strip() or ""
    start = time.perf_counter()
    try:
        prev_ctx = _format_previous_slides(previous_slides)
        user_content = (
            f"Tema principal: {topic.strip() or '(sin definir)'}\n"
            f"Keywords: {', '.join(kws) if kws else '(ninguna)'}\n"
            f"Audiencia: {audience} — {AUDIENCE_GUIDANCE[audience]}\n"
            f"Idioma de salida: {LANGUAGE_NAMES[language]}\n"
            f"Layout anterior: {previous_layout or '(ninguno)'}\n"
            f"Es apertura: {'si' if is_opening else 'no'} — hero_cover solo permitido si si\n"
            f"Slides previas (NO repitas titulo ni idea dominante ya cubierta):\n{prev_ctx}\n"
            f"Transcripción: {transcript.strip()}\n"
            f"Diseños disponibles: {_designs_for_prompt_cached()}"
        )
        response = client.chat.completions.create(
            model="muse-spark-1.3",
            messages=[
                {"role": "system", "content": build_system_prompt(language)},
                {"role": "user", "content": user_content},
            ],
            # TODO(measured): temperature 0.7 stays until latency/quality data says otherwise.
            temperature=0.7,
            top_p=0.9,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            reasoning_effort="minimal",
            response_format={"type": "json_object"},
        )
        elapsed = time.perf_counter() - start
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] muse-spark fallback reason={str(exc)[:120]!r}", flush=True)
            return _fallback_slide(transcript, kws, topic, language)
        if not isinstance(data, dict):
            print("[llm] muse-spark fallback reason='invalid-json'", flush=True)
            return _fallback_slide(transcript, kws, topic, language)
        # El modelo decide en esta misma respuesta si corresponde al tema principal.
        relevant = data.get("relevant", True)
        relevant = False if relevant is False else True
        if not relevant:
            print(
                "[llm] muse-spark layout=title_text "
                f"audience={audience} reason=filtered "
                f"elapsed={time.perf_counter() - start:.2f}s",
                flush=True,
            )
            return {
                "layout": "title_text",
                "title": "",
                "text": "",
                "bullets": [],
                "keywords": kws,
                "kicker": "",
                "subtitle": "",
                "cards": [],
                "stats": [],
                "chips": [],
                "steps": [],
                "code": "",
                "code_tipo": "",
                "code_titulo": "",
                "codigo_matematica": None,
                "image": "",
                "imagen_hashtag": "",
                "imagen_prompt": "",
                "concept": "",
                "explanation": "",
                "example": "",
                "takeaway": "",
                "content_type": "",
                "layout_reason": "",
                "relevant": False,
                "filtered": True,
                "titulo": "",
                "texto": "",
                "listado": [],
                "conceptos": [],
            }
        raw_layout = data.get("layout") if isinstance(data, dict) else None
        layout = raw_layout if raw_layout in VALID_LAYOUTS else None
        # Spanish composite wins; English kept for compat.
        # Caps mirror validate_slide budgets (large editorial type).
        title = (
            str(data.get("titulo") or data.get("title") or "").strip()[:100]
            or ("Live" if language == "en" else "En vivo")
        )
        text = (
            str(data.get("texto") or data.get("text") or "").strip()[:400]
            or (transcript or "").strip()[:400]
        )
        raw_listado = data.get("listado") if isinstance(data.get("listado"), list) else None
        raw_bullets = data.get("bullets") if isinstance(data.get("bullets"), list) else []
        bullets_src = raw_listado if raw_listado is not None else raw_bullets
        bullets = [str(b).strip()[:120] for b in bullets_src if str(b).strip()][:4]
        out_kws = data.get("keywords") if isinstance(data.get("keywords"), list) else kws
        out_kws = [str(k).strip() for k in out_kws if str(k).strip()][:5]
        validated = validate_slide(
            {
                "layout": layout,
                "title": title,
                "titulo": data.get("titulo"),
                "text": text,
                "texto": data.get("texto"),
                "bullets": bullets,
                "listado": data.get("listado"),
                "conceptos": data.get("conceptos"),
                "codigo_matematica": data.get("codigo_matematica"),
                "imagen_hashtag": data.get("imagen_hashtag"),
                "imagen_prompt": data.get("imagen_prompt"),
                "keywords": out_kws,
                "kicker": data.get("kicker"),
                "subtitle": data.get("subtitle"),
                "cards": data.get("cards"),
                "stats": data.get("stats"),
                "chips": data.get("chips"),
                "steps": data.get("steps"),
                "code": data.get("code"),
                "image": data.get("image"),
                "concept": data.get("concept"),
                "explanation": data.get("explanation"),
                "example": data.get("example"),
                "takeaway": data.get("takeaway"),
                "content_type": data.get("content_type"),
                "layout_reason": data.get("layout_reason"),
                "relevant": True,
                "filtered": False,
            },
            is_opening=is_opening,
            language=language,
        )
        print(
            f"[llm] muse-spark layout={validated.get('layout')} audience={audience} "
            f"language={language} "
            f"reason={str(validated.get('layout_reason') or '')[:60]!r} "
            f"cards={len(validated.get('cards') or [])} "
            f"stats={len(validated.get('stats') or [])} "
            f"steps={len(validated.get('steps') or [])} "
            f"chips={len(validated.get('chips') or [])} "
            f"bullets={len(validated.get('bullets') or [])} "
            f"elapsed={time.perf_counter() - start:.2f}s",
            flush=True,
        )
        return validated
    except Exception as exc:  # noqa: BLE001 - MVP: fallback, no rompe el vivo
        print(f"[llm] muse-spark fallback reason={str(exc)[:120]!r}", flush=True)
        return _fallback_slide(transcript, kws, topic, language)


def analyze_text(text: str) -> str:
    """Compat: devuelve el texto breve del slide (antes devolvía str libre)."""
    slide = generate_slide(text, topic="", keywords=[])
    return slide.get("text", "")


if __name__ == "__main__":
    print(generate_slide("Python es un lenguaje de programación", "Python", ["programación"]))
