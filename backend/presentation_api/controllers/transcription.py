"""Controller transcription: proxy que oculta MODEL_API_KEY y llama a Meta Muse Voice Transcribe API."""
import asyncio
import json
import os
import shutil
import subprocess
import tempfile

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket
from backend.presentation_api.utils.auth import extract_ws_token, get_current_user, require_auth
from backend.presentation_api.utils.topic_cleaner import analyze_topic, clean_topic, normalize_language

from backend.realtime_proxy import handle_frontend_socket

router = APIRouter(tags=["transcription"])

META_ASR_URL_DEFAULT = "https://api.meta.ai/v1/asr/transcribe"
ASR_MODEL_DEFAULT = "muse-voice-transcribe-1.0"
MAX_BYTES = 32 * 1024 * 1024  # 32 MB


def get_api_key() -> str:
    return os.getenv("MODEL_API_KEY", "").strip()


def get_asr_url() -> str:
    return os.getenv("META_ASR_URL", META_ASR_URL_DEFAULT).strip()


def get_asr_model() -> str:
    return os.getenv("ASR_MODEL", ASR_MODEL_DEFAULT).strip()


@router.get("/health")
def health():
    """Estado del servicio. No expone la key, solo si esta configurada."""
    return {
        "status": "ok",
        "model": get_asr_model(),
        "api_key_configured": bool(get_api_key()),
    }


def convert_audio_bytes(data: bytes) -> bytes:
    """Convierte cualquier audio a WAV mono 16-bit PCM 24 kHz usando ffmpeg.

    Lanza HTTPException 500 con mensaje claro si ffmpeg falta o falla.
    """
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=500,
            detail="ffmpeg no esta instalado. Instálalo con: brew install ffmpeg (macOS) o apt install ffmpeg (Linux).",
        )
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix="-input")
    tmp_out_path = tmp_in.name + "-24k.wav"
    try:
        tmp_in.write(data)
        tmp_in.close()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            tmp_in.name,
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            "pcm_s16le",
            tmp_out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(tmp_out_path):
            raise HTTPException(
                status_code=500,
                detail=f"ffmpeg no pudo convertir el audio: {proc.stderr[-1000:]}",
            )
        with open(tmp_out_path, "rb") as f:
            return f.read()
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="ffmpeg no esta instalado. Instálalo con: brew install ffmpeg (macOS) o apt install ffmpeg (Linux).",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error al convertir audio: {exc}")
    finally:
        for path in (tmp_in.name, tmp_out_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass


def extract_text(payload: dict) -> str:
    """Extrae el transcript de la respuesta de Meta de forma tolerante."""
    for key in ("transcript", "text", "transcription"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    turns = payload.get("turns")
    if isinstance(turns, list):
        parts = []
        for turn in turns:
            if isinstance(turn, dict):
                for key in ("text", "transcript"):
                    value = turn.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value)
                        break
        if parts:
            return " ".join(parts)
    return ""


@router.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    user: dict = Depends(require_auth),
):
    from backend.presentation_api.utils.trial import is_trial_active

    if not is_trial_active(user):
        raise HTTPException(
            status_code=403,
            detail="Tu prueba gratuita finalizó. Escríbenos por el formulario de contacto y la extendemos.",
        )
    api_key = get_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="MODEL_API_KEY no configurada en el backend. Define MODEL_API_KEY en el archivo .env.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacio.")
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo supera el limite de 32 MB (recibido {len(raw) / 1024 / 1024:.1f} MB).",
        )

    # Conversión ffmpeg (subprocess) en worker thread para no bloquear el event loop.
    wav_bytes = await asyncio.to_thread(convert_audio_bytes, raw)

    lang = normalize_language(language)
    language_bias = ["English"] if lang == "en" else ["Spanish"]
    request_part = {
        "model": get_asr_model(),
        "audioEncoding": "WAV",
        "mode": "PUSH_TO_TALK",
        "languageBias": language_bias,
    }

    files = {
        # Parte JSON con content-type explicito application/json.
        "request": ("request.json", json.dumps(request_part), "application/json"),
        "audio": ("audio.wav", wav_bytes, "audio/wav"),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(get_asr_url(), headers=headers, files=files)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout al llamar a Meta ASR (120s). Reintenta con un audio mas corto.")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Error de red al llamar a Meta ASR: {exc}")

    if resp.status_code != 200:
        detail = f"Meta ASR devolvio {resp.status_code}."
        try:
            body = resp.json()
            detail += f" Respuesta: {json.dumps(body)[:1000]}"
        except Exception:  # noqa: BLE001
            if resp.text:
                detail += f" Respuesta: {resp.text[:1000]}"
        # Propaga codigos conocidos, el resto como 502.
        if resp.status_code in (400, 401, 403, 404, 413, 429, 500, 502, 503):
            raise HTTPException(status_code=resp.status_code, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Meta ASR devolvio una respuesta no JSON.")

    raw_text = extract_text(payload)
    analysis = analyze_topic(raw_text, language=lang)
    return {
        "text": raw_text,
        "topic": analysis["topic"],
        "keywords": analysis["keywords"],
        "cleaned": analysis["cleaned"],
        "sessionId": payload.get("sessionId") or payload.get("session_id"),
        "audioDurationMs": payload.get("audioDurationMs") or payload.get("audio_duration_ms"),
        "turns": payload.get("turns") or [],
    }


@router.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket):
    """Proxy realtime: PCM 24k del frontend hacia Meta, eventos de vuelta.

    Auth Clerk obligatoria: token en query `?token=` o header
    Sec-WebSocket-Protocol. Cierra con 4401 si falta/invalido o trial vencido.
    Sin CLERK_SECRET_KEY (dev) permite con warning (fail-open, ver auth.py).

    El POST /api/transcribe queda intacto como fallback por lotes.
    """
    from backend.presentation_api.utils.trial import is_trial_active

    token = extract_ws_token(websocket)
    try:
        user = await asyncio.to_thread(get_current_user, token)
    except HTTPException:
        # Rechazo con motivo legible: accept + error + close 4401.
        await websocket.accept()
        try:
            import json as _json

            await websocket.send_text(
                _json.dumps({"type": "error", "message": "Autenticacion requerida (Clerk)."})
            )
        except Exception:  # noqa: BLE001
            pass
        await websocket.close(code=4401)
        return
    if not is_trial_active(user):
        await websocket.accept()
        try:
            import json as _json

            await websocket.send_text(
                _json.dumps(
                    {
                        "type": "error",
                        "message": "Tu prueba gratuita finalizó. Escríbenos por el formulario de contacto y la extendemos.",
                    }
                )
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close(code=4401)
        except Exception:  # noqa: BLE001
            pass
        return
    # Clerk identity (verified sub) flows into the bridge/store; the
    # frontend user_id is never trusted. Dev-local fail-open stays in auth.
    await handle_frontend_socket(websocket, user_id=user.get("user_id") or "dev-local")
