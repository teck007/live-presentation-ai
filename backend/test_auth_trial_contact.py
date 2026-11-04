"""Tests de auth Clerk (fail-open dev / estricto), trial 24h y contacto.

No requieren red real: Clerk y Resend se mockean o se evita llamarlos
(fail-open sin CLERK_SECRET_KEY, RESEND_API_KEY ausente => 503).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.presentation_api import app
from backend.presentation_api.utils import auth as auth_mod
from backend.presentation_api.utils import trial as trial_mod


@pytest.fixture
def isolated_trial_store(monkeypatch, tmp_path):
    """Store de trial aislado por test (no toca el archivo real)."""
    monkeypatch.setenv("TRIAL_STORE_PATH", str(tmp_path / "trial.json"))
    trial_mod._first_seen.clear()
    trial_mod._store_loaded = False
    auth_mod._created_at_cache.clear()
    from backend.presentation_api.controllers import contact as contact_mod

    contact_mod._hits.clear()
    yield
    trial_mod._first_seen.clear()
    trial_mod._store_loaded = False
    auth_mod._created_at_cache.clear()
    contact_mod._hits.clear()


@pytest.fixture
def dev_mode(monkeypatch, isolated_trial_store):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    return TestClient(app)


def _user(hours_ago: float) -> dict:
    return {
        "user_id": "u-test",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    }


# --- Trial: active / expired ---


def test_trial_active_dentro_24h():
    assert trial_mod.is_trial_active(_user(1)) is True
    status = trial_mod.trial_status(_user(1))
    assert status["active"] is True
    assert "expires_at" in status


def test_trial_expired_tras_24h():
    assert trial_mod.is_trial_active(_user(25)) is False
    assert trial_mod.trial_status(_user(25))["active"] is False


def test_trial_fallback_primer_visto(isolated_trial_store):
    user = {"user_id": "nuevo-sin-created-at", "created_at": None}
    assert trial_mod.is_trial_active(user) is True
    # El inicio persiste: segunda lectura da el mismo expires_at.
    assert trial_mod.trial_expires_at(user) == trial_mod.trial_expires_at(user)


def test_trial_expires_at_24h_desde_inicio():
    now = datetime.now(timezone.utc)
    user = {"user_id": "u", "created_at": now}
    assert trial_mod.trial_expires_at(user, now=now) == now + timedelta(hours=24)


# --- Auth: fail-open dev vs estricto ---


def test_trial_status_dev_fail_open(dev_mode):
    resp = dev_mode.get("/api/trial/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["active"] is True
    assert "expires_at" in body


def test_generate_bloquea_sin_token_en_estricto(monkeypatch, isolated_trial_store):
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    client = TestClient(app)
    resp = client.post("/api/presentations/generate", json={"transcript": "hola mundo"})
    assert resp.status_code == 401


def test_generate_bloquea_trial_vencido_en_estricto(monkeypatch, isolated_trial_store):
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    expired = {"user_id": "u-vencido", "created_at": datetime.now(timezone.utc) - timedelta(hours=30)}
    with patch.object(auth_mod, "verify_clerk_token", return_value={"sub": "u-vencido"}), patch.object(
        auth_mod, "fetch_clerk_created_at", return_value=expired["created_at"]
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/presentations/generate",
            json={"transcript": "hola mundo"},
            headers={"Authorization": "Bearer fake.jwt.token"},
        )
    assert resp.status_code == 403
    assert "prueba" in resp.json()["detail"].lower()


def test_ws_rechaza_sin_token_en_estricto(monkeypatch, isolated_trial_store):
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_fake")
    client = TestClient(app)
    with client.websocket_connect("/ws/transcribe") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
    assert exc_info.value.code == 4401


# --- Contacto: validacion + resend mock + rate-limit ---


def _contact_ok_payload():
    return {"nombre": "Ana", "email": "ana@example.com", "mensaje": "Hola, quiero extender mi prueba."}


def test_contact_acepta_alias_ingles_con_resend_mockeado(dev_mode, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("CONTACT_TO", "contacto@devstudio.cl")
    sent = {}

    class FakeEmails:
        @staticmethod
        def send(params):
            sent.update(params)
            return {"id": "fake-id"}

    with patch("resend.Emails", FakeEmails):
        resp = dev_mode.post(
            "/api/contact",
            json={"name": "Ana", "email": "ana@example.com", "message": "Hola, quiero extender mi prueba."},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}
    assert sent["to"] == ["contacto@devstudio.cl"]
    assert "Ana" in sent["subject"]
    assert sent["reply_to"] == "ana@example.com"


def test_contact_escapa_html(dev_mode, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    sent = {}

    class FakeEmails:
        @staticmethod
        def send(params):
            sent.update(params)
            return {"id": "fake-id"}

    with patch("resend.Emails", FakeEmails):
        resp = dev_mode.post(
            "/api/contact", json={"nombre": "<b>Ana</b>", "email": "ana@example.com", "mensaje": "<script>x</script> hola mundo"}
        )
    assert resp.status_code == 200, resp.text
    assert "<script>" not in sent["html"]
    assert "&lt;script&gt;" in sent["html"]


def test_contact_validacion_422(dev_mode, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    # Email invalido.
    assert dev_mode.post("/api/contact", json={"nombre": "Ana", "email": "no-es-email", "mensaje": "hola mundo cruel"}).status_code == 422
    # Nombre vacio.
    assert dev_mode.post("/api/contact", json={"nombre": "", "email": "ana@example.com", "mensaje": "hola mundo cruel"}).status_code == 422
    # Mensaje vacio.
    assert dev_mode.post("/api/contact", json={"nombre": "Ana", "email": "ana@example.com", "mensaje": ""}).status_code == 422


def test_contact_sin_resend_key_da_503(dev_mode, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    resp = dev_mode.post("/api/contact", json=_contact_ok_payload())
    assert resp.status_code == 503
    assert "RESEND_API_KEY" in resp.json()["detail"]


def test_contact_rate_limit_429(dev_mode, monkeypatch):
    from backend.presentation_api.controllers import contact as contact_mod

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    contact_mod._hits.clear()

    class FakeEmails:
        @staticmethod
        def send(params):
            return {"id": "fake-id"}

    with patch("resend.Emails", FakeEmails):
        codes = [dev_mode.post("/api/contact", json=_contact_ok_payload()).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5
    assert codes[5] == 429
