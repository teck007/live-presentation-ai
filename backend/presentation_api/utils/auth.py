"""Auth Clerk via JWT/JWKS para el backend.

Flujo MVP:
- El frontend envia el Clerk session token en `Authorization: Bearer <token>`
  (o `?token=` en WS).
- Se valida la firma RS256 contra el JWKS del issuer (`{iss}/.well-known/jwks.json`)
  con cache en memoria (PyJWT `PyJWKClient`).
- `created_at` se intenta obtener de Clerk Backend API (`/v1/users/{id}`) si hay
  `CLERK_SECRET_KEY`; si no, queda en None y el trial usa primer visto.

Fail-open SOLO en dev: si no hay `CLERK_SECRET_KEY` configurada, se permite el
acceso con un usuario local `dev-local` y warning en log, para no bloquear el
desarrollo/prueba manual. EN PRODUCCION esto debe ser estricto: configurar
siempre `CLERK_SECRET_KEY` (con secret presente, token ausente o invalido => 401).
"""
import base64
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, Request

logger = logging.getLogger("auth")

DEV_USER_ID = "dev-local"

# Cache de PyJWKClient por issuer (el cliente ya cachea las keys internamente).
_jwks_clients: dict[str, object] = {}
# Cache de created_at por user_id para no pegar a Clerk API en cada request.
_created_at_cache: dict[str, datetime | None] = {}


def is_strict() -> bool:
    """True cuando hay CLERK_SECRET_KEY: ahi la auth es obligatoria."""
    return bool(os.getenv("CLERK_SECRET_KEY", "").strip())


def _b64_json(part: str) -> dict:
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())


def _unverified_claims(token: str) -> tuple[dict, dict]:
    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError("JWT malformado (se esperaban 3 segmentos).")
    return _b64_json(segments[0]), _b64_json(segments[1])


def _jwks_client_for(issuer: str):
    import jwt

    url = issuer.rstrip("/") + "/.well-known/jwks.json"
    client = _jwks_clients.get(url)
    if client is None:
        client = jwt.PyJWKClient(url, cache_keys=True, max_cached_keys=16)
        _jwks_clients[url] = client
    return client


def verify_clerk_token(token: str) -> dict:
    """Valida firma RS256 + expiracion contra el JWKS del issuer.

    Devuelve los claims decodificados. Lanza ValueError/Exception si invalido.
    """
    import jwt

    header, claims = _unverified_claims(token)
    issuer = str(claims.get("iss") or "").strip()
    if not issuer:
        raise ValueError("JWT sin claim 'iss'; no se puede resolver el JWKS.")
    if header.get("alg") != "RS256":
        raise ValueError(f"Algoritmo JWT no soportado: {header.get('alg')!r}.")
    client = _jwks_client_for(issuer)
    signing_key = client.get_signing_key_from_jwt(token)
    # Clerk session tokens: iss = Frontend API URL; sub = user_id.
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        options={"require": ["exp", "iss", "sub"]},
    )


def fetch_clerk_created_at(user_id: str) -> datetime | None:
    """Crea `created_at` del usuario via Clerk Backend API. Fail-soft -> None."""
    if user_id in _created_at_cache:
        return _created_at_cache[user_id]
    secret = os.getenv("CLERK_SECRET_KEY", "").strip()
    if not secret:
        _created_at_cache[user_id] = None
        return None
    try:
        # Clerk expone created_at en milisegundos epoch en GET /v1/users/{id}.
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=5.0,
        )
        if resp.status_code != 200:
            logger.warning("Clerk /users %s -> %s; uso primer visto.", user_id, resp.status_code)
            _created_at_cache[user_id] = None
            return None
        raw = resp.json().get("created_at")
        created = None
        if isinstance(raw, (int, float)):
            # Clerk usa ms; tolera segundos por si cambia el formato.
            ts = raw / 1000.0 if raw > 1e12 else float(raw)
            created = datetime.fromtimestamp(ts, tz=timezone.utc)
        _created_at_cache[user_id] = created
        return created
    except Exception as exc:  # noqa: BLE001 - fail-soft a primer visto
        logger.warning("No se pudo obtener created_at de Clerk (%s); uso primer visto.", exc)
        _created_at_cache[user_id] = None
        return None


def get_current_user(token: str | None) -> dict:
    """Resuelve el usuario desde el token.

    Devuelve {"user_id": str, "created_at": datetime|None}.
    - Sin CLERK_SECRET_KEY (dev): fail-open con usuario dev-local + warning.
    - Con secret: token ausente/invalido => HTTPException 401.
    """
    if not is_strict():
        logger.warning(
            "CLERK_SECRET_KEY ausente: auth en modo dev fail-open (usuario %s). "
            "En produccion configurar CLERK_SECRET_KEY para exigir JWT.",
            DEV_USER_ID,
        )
        return {"user_id": DEV_USER_ID, "created_at": None}
    if not token:
        raise HTTPException(status_code=401, detail="Falta token de autenticacion (Clerk).")
    try:
        claims = verify_clerk_token(token)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.info("JWT Clerk invalido: %s", exc)
        raise HTTPException(status_code=401, detail="Token invalido o expirado.")
    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin subject (sub).")
    return {"user_id": user_id, "created_at": fetch_clerk_created_at(user_id)}


def extract_token(request: Request) -> str | None:
    """Authorization: Bearer <t> tiene prioridad; fallback a query ?token=."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token
    query_token = request.query_params.get("token")
    if query_token and query_token.strip():
        return query_token.strip()
    return None


async def require_auth(request: Request) -> dict:
    """Dependency FastAPI: usuario autenticado (o dev fail-open sin secret)."""
    # JWKS/Clerk son I/O síncrona: se ejecutan en worker thread para no bloquear el loop.
    return await asyncio.to_thread(get_current_user, extract_token(request))


def extract_ws_token(websocket) -> str | None:
    """Token WS: query `?token=` o header Sec-WebSocket-Protocol (primer valor)."""
    try:
        query_token = websocket.query_params.get("token")
    except Exception:  # noqa: BLE001
        query_token = None
    if query_token and query_token.strip():
        return query_token.strip()
    try:
        proto = websocket.headers.get("sec-websocket-protocol", "")
    except Exception:  # noqa: BLE001
        proto = ""
    if proto:
        first = proto.split(",")[0].strip()
        if first:
            return first
    return None
