"""Controller contact: formulario libre (landing + pantalla expirada) via Resend.

POST /api/contact {nombre|name, email, mensaje|message} -> {ok: True}.
- Acepta claves en espanol (contrato acordado) y en ingles (ContactForm.vue actual).
- Rate-limit en memoria: 5 req/min por IP (MVP; con multiples workers/replicas
  migrar a Redis).
- Sin RESEND_API_KEY: 503 explicativo, sin crash. Error de Resend: 502 fail-soft.
- Las keys solo viven en el backend (env); nunca se exponen ni se loguean.
"""
import html
import asyncio
import logging
import os
import threading
import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("contact")

router = APIRouter(prefix="/contact", tags=["contact"])

CONTACT_TO_DEFAULT = "contacto@devstudio.cl"
CONTACT_FROM_DEFAULT = "onboarding@resend.dev"  # remitente dev de Resend

RATE_MAX = 5
RATE_WINDOW_S = 60.0
_hits: dict[str, deque] = {}
_hits_lock = threading.Lock()


def get_contact_to() -> str:
    return os.getenv("CONTACT_TO", CONTACT_TO_DEFAULT).strip() or CONTACT_TO_DEFAULT


def get_contact_from() -> str:
    return os.getenv("CONTACT_FROM", CONTACT_FROM_DEFAULT).strip() or CONTACT_FROM_DEFAULT


def check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _hits_lock:
        window = _hits.setdefault(ip, deque())
        while window and now - window[0] > RATE_WINDOW_S:
            window.popleft()
        if len(window) >= RATE_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiados mensajes. Espera un minuto e intenta de nuevo.",
            )
        window.append(now)


class ContactRequest(BaseModel):
    # Contrato acordado en espanol; alias en ingles por el ContactForm.vue actual.
    nombre: str = Field(min_length=1, max_length=80, validation_alias="nombre")
    email: EmailStr
    mensaje: str = Field(min_length=1, max_length=2000, validation_alias="mensaje")

    model_config = {"populate_by_name": True}


def _coerce_payload(body: dict) -> dict:
    """Traduce {name,message} -> {nombre,mensaje} antes de validar Pydantic."""
    coerced = dict(body)
    if "nombre" not in coerced and "name" in coerced:
        coerced["nombre"] = coerced.pop("name")
    if "mensaje" not in coerced and "message" in coerced:
        coerced["mensaje"] = coerced.pop("message")
    return coerced


def send_contact_email(nombre: str, email: str, mensaje: str) -> None:
    """Envia via resend.Emails.send. Lanza HTTPException 503/502 segun el caso."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning("RESEND_API_KEY ausente: no se puede enviar el contacto de %s.", email)
        raise HTTPException(
            status_code=503,
            detail="El servicio de contacto no esta configurado (RESEND_API_KEY). Escríbenos a contacto@devstudio.cl.",
        )
    try:
        import resend
    except ImportError:
        logger.warning("Paquete 'resend' no instalado en el backend.")
        raise HTTPException(
            status_code=503,
            detail="El servicio de contacto no esta disponible. Escríbenos a contacto@devstudio.cl.",
        )
    safe_nombre = html.escape(nombre, quote=True)
    safe_email = html.escape(email, quote=True)
    safe_mensaje = html.escape(mensaje, quote=True).replace("\n", "<br/>")
    body_html = (
        f"<p><strong>Nombre:</strong> {safe_nombre}</p>"
        f"<p><strong>Email:</strong> {safe_email}</p>"
        f"<p><strong>Mensaje:</strong></p><p>{safe_mensaje}</p>"
    )
    try:
        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": get_contact_from(),
                "to": [get_contact_to()],
                "reply_to": email,
                "subject": f"Contacto Live Presentation AI — {nombre}",
                "html": body_html,
            }
        )
    except Exception as exc:  # noqa: BLE001 - fail-soft con mensaje claro
        logger.warning("Resend fallo al enviar contacto de %s: %s", email, exc)
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el mensaje. Inténtalo de nuevo en unos minutos.",
        )


@router.get("/health")
def health():
    return {"status": "ok", "domain": "contact"}


@router.post("")
@router.post("/")
async def create_contact(request: Request):
    """Recibe el formulario de contacto y lo reenvia por email via Resend."""
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(ip)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Body JSON invalido.")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body JSON invalido.")
    try:
        req = ContactRequest.model_validate(_coerce_payload(body))
    except Exception as exc:
        # Mensaje claro sin filtrar internals de Pydantic.
        logger.info("Contacto invalido desde %s: %s", ip, exc)
        raise HTTPException(
            status_code=422,
            detail="Datos invalidos: nombre (1-80), email valido y mensaje (1-2000).",
        )
    nombre = req.nombre.strip()
    mensaje = req.mensaje.strip()
    if not nombre or not mensaje:
        raise HTTPException(
            status_code=422,
            detail="Datos invalidos: nombre (1-80), email valido y mensaje (1-2000).",
        )
    # Resend es I/O síncrona: worker thread para no bloquear el event loop.
    await asyncio.to_thread(send_contact_email, nombre, str(req.email), mensaje)
    return {"ok": True}
