"""Generación de imágenes para el vivo efímero (sin persistencia, sin R2).

Usa `POST https://api.meta.ai/v1/images/generations` con la misma auth
`MODEL_API_KEY` del resto del backend. La feature es opt-in: con
`ENABLE_IMAGE_GENERATION` apagada (default) `generate_image` devuelve
`None` sin hacer ninguna request. Nunca lanza excepciones: todo
fail-open a placeholder.
"""

import hashlib
import logging
import os
from collections import OrderedDict

import httpx
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

_META_IMAGES_URL = "https://api.meta.ai/v1/images/generations"
_DEFAULT_IMAGE_MODEL = "muse-image-1.0"
_DEFAULT_IMAGE_SIZE = "1536x1024"

# Un solo intento, sin retry: el vivo nunca se bloquea por una imagen.
_TIMEOUT_S = 25.0

# Tope de caracteres del body que se registra en los errores.
_MAX_LOG_BODY = 300

# Cache LRU en memoria por hash del prompt normalizado: evita regenerar
# duplicados cuando el mismo concepto visual se repite entre turnos.
_CACHE_MAX = 128
_cache: OrderedDict[str, str] = OrderedDict()


def _normalizar_prompt(prompt: str) -> str:
    """Minúsculas, espacios colapsados: misma idea visual, misma key."""
    return " ".join((prompt or "").strip().lower().split())


def _cache_key(prompt_norm: str, model: str, size: str) -> str:
    base = f"{model}|{size}|{prompt_norm}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> str | None:
    try:
        url = _cache.get(key)
        if url:
            _cache.move_to_end(key)
            return url
    except Exception:
        pass
    return None


def _cache_put(key: str, url: str) -> None:
    try:
        _cache[key] = url
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    except Exception:
        pass


def _extract_image_url(payload: dict) -> str | None:
    """Extrae de forma defensiva la URL de `{"data": [{"url": "..."}]}`.

    Si la respuesta trae `b64_json` en vez de URL, devuelve `None`: en esta
    fase vivo-url-only no se inyecta base64 por WS para no inflar el socket.
    Cualquier estructura borde devuelve `None` sin lanzar excepciones.
    """
    try:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return None
        first = data[0]
        if not isinstance(first, dict):
            return None
        url = first.get("url")
        if isinstance(url, str) and url.strip().startswith("https://"):
            return url.strip()
        b64 = first.get("b64_json")
        if isinstance(b64, str) and b64.strip():
            logger.info("Respuesta de imagen en b64_json: se omite (fase vivo-url-only)")
            return None
        return None
    except Exception:
        return None


def _body_acotado(response) -> str:
    """Devuelve el body de la respuesta recortado para el log (sin secretos)."""
    try:
        body = getattr(response, "text", "") or ""
    except Exception:
        return ""
    return " ".join(str(body).split())[:_MAX_LOG_BODY]


async def generate_image(prompt: str) -> str | None:
    """Genera una imagen efímera con la API de imágenes de Meta.

    Args:
        prompt: Descripción visual de la imagen a generar.

    Returns:
        URL pública https de la imagen, o `None` si la feature está
        apagada, falta la API key, el prompt está vacío, la respuesta no
        trae URL, o falla/timeoutea la request. Nunca lanza excepciones.
    """
    if (os.getenv("ENABLE_IMAGE_GENERATION", "false") or "").strip().lower() != "true":
        logger.info("Generación de imágenes deshabilitada (ENABLE_IMAGE_GENERATION)")
        return None

    clean_prompt = (prompt or "").strip()
    if not clean_prompt:
        logger.warning("Prompt vacío para generar imagen")
        return None

    api_key = (os.getenv("MODEL_API_KEY") or "").strip()
    if not api_key:
        logger.error("MODEL_API_KEY no está configurada")
        return None

    model = (os.getenv("MUSE_IMAGE_MODEL", "") or "").strip() or _DEFAULT_IMAGE_MODEL
    size = (os.getenv("MUSE_IMAGE_SIZE", "") or "").strip() or _DEFAULT_IMAGE_SIZE

    norm = _normalizar_prompt(clean_prompt)
    key = _cache_key(norm, model, size)
    cached = _cache_get(key)
    if cached:
        logger.info("Imagen reutilizada desde cache")
        return cached

    payload: dict = {
        "model": model,
        "prompt": clean_prompt,
        "n": 1,
        "size": size,
        "response_format": "url",
        "output_format": "webp",
        "reasoning_strength": "low",
        "tool_enablement": {},
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(
                _META_IMAGES_URL, headers=headers, json=payload
            )
    except Exception as e:
        logger.warning(f"Generación de imagen falló: {type(e).__name__}")
        return None

    if response.status_code != 200:
        logger.error(
            f"API de imágenes rechazó la generación ({response.status_code}): "
            f"{_body_acotado(response)}"
        )
        return None

    try:
        data = response.json()
    except Exception as e:
        logger.warning(f"Respuesta de imágenes no es JSON válido: {e}")
        return None

    url = _extract_image_url(data)
    if url is None:
        logger.warning("La respuesta de imágenes no incluye una URL")
        return None

    _cache_put(key, url)
    logger.info("Imagen generada para el vivo (url efímera)")
    return url
