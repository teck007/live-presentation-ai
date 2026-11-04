"""Trial MVP: 24h corridas desde registro, uso libre (sin tope de minutos/slides).

- Inicio del trial: `created_at` de Clerk cuando esta disponible; si no,
  primer visto del `user_id` (memoria + archivo JSON local para persistir
  reinicios). `schema.sql`/DB real sigue TODO: migrar este store cuando exista.
- El frontend NO muestra reloj (contador invisible): solo usa
  `GET /api/trial/status` -> {active, expires_at} como guard para bloquear
  `/live` al vencer.
"""
import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("trial")

TRIAL_HOURS_DEFAULT = 24
_STORE_FILENAME = ".trial_first_seen.json"

_lock = threading.Lock()
_first_seen: dict[str, str] = {}
_store_loaded = False


def trial_hours() -> float:
    try:
        return max(0.0, float(os.getenv("TRIAL_HOURS", str(TRIAL_HOURS_DEFAULT))))
    except ValueError:
        return float(TRIAL_HOURS_DEFAULT)


def _store_path() -> Path:
    custom = os.getenv("TRIAL_STORE_PATH", "").strip()
    if custom:
        return Path(custom)
    # backend/.trial_first_seen.json (junto al codigo, sin DB real todavia).
    return Path(__file__).resolve().parent.parent.parent / _STORE_FILENAME


def _load_store() -> None:
    global _store_loaded
    if _store_loaded:
        return
    _store_loaded = True
    try:
        path = _store_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(k, str) and isinstance(v, str):
                        _first_seen[k] = v
    except Exception as exc:  # noqa: BLE001 - store corrupto => arranca vacio
        logger.warning("No se pudo leer el store de trial (%s); arranca vacio.", exc)


def _save_store_locked() -> None:
    try:
        _store_path().write_text(json.dumps(_first_seen), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - persistencia best-effort
        logger.warning("No se pudo persistir el store de trial: %s", exc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def get_first_seen(user_id: str, now: datetime | None = None) -> datetime:
    """Primer visto del user_id (lo registra si es nuevo). Thread-safe."""
    _load_store()
    now = now or datetime.now(timezone.utc)
    with _lock:
        parsed = _parse_iso(_first_seen.get(user_id))
        if parsed is None:
            parsed = now
            _first_seen[user_id] = now.isoformat()
            _save_store_locked()
        return parsed


def trial_start(user: dict, now: datetime | None = None) -> datetime:
    """Inicio del trial: created_at de Clerk si existe, si no primer visto."""
    created = user.get("created_at")
    if isinstance(created, datetime):
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created
    return get_first_seen(str(user.get("user_id") or "anonymous"), now=now)


def trial_expires_at(user: dict, now: datetime | None = None) -> datetime:
    return trial_start(user, now=now) + timedelta(hours=trial_hours())


def is_trial_active(user: dict, now: datetime | None = None) -> bool:
    """True si estamos dentro de las 24h desde el inicio. Vencido exacto => False."""
    now = now or datetime.now(timezone.utc)
    return now < trial_expires_at(user, now=now)


def trial_status(user: dict, now: datetime | None = None) -> dict:
    """Payload para GET /api/trial/status (guard del frontend, NO reloj visible)."""
    now = now or datetime.now(timezone.utc)
    expires = trial_expires_at(user, now=now)
    return {"active": now < expires, "expires_at": expires.isoformat()}
