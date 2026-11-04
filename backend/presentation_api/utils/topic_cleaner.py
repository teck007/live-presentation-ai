"""
Limpieza heurística del texto libre del usuario para extraer el tema real.

El usuario suele escribir frases como "hacé una presentación para desarrollar
paso a paso un ensayo argumentativo". Este módulo quita los prefijos de
instrucción y deja el tema ("ensayo argumentativo"). Se usa para armar el
query de búsqueda web y el nombre de la presentación; el prompt del LLM
sigue recibiendo el texto crudo para conservar las intenciones del usuario.
"""

from __future__ import annotations

import re

# Prefijos de instrucción / cortesía que se eliminan del inicio del texto.
# Se aplican en cascada porque un prefijo puede dejar otro ("hacé una
# presentación para desarrollar..." -> "para desarrollar..." -> "paso a paso...").
_LEADING_META = re.compile(
    r"^\s*(?:"
    # Habilidad o cortesía: "podes/puedo/podrías + verbo en infinitivo"
    r"(?:me\s+)?(?:pod(?:és|es|rías|rías)|pued(?:es|o|a))\s+"
    r"(?:hacer|crear|armar|generar|desarrollar|preparar|elaborar|organizar|"
    r"diseñar|dar|explicar|contar|mostrar|enseñar|resumir|exponer|hablar|"
    r"buscar|ayudar)\s+"
    r"(?:una|un|la|el|los|las|me\s+)?\s*(?:presentaci(?:o|ó)n\s+)?"
    r"|"
    # Deseos, necesidad y peticiones
    r"(?:quiero|necesito|quisiera|busco|me\s+gustar(?:ía|iá)|me\s+encantar(?:ía|iá))"
    r"\s+(?:que\s+|saber\s+|conocer\s+|aprender\s+)?"
    r"|"
    # Pedidos de material: "dame ideas para un proyecto..." (antes de la rama
    # de imperativos porque "dame" también matchea como verbo).
    r"(?:dame|dáme)\s+(?:ideas|información|informacion|ejemplos)?\s+"
    r"|"
    # Verbos en imperativo (voseo y tuteo) + complemento típico
    r"(?:me\s+)?(?:hac(?:e|é|eme)|haz(?:me)?|arm(?:a|á|ame)|cre(?:a|á|ame)|"
    r"gener(?:a|á|ame)|desarroll(?:a|á|ame)|elabor(?:a|á|ame)|"
    r"prepar(?:a|á|ame)|organiz(?:a|á|ame)|diseñ(?:a|á|ame)|"
    r"d(?:a|á)me|explic(?:a|á|ame)|cont(?:a|á|ame)|mostr(?:a|á|ame)|"
    r"enseñ(?:a|á|ame)|resum(?:í|i)|expon(?:é|e)|habl(?:a|á|ame)|"
    r"ayud(?:a|á|ame)|busc(?:a|á|ame)|ven|ve|pon|ten|di)"
    r"\s+(?:una|un|la|el|los|las|me\s+)?\s*(?:presentaci(?:o|ó)n\s+)?"
    r"|"
    # Preguntas introductorias: "qué es", "cómo funciona", "cómo se hace"
    r"(?:qué|que)\s+(?:es|son|fue|fueron)\s+"
    r"|"
    r"(?:cómo|como)\s+(?:funciona|funcionan|se\s+hace|se\s+hacen|hacer)\s+"
    r"|"
    r"por\s+favor\s+"
    r")"
    r"(?:acerca\s+de|del|de\s+las|de\s+los|de\s+la|sobre|de|en)?\s*",
    re.IGNORECASE,
)

# "para + verbo en infinitivo" ("para desarrollar...") o "para + artículo" ("para un...").
_PARA_RESTOS = re.compile(
    r"^\s*para\s+(?:\w{2,}(?:ar|er|ir|se)\b|(?:un|una|el|la|los|las))\s*"
)

# Modificadores colgantes y artículos iniciales ("paso a paso un ensayo...").
_PASO_A_PASO = re.compile(r"^\s*paso\s+a\s+paso\s*")
_ARTICULO = re.compile(r"^\s*(?:un|una|el|la|los|las)\s+")

# Saludos iniciales ("hola quiero una presentación sobre..." -> quitar "hola").
# Solo al inicio del texto, case-insensitive.
_GREETINGS = re.compile(
    r"^\s*(?:hola|buenas|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|"
    r"buenos\s+tardes|hey|al[oó])\b[\s,!.\u00bf?]*",
    re.IGNORECASE,
)

# English leading greetings (mirrors _GREETINGS, applied when language="en").
_GREETINGS_EN = re.compile(
    r"^\s*(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)\b[\s,!.?]*",
    re.IGNORECASE,
)

# "quiero hablar sobre/de..." ("eh bueno quiero hablar sobre el cambio...").
_HABLAR_SOBRE = re.compile(
    r"^\s*(?:quiero|quisiera|necesito)\s+"
    r"(?:hablar|contar|explicar)\s+"
    r"(?:acerca\s+de|sobre|de|en)?\s*",
    re.IGNORECASE,
)
_FILLERS = [
    "bueno pues",
    "o sea",
    "a ver",
    "eh",
    "em",
    "mmm",
    "este",
    "esto",
    "bueno",
    "digamos",
    "viste",
    "mira",
    "mirá",
    "pues",
]

# English voice fillers (mirrors _FILLERS, applied when language="en").
_FILLERS_EN = [
    "well you know",
    "you know",
    "i mean",
    "let me see",
    "uh",
    "um",
    "hmm",
    "like",
    "well",
    "so",
    "actually",
    "basically",
    "right",
]

# Palabras individuales que forman las muletillas (para filtrado de keywords).
_FILLER_WORDS = frozenset(w for phrase in _FILLERS for w in phrase.split())

# English filler words (mirrors _FILLER_WORDS, applied when language="en").
_FILLER_WORDS_EN = frozenset(w for phrase in _FILLERS_EN for w in phrase.split())

# Regex de muletillas (frases largas primero) con límites de palabra.
_FILLER_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in sorted(_FILLERS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# English filler regex (mirrors _FILLER_RE, applied when language="en").
_FILLER_RE_EN = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in sorted(_FILLERS_EN, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Palabras repetidas consecutivas ("el el cambio" -> "el cambio").
_REPEATED_WORD_RE = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)

# Stopwords mínimas en español para extracción de keywords.
_STOPWORDS_ES = frozenset(
    {
        "y", "o", "u", "pero", "porque", "pues", "que", "de", "del", "la",
        "el", "los", "las", "un", "una", "unos", "unas", "en", "con",
        "por", "para", "se", "su", "sus", "mi", "mis", "tu", "tus",
        "es", "son", "fue", "fueron", "hay", "este", "esta", "estos",
        "estas", "ese", "esa", "eso", "aquí", "ahí", "muy", "más",
        "mas", "también", "tampoco", "además", "entonces", "luego",
        "después", "cuando", "donde", "como", "cómo", "qué", "cual",
        "cuáles", "yo", "tú", "él", "ella", "nosotros", "ustedes",
        "me", "te", "nos", "lo", "le", "les", "al", "a", "e", "haz",
        "presentación", "presentacion",
    }
)

# Minimal English stopwords for keyword extraction (mirrors _STOPWORDS_ES).
_STOPWORDS_EN = frozenset(
    {
        "and", "or", "but", "because", "so", "that", "of", "the", "a",
        "an", "in", "with", "for", "to", "its", "his", "her", "my",
        "your", "is", "are", "was", "were", "there", "this", "that",
        "these", "those", "here", "very", "also", "then", "when",
        "where", "how", "what", "which", "i", "you", "he", "she",
        "we", "they", "me", "us", "him", "them", "at", "on", "by",
        "from", "as", "be", "been", "have", "has", "had", "do",
        "does", "did", "will", "would", "can", "could", "should",
        "presentation",
    }
)

VALID_LANGUAGES = ("es", "en")


def normalize_language(value: object) -> str:
    """Normalize UI locale id; unknown or empty falls back to Spanish."""
    v = str(value or "").strip().lower()
    return v if v in VALID_LANGUAGES else "es"


_TOKEN_RE = re.compile(r"[a-záéíóúñü]+")

# English token regex (ASCII only; no accented vowels).
_TOKEN_RE_EN = re.compile(r"[a-z]+")


def _filler_re_for(language: str):
    return _FILLER_RE_EN if normalize_language(language) == "en" else _FILLER_RE


def _filler_words_for(language: str) -> frozenset:
    return _FILLER_WORDS_EN if normalize_language(language) == "en" else _FILLER_WORDS


def _stopwords_for(language: str) -> frozenset:
    return _STOPWORDS_EN if normalize_language(language) == "en" else _STOPWORDS_ES


def _token_re_for(language: str):
    return _TOKEN_RE_EN if normalize_language(language) == "en" else _TOKEN_RE


def _greetings_re_for(language: str):
    return _GREETINGS_EN if normalize_language(language) == "en" else _GREETINGS


def _remove_fillers(text: str, language: str = "es") -> str:
    """Remove voice fillers anywhere, collapse repeated words, normalize spaces."""
    if not text:
        return ""
    filler_re = _filler_re_for(language)
    text = filler_re.sub(" ", text)
    prev = None
    while prev != text:
        prev = text
        text = _REPEATED_WORD_RE.sub(r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _strip_greetings(text: str, language: str = "es") -> str:
    """Remove leading greetings, keeping them when they are the content.

    "hola mundo" stays as-is (greeting + single word is likely the topic).
    Only strips when the remainder has >= 2 words and len >= 3.
    """
    greetings_re = _greetings_re_for(language)
    prev = None
    while prev != text:
        prev = text
        m = greetings_re.match(text)
        if not m:
            break
        remainder = text[m.end():].strip()
        if len(remainder) < 3 or len(remainder.split()) < 2:
            break
        text = remainder
    return text


def clean_topic(raw: str, language: str = "es") -> str:
    """Extrae el tema real de un texto libre del usuario (best-effort).

    Devuelve el tema limpio; si la limpieza lo deja vacío o irreconocible,
    devuelve el texto original recortado.
    """
    lang = normalize_language(language)
    if not raw:
        return ""
    text = raw.strip()

    if lang == "en":
        return _clean_topic_en(text)

    # Saludos y muletillas ANTES de los prefijos: "hola quiero..." o
    # "eh bueno quiero hablar sobre..." exponen el prefijo al limpiarlos.
    # Se itera porque quitar fillers puede exponer saludos y viceversa.
    for _ in range(5):
        prev_outer = text
        text = _strip_greetings(text).strip()
        text = _remove_fillers(text).strip()
        # Cascada de prefijos: un prefijo puede dejar otro.
        prev = None
        while prev != text:
            prev = text
            text = _HABLAR_SOBRE.sub("", text).strip()
            text = _LEADING_META.sub("", text).strip()
        if text == prev_outer:
            break

    # Restos tipo "para desarrollar..." o "para un...", "paso a paso..." y artículos.
    text = _PARA_RESTOS.sub("", text).strip()
    text = _PASO_A_PASO.sub("", text).strip()
    text = _ARTICULO.sub("", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Muletillas en cualquier posición ("... sobre eh el cambio ...").
    # Se re-aplica el artículo inicial porque quitar fillers puede exponerlo
    # ("eh el cambio climático" -> "el cambio climático" -> "cambio climático").
    # Quitar fillers también puede exponer saludos/prefijos ("eh hola quiero...").
    text = _remove_fillers(text).strip()
    text = _ARTICULO.sub("", text).strip()
    text = _strip_greetings(text).strip()
    # Un saludo expuesto puede haber tapado un prefijo: una pasada final.
    prev = None
    while prev != text:
        prev = text
        text = _HABLAR_SOBRE.sub("", text).strip()
        text = _LEADING_META.sub("", text).strip()
    text = _ARTICULO.sub("", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()

    if len(text) < 3:
        return raw.strip()
    return text


# English instruction/polite prefixes stripped from the start of the text
# (mirrors _LEADING_META, applied when language="en").
_LEADING_META_EN = re.compile(
    r"^\s*(?:"
    r"(?:can\s+you|could\s+you|would\s+you|please)\s+"
    r"(?:make|create|build|generate|develop|prepare|explain|tell|show|teach|summarize|summarise|give|help)\s+"
    r"(?:a|an|the\s+)?\s*(?:presentation\s+)?"
    r"|"
    r"(?:i\s+want|i\s+need|i['’]d\s+like|i\s+would\s+like)\s+"
    r"(?:to\s+know\s+|to\s+learn\s+|a\s+)?"
    r"|"
    r"(?:give\s+me|show\s+me|tell\s+me)\s+(?:ideas|information|examples?)?\s*"
    r"|"
    r"(?:make|create|build|generate|develop|prepare|explain|tell|show|teach|summarize|summarise|give)\s+"
    r"(?:a|an|the\s+)?\s*(?:presentation\s+)?"
    r"|"
    r"(?:what\s+is|what\s+are|what\s+was|what\s+were|how\s+does|how\s+do|how\s+to)\s+"
    r"|"
    r"please\s+"
    r")"
    r"(?:about|on|of|for|regarding|concerning)?\s*",
    re.IGNORECASE,
)

# "to + infinitive" leftovers ("to develop...") or articles.
_PARA_RESTOS_EN = re.compile(
    r"^\s*to\s+(?:\w{2,}(?:e|ing|ed)?\b|(?:a|an|the))\s*"
)

_ARTICULO_EN = re.compile(r"^\s*(?:a|an|the)\s+")


def _clean_topic_en(text: str) -> str:
    """English topic cleanup (mirrors the Spanish cascade, best-effort)."""
    raw = text
    for _ in range(5):
        prev_outer = text
        text = _strip_greetings(text, "en").strip()
        text = _remove_fillers(text, "en").strip()
        prev = None
        while prev != text:
            prev = text
            text = _LEADING_META_EN.sub("", text).strip()
        if text == prev_outer:
            break
    text = _PARA_RESTOS_EN.sub("", text).strip()
    text = _ARTICULO_EN.sub("", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = _remove_fillers(text, "en").strip()
    text = _ARTICULO_EN.sub("", text).strip()
    text = _strip_greetings(text, "en").strip()
    prev = None
    while prev != text:
        prev = text
        text = _LEADING_META_EN.sub("", text).strip()
    text = _ARTICULO_EN.sub("", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()
    if len(text) < 3:
        return raw.strip()
    return text


def extract_keywords(text: str, top_n: int = 5, language: str = "es") -> list[str]:
    """Extract top keywords by frequency, skipping stopwords and fillers."""
    if not text:
        return []
    lang = normalize_language(language)
    tokens = _token_re_for(lang).findall(text.lower())
    stopwords = _stopwords_for(lang)
    filler_words = _filler_words_for(lang)
    freq: dict[str, int] = {}
    first_index: dict[str, int] = {}
    for i, token in enumerate(tokens):
        if len(token) < 3:
            continue
        if token in stopwords:
            continue
        if token in filler_words:
            continue
        if token not in freq:
            freq[token] = 0
            first_index[token] = i
        freq[token] += 1
    ranked = sorted(freq, key=lambda t: (-freq[t], first_index[t]))
    return ranked[:top_n]


def analyze_topic(raw: str, top_n: int = 5, language: str = "es") -> dict:
    """Clean raw text and extract topic keywords (best-effort)."""
    lang = normalize_language(language)
    cleaned = clean_topic(raw or "", language=lang)
    if not cleaned:
        return {"topic": "", "keywords": [], "cleaned": ""}
    keywords = extract_keywords(cleaned, top_n, language=lang)
    words = cleaned.split()
    topic = " ".join(words[:8]) if len(words) > 8 else cleaned
    return {"topic": topic, "keywords": keywords, "cleaned": cleaned}


def _content_tokens(text: str, language: str = "es") -> set[str]:
    """Tokenize to content words (lowercased, no stopwords/fillers, len>=3)."""
    lang = normalize_language(language)
    tokens = _token_re_for(lang).findall((text or "").lower())
    stopwords = _stopwords_for(lang)
    filler_words = _filler_words_for(lang)
    return {
        t
        for t in tokens
        if len(t) >= 3 and t not in stopwords and t not in filler_words
    }


def is_relevant(transcript: str, topic: str, keywords: list[str] | None = None, language: str = "es") -> bool:
    """Decide si un transcript pertenece al tema principal (laxo, best-effort).

    - Sin topic definido -> True (sin filtro).
    - Transcript vacío -> False.
    - True si hay overlap de >=1 token de contenido entre transcript y
      (topic + keywords), o si el topic limpio aparece como subcadena.
    """
    lang = normalize_language(language)
    thesis = (topic or "").strip()
    if not thesis:
        return True
    raw = (transcript or "").strip()
    if not raw:
        return False

    cleaned_transcript = clean_topic(raw, language=lang).lower()
    cleaned_topic = clean_topic(thesis, language=lang).lower()
    if cleaned_topic and cleaned_topic in cleaned_transcript:
        return True

    topic_tokens = _content_tokens(thesis, language=lang)
    for kw in keywords or []:
        topic_tokens |= _content_tokens(kw, language=lang)
    if not topic_tokens:
        return True

    transcript_tokens = _content_tokens(raw, language=lang)
    if not transcript_tokens:
        return False
    return len(topic_tokens & transcript_tokens) > 0
