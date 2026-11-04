"""Controller trial: guard para el frontend (NO expone reloj visible).

GET /api/trial/status -> {active, expires_at}. Requiere auth Clerk
(o dev fail-open sin CLERK_SECRET_KEY). El frontend lo usa solo para
bloquear /live al vencer; nunca muestra cuenta regresiva.
"""
from fastapi import APIRouter, Depends

from backend.presentation_api.utils.auth import require_auth
from backend.presentation_api.utils.trial import trial_status

router = APIRouter(prefix="/trial", tags=["trial"])


@router.get("/status")
def status(user: dict = Depends(require_auth)):
    return trial_status(user)
