"""Tests del proxy de transcripcion. No requieren ffmpeg ni red real."""
import asyncio
import io
import json
import shutil
import time
import wave
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.presentation_api.controllers.transcription as transcription
from backend.presentation_api import app


def generar_wav_1s() -> bytes:
    """Genera un WAV valido de 1 segundo (tono 440 Hz, mono 16-bit 24 kHz)."""
    buffer = io.BytesIO()
    sample_rate = 24000
    n_frames = sample_rate  # 1 segundo
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        import math
        import struct

        for i in range(n_frames):
            sample = int(10000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            wf.writeframes(struct.pack("<h", sample))
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture
def client_sin_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _sin_jev_real(monkeypatch):
    """La suite nunca llama al API real de Jev: sin key el gate da fail-open.

    Sin esto, los tests que no mockean decide_slide_action dependen del
    veredicto en vivo (costo real, latencia variable, resultados fragiles).
    Tampoco depende del .env local para auth: sin CLERK_SECRET_KEY rige el
    fail-open dev (usuario dev-local) y los endpoints responden sin token.
    """
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)


def test_health_sin_key(client_sin_key):
    resp = client_sin_key.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model"] == "muse-voice-transcribe-1.0"
    assert body["api_key_configured"] is False


def test_transcribe_sin_key_da_503(client_sin_key):
    wav = generar_wav_1s()
    resp = client_sin_key.post(
        "/api/transcribe", files={"file": ("audio.wav", wav, "audio/wav")}
    )
    assert resp.status_code == 503
    assert "MODEL_API_KEY" in resp.json()["detail"]


def test_transcribe_ok_mockeado(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    client = TestClient(app)
    wav = generar_wav_1s()

    fake = FakeResponse(
        200,
        {
            "transcript": "hola mundo",
            "sessionId": "abc123",
            "audioDurationMs": 1000,
            "turns": [],
        },
    )
    mock_post = AsyncMock(return_value=fake)

    with (
        patch.object(transcription, "convert_audio_bytes", return_value=wav),
        patch("httpx.AsyncClient.post", mock_post),
    ):
        resp = client.post(
            "/api/transcribe", files={"file": ("audio.wav", wav, "audio/wav")}
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["text"] == "hola mundo"
    assert body["sessionId"] == "abc123"

    # Verifica que se llamo a Meta con multipart y auth.
    _, kwargs = mock_post.call_args
    assert "files" in kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer LLM_test"
    assert "request" in kwargs["files"]
    assert "audio" in kwargs["files"]


def test_error_meta_propagado(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    client = TestClient(app)
    wav = generar_wav_1s()

    fake = FakeResponse(429, {"error": "rate limited"}, text='{"error":"rate limited"}')
    mock_post = AsyncMock(return_value=fake)

    with (
        patch.object(transcription, "convert_audio_bytes", return_value=wav),
        patch("httpx.AsyncClient.post", mock_post),
    ):
        resp = client.post(
            "/api/transcribe", files={"file": ("audio.wav", wav, "audio/wav")}
        )

    assert resp.status_code == 429
    assert "429" in resp.json()["detail"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no instalado")
def test_conversion_real_si_ffmpeg_existe():
    wav = generar_wav_1s()
    out = transcription.convert_audio_bytes(wav)
    # Un WAV valido empieza con RIFF.
    assert out[:4] == b"RIFF"


# --- U1 ws-llm-slides-async: RED backend (seq/dedupe/stale/filtered/no-bloqueo) ---

class _FakeFrontend:
    def __init__(self):
        self.sent: list[dict] = []
        self.closed_code = None

    async def send_text(self, payload: str):
        self.sent.append(json.loads(payload))

    async def close(self, code: int = 1000):
        self.closed_code = code


def _make_bridge():
    from backend.realtime_proxy import RealtimeBridge

    front = _FakeFrontend()
    bridge = RealtimeBridge(front, {"silence_pause_ms": 15000, "pre_roll_ms": 0, "vad_threshold": 0.02})
    return bridge, front


def _speech_complete(turn_id: str, text: str = "el cambio climatico avanza") -> dict:
    return {"type": "speechComplete", "turnId": turn_id, "transcript": text}


def test_ws_dedupe_turnId_single_spawn():
    """Mismo turnId dos veces -> un solo slide_pending y una sola tarea."""
    from backend.presentation_api.utils import llm_client as llm_mod

    async def scenario():
        bridge, front = _make_bridge()
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t1"))
            await bridge.handle_speech_complete(_speech_complete("t1"))
            # Da tiempo a que las tareas terminen sin bloquear relay.
            for _ in range(100):
                if gen.call_count >= 1:
                    break
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.05)
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        pendings = [m for m in front.sent if m.get("type") == "slide_pending"]
        assert len(pendings) == 1
        assert gen.call_count == 1
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_seq_order_monotonic():
    """Dos turnos nuevos -> seq 1, 2 en orden de llegada."""
    from backend.presentation_api.utils import llm_client as llm_mod

    async def scenario():
        bridge, front = _make_bridge()
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-a"))
            await bridge.handle_speech_complete(_speech_complete("t-b"))
            await bridge.cancel_slide_tasks()
        pendings = [m for m in front.sent if m.get("type") == "slide_pending"]
        assert [m["seq"] for m in pendings] == [1, 2]
        assert pendings[0]["turnId"] == "t-a"
        assert pendings[1]["turnId"] == "t-b"

    asyncio.run(scenario())


def test_ws_stale_pre_emit_drop():
    """Resultado v1 que termina tras bump a v2 -> no emite slide."""

    async def scenario():
        bridge, front = _make_bridge()
        started = asyncio.Event()

        def slow_generate(transcript, topic, keywords=None, *args, **kwargs):
            started.set()
            # Simula LLM lento sin bloquear el loop de eventos del test.
            time.sleep(0.3)
            return {"layout": "title_text", "title": "T", "text": "x",
                    "bullets": [], "keywords": [], "relevant": True, "filtered": False}

        from backend.presentation_api.utils import llm_client as llm_mod

        with (
            patch.object(llm_mod, "generate_slide", side_effect=slow_generate),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-stale"))
            assert await asyncio.wait_for(started.wait(), timeout=2)
            bridge.confirm_topic_version(bridge.current_topic_version + 1)
            await asyncio.sleep(0.6)
            slides = [m for m in front.sent if m.get("type") == "slide"]
            assert slides == []
            await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_filtered_silence_no_llm():
    """Solo transcript vacio/corto filtra sin LLM; off-topic va al LLM (decide el modelo)."""

    async def scenario():
        bridge, front = _make_bridge()
        bridge.current_topic = "cambio climatico"
        from backend.presentation_api.utils import llm_client as llm_mod

        with patch.object(llm_mod, "generate_slide") as gen:
            await bridge.handle_speech_complete(_speech_complete("t-off", "  "))
            await asyncio.sleep(0.05)
            await bridge.cancel_slide_tasks()
        assert gen.call_count == 0
        filtered = [m for m in front.sent if m.get("type") == "slide_filtered"]
        assert len(filtered) == 1
        assert filtered[0]["turnId"] == "t-off"
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert slides == []

    asyncio.run(scenario())


def test_ws_relay_no_bloqueante_con_llm_lento():
    """Con LLM lento en t1, el pending de t2 llega sin esperar al slide."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod

        def slow_generate(transcript, topic, keywords=None, *args, **kwargs):
            time.sleep(0.5)
            return {"layout": "title_text", "title": "T", "text": "x",
                    "bullets": [], "keywords": [], "relevant": True, "filtered": False}

        with (
            patch.object(llm_mod, "generate_slide", side_effect=slow_generate),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            t0 = time.monotonic()
            await bridge.handle_speech_complete(_speech_complete("t1"))
            await bridge.handle_speech_complete(_speech_complete("t2"))
            elapsed = time.monotonic() - t0
            # El segundo pending debe emitirse sin esperar los 0.5s del LLM.
            assert elapsed < 0.4
            pendings = [m for m in front.sent if m.get("type") == "slide_pending"]
            assert [m["turnId"] for m in pendings] == ["t1", "t2"]
            await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


# --- REMEDIACION ws-llm-slides-async: contrato, text-only, error, regen (RED primero) ---

def test_ws_event_contract_pending_terminal_shapes():
    """Contrato: pending + terminal llevan turnId/seq/topicVersion; terminal unico por turno."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": ["k"], "relevant": True, "filtered": False}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-contrato"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        by_turn: dict[str, list[dict]] = {}
        for m in front.sent:
            if m.get("type") in ("slide_pending", "slide", "slide_filtered", "slide_error"):
                for key in ("turnId", "seq", "topicVersion"):
                    assert key in m, f"evento {m.get('type')} sin {key}: {m}"
                by_turn.setdefault(m["turnId"], []).append(m)
        assert "t-contrato" in by_turn
        kinds = [m["type"] for m in by_turn["t-contrato"]]
        assert kinds[0] == "slide_pending"
        terminals = [k for k in kinds[1:] if k in ("slide", "slide_filtered", "slide_error")]
        assert len(terminals) == 1, f"un solo terminal por turno nuevo: {kinds}"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_slide_text_only_no_media():
    """Contrato progresivo: el slide sale inmediato con texto; la imagen es
    opcional y llega después por slide_image_updated (nunca bloquea)."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": ["b1"], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-textonly"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert len(slides) == 1
        payload = slides[0]
        for banned in ("imageUrl", "image_url", "media", "mediaUrl"):
            assert banned not in payload, f"contrato progresivo no admite {banned}"
        # image/imagen_prompt son opcionales ("" o https), nunca otras formas.
        for key in ("image", "imagen_prompt"):
            assert key in payload
            assert isinstance(payload[key], str)
            assert payload[key] == "" or not payload[key].startswith("data:")
        assert payload["title"]
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_slide_error_on_llm_failure():
    """LLM que falla -> slide_error con turnId/seq/version y mensaje, sin slide."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod

        def boom(transcript, topic, keywords=None, *args, **kwargs):
            raise RuntimeError("llm caido")

        with (
            patch.object(llm_mod, "generate_slide", side_effect=boom),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-error"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        errors = [m for m in front.sent if m.get("type") == "slide_error"]
        assert len(errors) == 1
        assert errors[0]["turnId"] == "t-error"
        assert "message" in errors[0] and errors[0]["message"]
        assert [m for m in front.sent if m.get("type") == "slide"] == []
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_regen_replaced_new_seq_same_turn():
    """Regen de turno conocido -> slide_replaced con mismo turnId y seq nuevo."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "T2", "text": "nuevo",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-regen"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
            first = [m for m in front.sent if m.get("type") == "slide"]
            assert len(first) == 1
            ok = await bridge.request_regen("t-regen", "el cambio climatico avanza mas")
            assert ok is True
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        replaced = [m for m in front.sent if m.get("type") == "slide_replaced"]
        assert len(replaced) == 1
        assert replaced[0]["turnId"] == "t-regen"
        assert replaced[0]["seq"] > first[0]["seq"]
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_regen_filtered_emits_removed():
    """Regen con resultado filtrado -> slide_removed con turnId y version."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        filtered_slide = {"layout": "title_text", "title": "", "text": "",
                          "bullets": [], "keywords": [], "relevant": False, "filtered": True}
        with patch("backend.realtime_proxy.is_relevant", return_value=True):
            with patch.object(llm_mod, "generate_slide", return_value=fake_slide):
                await bridge.handle_speech_complete(_speech_complete("t-regen-rm"))
                for task in list(bridge.pending_tasks.values()):
                    try:
                        await asyncio.wait_for(task, timeout=2)
                    except Exception:
                        pass
            with patch.object(llm_mod, "generate_slide", return_value=filtered_slide):
                ok = await bridge.request_regen("t-regen-rm", "texto ya irrelevante")
                assert ok is True
                for task in list(bridge.pending_tasks.values()):
                    try:
                        await asyncio.wait_for(task, timeout=2)
                    except Exception:
                        pass
        removed = [m for m in front.sent if m.get("type") == "slide_removed"]
        assert len(removed) == 1
        assert removed[0]["turnId"] == "t-regen-rm"
        assert removed[0]["topicVersion"] == bridge.current_topic_version
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_regen_unknown_turn_rejected():
    """Regen de turno desconocido -> False y ningun evento slide_* nuevo."""

    async def scenario():
        bridge, front = _make_bridge()
        ok = await bridge.request_regen("t-fantasma", "nada")
        assert ok is False
        assert [m for m in front.sent if str(m.get("type", "")).startswith("slide_")] == []
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_topic_filter_fix_offtopic_calls_llm():
    """Regla nueva: con topic definido, off-topic SI va al LLM (el modelo decide)."""

    async def scenario():
        bridge, front = _make_bridge()
        bridge.current_topic = "cambio climatico"
        bridge.current_keywords = ["clima"]
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "", "text": "",
                      "bullets": [], "keywords": [], "relevant": False, "filtered": True}
        with (
            # Gate fail-open: este test verifica el ruteo al LLM, no el veredicto Jev.
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "fail-open: test", "raw": {}}),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
        ):
            event = _speech_complete("t-fix-off", "futbol y goles del partido")
            event["topic"] = "cocina"
            event["keywords"] = ["cocina"]
            await bridge.handle_speech_complete(event)
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        assert gen.call_count == 1
        # El topic usado es el de sesion, no el del evento.
        called_topic = gen.call_args[0][1] if gen.call_args else None
        assert called_topic == "cambio climatico"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_topic_filter_fix_empty_no_llm():
    """Regla nueva: transcript vacio/corto no llama al LLM (unico short-circuit)."""

    async def scenario():
        bridge, front = _make_bridge()
        bridge.current_topic = "cambio climatico"
        from backend.presentation_api.utils import llm_client as llm_mod
        with patch.object(llm_mod, "generate_slide") as gen:
            await bridge.handle_speech_complete(_speech_complete("t-fix-empty", "  "))
            await asyncio.sleep(0.05)
            await bridge.cancel_slide_tasks()
        assert gen.call_count == 0
        filtered = [m for m in front.sent if m.get("type") == "slide_filtered"]
        assert len(filtered) == 1
        assert filtered[0]["turnId"] == "t-fix-empty"

    asyncio.run(scenario())


def test_ws_topic_filter_fix_free_mode_ignores_event_topic():
    """Regla nueva: sin topic de sesion, todo va al LLM aunque el evento traiga topic."""

    async def scenario():
        bridge, front = _make_bridge()
        bridge.current_topic = ""
        bridge.current_keywords = []
        from backend.presentation_api.utils import llm_client as llm_mod
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen:
            event = _speech_complete("t-fix-free", "receta de cocina con ajo")
            event["topic"] = "cambio climatico"
            event["keywords"] = ["clima"]
            await bridge.handle_speech_complete(event)
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        assert gen.call_count == 1
        called_topic = gen.call_args[0][1] if gen.call_args else None
        assert called_topic == ""
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_semaphore_cap_two_concurrent():
    """Con 4 turnos rapidos, nunca hay mas de 2 generate_slide concurrentes."""
    import threading

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import llm_client as llm_mod

        active = 0
        max_active = 0
        lock = threading.Lock()

        def counting_generate(transcript, topic, keywords=None, *args, **kwargs):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            try:
                time.sleep(0.2)
            finally:
                with lock:
                    active -= 1
            return {"layout": "title_text", "title": "T", "text": "x",
                    "bullets": [], "keywords": [], "relevant": True, "filtered": False}

        with (
            patch.object(llm_mod, "generate_slide", side_effect=counting_generate),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            for i in range(4):
                await bridge.handle_speech_complete(_speech_complete(f"t-cap-{i}"))
            await asyncio.sleep(1.5)
            await bridge.cancel_slide_tasks()
        assert max_active <= 2
        assert max_active >= 1  # el codigo bajo test realmente corrio
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert len(slides) == 4

    asyncio.run(scenario())


def test_ws_opening_seq1_keeps_hero_second_degrades():
    """WS: seq==1 permite hero; segundo slide misma version degrada a split/title."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        def hero_generate(transcript, topic, keywords=None, *args, **kwargs):
            return {
                "layout": "hero_cover", "title": "T", "text": "apertura",
                "bullets": ["a"], "image": "https://example.com/a.jpg",
                "keywords": [], "relevant": True, "filtered": False,
            }

        seen = {}

        def capture(transcript, topic, keywords=None, *args, **kwargs):
            is_open = kwargs.get("is_opening", args[2] if len(args) >= 3 else None)
            seen.setdefault("calls", []).append(is_open)
            return hero_generate(transcript, topic, keywords, *args, **kwargs)

        with (
            # Gate aislado en new: este test verifica degradacion de hero,
            # no el veredicto del gate (fail-open conservador haria keep).
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "jev:new", "raw": {}}),
            patch.object(llm_mod, "generate_slide", side_effect=capture),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-open-1"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
            await bridge.handle_speech_complete(_speech_complete("t-open-2"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert len(slides) == 2
        assert slides[0]["layout"] == "hero_cover"
        assert slides[1]["layout"] in ("split_media", "title_text")
        assert seen["calls"][0] is True
        assert seen["calls"][1] is False
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_rest_respects_is_opening_flag(monkeypatch):
    """REST: is_opening True permite hero; False/omitido degrada."""
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.controllers import presentation as pres_mod

    client = TestClient(app_mod)

    def fake_generate(transcript, topic, keywords=None, *args, **kwargs):
        return {"layout": "hero_cover", "title": "T", "text": "apertura",
                "bullets": ["a"], "image": "https://example.com/a.jpg",
                "keywords": [], "relevant": True, "filtered": False}

    with patch.object(pres_mod, "generate_slide", side_effect=fake_generate):
        r_open = client.post("/api/presentations/generate", json={
            "transcript": "apertura del tema principal", "topic": "clima",
            "keywords": [], "is_opening": True,
        })
        assert r_open.status_code == 200, r_open.text
        assert r_open.json()["layout"] == "hero_cover"
        r_mid = client.post("/api/presentations/generate", json={
            "transcript": "apertura del tema principal", "topic": "clima",
            "keywords": [], "is_opening": False,
        })
        assert r_mid.status_code == 200, r_mid.text
        assert r_mid.json()["layout"] in ("split_media", "title_text")
        r_omit = client.post("/api/presentations/generate", json={
            "transcript": "apertura del tema principal", "topic": "clima",
            "keywords": [],
        })
        assert r_omit.status_code == 200, r_omit.text
        assert r_omit.json()["layout"] in ("split_media", "title_text")


# --- JEV gate: keep/update/new + fail-open + slide_kept + windows ---

def _make_bridge_win(window_s: float = 0.16):
    from backend.realtime_proxy import RealtimeBridge

    front = _FakeFrontend()
    bridge = RealtimeBridge(
        front,
        {
            "silence_pause_ms": 15000,
            "pre_roll_ms": 0,
            "vad_threshold": 0.02,
            "slide_window_s": window_s,
            "window_duty_cycle": "",
            "slide_context_chars": 600,
        },
    )
    return bridge, front


async def _drain_bridge(bridge, timeout: float = 2.0) -> None:
    for task in list(bridge.pending_tasks.values()):
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except Exception:
            pass


def _loud_frame() -> bytes:
    import struct

    return struct.pack("<1920h", *([12000] * 1920))


def test_jev_gate_new_paints_slide():
    """Gate new -> generate_slide corre y pinta slide con contrato."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "jev:new", "raw": {}}),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
        ):
            await bridge.handle_speech_complete(_speech_complete("t-jev-new"))
            await _drain_bridge(bridge)
        assert gen.call_count == 1
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert len(slides) == 1
        assert slides[0]["turnId"] == "t-jev-new"
        for key in ("turnId", "seq", "topicVersion"):
            assert key in slides[0]
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_jev_gate_keep_emits_kept_no_llm():
    """Gate keep -> slide_kept terminal con contrato, sin llamar al LLM."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        decisions = [
            {"relevant": True, "action": "keep", "reason": "jev:keep", "raw": {}},
            {"relevant": True, "action": "new", "reason": "jev:new", "raw": {}},
        ]
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action", side_effect=decisions),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
        ):
            await bridge.handle_speech_complete(_speech_complete("t-jev-keep"))
            await _drain_bridge(bridge)
            await bridge.handle_speech_complete(_speech_complete("t-jev-next"))
            await _drain_bridge(bridge)
        # Solo el segundo turno llego al LLM.
        assert gen.call_count == 1
        kept = [m for m in front.sent if m.get("type") == "slide_kept"]
        assert len(kept) == 1
        assert kept[0]["turnId"] == "t-jev-keep"
        assert kept[0]["seq"] == 1
        for key in ("turnId", "seq", "topicVersion"):
            assert key in kept[0]
        slides = [m for m in front.sent if m.get("type") == "slide"]
        assert len(slides) == 1
        assert slides[0]["seq"] == 2
        assert slides[0]["turnId"] == "t-jev-next"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_jev_gate_update_emits_replaced_with_fused_context():
    """Gate update -> slide_replaced y el LLM recibe contexto fusionado."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        bridge.slide_context_tail = "contexto previo del slide"
        fake_slide = {"layout": "title_text", "title": "T2", "text": "nuevo",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "update",
                                       "reason": "jev:update", "raw": {}}),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
        ):
            await bridge.handle_speech_complete(_speech_complete("t-jev-upd"))
            await _drain_bridge(bridge)
        assert gen.call_count == 1
        fused = gen.call_args[0][0]
        assert "contexto previo del slide" in fused
        replaced = [m for m in front.sent if m.get("type") == "slide_replaced"]
        assert len(replaced) == 1
        assert replaced[0]["turnId"] == "t-jev-upd"
        assert [m for m in front.sent if m.get("type") == "slide"] == []
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_jev_schema_invalid_fail_open():
    """Respuesta Jev invalida o HTTP error -> fail-open new (pinta igual)."""

    async def scenario():
        from backend.presentation_api.utils import jev_client as jev_mod

        assert jev_mod.parse_decision_payload({"nonsense": 1})["action"] == "new"
        assert jev_mod.parse_decision_payload(None)["action"] == "new"
        assert jev_mod.parse_decision_payload(
            {"answers": {"slide_action": {"choice": "borrar"}}})["action"] == "new"
        # Confianza bajo el umbral -> fail-open new.
        low = {"answers": {"on_topic": {"probability": 0.9},
                           "slide_action": {"choice": "keep", "confidence": 0.1}}}
        assert jev_mod.parse_decision_payload(low)["action"] == "new"
        # Off-topic valido -> keep (no pinta).
        off = {"answers": {"on_topic": {"probability": 0.1},
                           "slide_action": {"choice": "new", "confidence": 0.99}}}
        parsed = jev_mod.parse_decision_payload(off)
        assert parsed["relevant"] is False and parsed["action"] == "keep"

    asyncio.run(scenario())


def test_jev_payload_shape_dict_questions():
    """El payload Jev usa questions como dict con type (schema oficial)."""
    from backend.presentation_api.utils import jev_client as jev_mod

    payload = jev_mod.build_payload(
        "el ciclo del agua", ["lluvia"], "general",
        "la lluvia cae al suelo", {"titulo": "T", "resumen": "r"},
    )
    questions = payload["questions"]
    assert isinstance(questions, dict)
    assert set(questions) == {"on_topic", "slide_action"}
    assert questions["on_topic"]["type"] == "noul"
    assert questions["slide_action"]["type"] == "choice"
    for q in questions.values():
        assert "kind" not in q and "options" not in q and "id" not in q
    assert set(questions["slide_action"]["criteria"]) == {"keep", "update", "new"}
    assert "state" in payload and "model" in payload


def test_jev_parse_official_response_shape():
    """Parsea la forma oficial: noul prob + choice/confidence/probabilities."""
    from backend.presentation_api.utils import jev_client as jev_mod

    raw = {"answers": {
        "on_topic": {"type": "noul", "noul": 0.92},
        "slide_action": {"type": "choice", "choice": "new",
                         "confidence": 0.88,
                         "probabilities": {"keep": 0.05, "update": 0.07, "new": 0.88}},
    }}
    parsed = jev_mod.parse_decision_payload(raw)
    assert parsed["relevant"] is True and parsed["action"] == "new"

    off = {"answers": {
        "on_topic": {"type": "noul", "noul": 0.1},
        "slide_action": {"type": "choice", "choice": "new",
                         "confidence": 0.99,
                         "probabilities": {"keep": 0.0, "update": 0.01, "new": 0.99}},
    }}
    parsed_off = jev_mod.parse_decision_payload(off)
    assert parsed_off["relevant"] is False and parsed_off["action"] == "keep"

    bad = {"answers": {
        "on_topic": {"type": "noul", "noul": 0.9},
        "slide_action": {"type": "choice", "choice": "borrar", "confidence": 0.99},
    }}
    assert jev_mod.parse_decision_payload(bad)["reason"] == "fail-open: invalid-choice"


def test_jev_timeout_fail_open(monkeypatch):
    """Timeout de red Jev -> fail-open new, el slide se genera igual."""
    import httpx

    from backend.presentation_api.utils import jev_client as jev_mod

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def _boom(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    with patch.object(jev_mod.httpx, "post", side_effect=_boom):
        result = jev_mod.decide_slide_action("tema", [], "general", "texto", {})
    assert result["relevant"] is True
    assert result["action"] == "new"
    assert result["reason"].startswith("fail-open")


def test_jev_window_forces_eval_without_speech_complete():
    """Ventana VAD cerrada con parcial y sin speechComplete -> eval forzada."""

    async def scenario():
        bridge, front = _make_bridge_win(0.16)
        bridge.streaming = True
        bridge.upstream = object()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "jev:new", "raw": {}}),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide) as gen,
        ):
            bridge._note_meta_event({"type": "speechStart", "turnId": "tw1"})
            bridge._note_meta_event({"type": "transcript", "turnId": "tw1",
                                     "transcript": "el ciclo del agua y la lluvia",
                                     "final": False})
            for _ in range(3):
                await bridge.on_audio_frame(_loud_frame())
            await _drain_bridge(bridge)
        assert gen.call_count == 1
        pendings = [m for m in front.sent if m.get("type") == "slide_pending"]
        assert pendings and pendings[0]["turnId"].startswith("tw1#w")
        # El turno original sigue elegible para un speechComplete posterior.
        assert "tw1" not in bridge.seen_turnIds
        # El stream PCM no se corto: Meta endpointing sigue primario.
        assert bridge.streaming is True and bridge.upstream is not None
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


# --- Word-count windows: target / filler / cap / grace / tail ---

def _make_bridge_words(target=5, max_voice=60.0, min_content=2, grace=5.0,
                       legacy=3600.0):
    from backend.realtime_proxy import RealtimeBridge

    front = _FakeFrontend()
    bridge = RealtimeBridge(
        front,
        {
            "silence_pause_ms": 15000,
            "pre_roll_ms": 0,
            "vad_threshold": 0.02,
            "slide_window_s": legacy,
            "window_target_words": target,
            "window_max_voice_s": max_voice,
            "window_min_content_words": min_content,
            "window_grace_s": grace,
            "window_duty_cycle": "",
            "slide_context_chars": 600,
        },
    )
    return bridge, front


def test_window_fires_by_word_count_with_delta():
    """Parcial >= TARGET con punto final -> emite ventana con solo el delta."""

    async def scenario():
        bridge, front = _make_bridge_words()
        bridge.streaming = True
        bridge.upstream = object()
        with patch.object(bridge, "_spawn_gated_slide",
                          new=AsyncMock()) as spawn:
            bridge._note_meta_event({"type": "speechStart", "turnId": "twords"})
            bridge._note_meta_event({"type": "transcript", "turnId": "twords",
                                     "transcript": "el ciclo del agua produce lluvia intensa.",
                                     "final": False})
            await bridge.on_audio_frame(_loud_frame())
        assert spawn.await_count == 1
        args = spawn.await_args[0]
        assert args[0].startswith("twords#w")
        assert args[3] == "el ciclo del agua produce lluvia intensa."
        assert bridge.last_forced_text["twords"] == \
            "el ciclo del agua produce lluvia intensa."
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_window_short_filler_does_not_call_jev():
    """Solo muletillas (contenido < MIN) -> acumula sin llamar al LLM."""

    async def scenario():
        bridge, front = _make_bridge_words()
        bridge.streaming = True
        bridge.upstream = object()
        from backend.presentation_api.utils import llm_client as llm_mod

        with patch.object(llm_mod, "generate_slide") as gen:
            bridge._note_meta_event({"type": "speechStart", "turnId": "tfill"})
            bridge._note_meta_event({"type": "transcript", "turnId": "tfill",
                                     "transcript": "eh em mmm este bueno pues",
                                     "final": False})
            for _ in range(10):
                await bridge.on_audio_frame(_loud_frame())
            await asyncio.sleep(0.05)
            await bridge.cancel_slide_tasks()
        assert gen.call_count == 0
        pendings = [m for m in front.sent if m.get("type") == "slide_pending"]
        assert pendings == []

    asyncio.run(scenario())


def test_window_cap_fires_on_slow_speech():
    """vad_window_s >= MAX con poco texto -> emite igual (habla lenta)."""

    async def scenario():
        bridge, front = _make_bridge_words(target=18, max_voice=5.0,
                                           min_content=2, legacy=3600.0)
        bridge.streaming = True
        bridge.upstream = object()
        with patch.object(bridge, "_spawn_gated_slide",
                          new=AsyncMock()) as spawn:
            bridge._note_meta_event({"type": "speechStart", "turnId": "tslow"})
            bridge._note_meta_event({"type": "transcript", "turnId": "tslow",
                                     "transcript": "el ciclo del agua",
                                     "final": False})
            for _ in range(70):  # 70 * 0.08s = 5.6s >= MAX 5.0
                await bridge.on_audio_frame(_loud_frame())
                if spawn.await_count:
                    break
        assert spawn.await_count == 1
        assert spawn.await_args[0][3] == "el ciclo del agua"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_window_grace_waits_for_punctuation():
    """Parcial >= TARGET sin punto -> arma gracia; al vencer, emite."""

    async def scenario():
        bridge, front = _make_bridge_words()
        bridge.streaming = True
        bridge.upstream = object()
        with patch.object(bridge, "_spawn_gated_slide",
                          new=AsyncMock()) as spawn:
            bridge._note_meta_event({"type": "speechStart", "turnId": "tgrace"})
            bridge._note_meta_event({"type": "transcript", "turnId": "tgrace",
                                     "transcript": "el ciclo del agua produce lluvia intensa hoy",
                                     "final": False})
            await bridge.on_audio_frame(_loud_frame())
            assert spawn.await_count == 0
            assert bridge.window_grace_until > 0
            # Simula gracia vencida: el proximo frame emite.
            import asyncio as _aio

            bridge.window_grace_until = _aio.get_event_loop().time() - 1
            await bridge.on_audio_frame(_loud_frame())
            assert spawn.await_count == 1
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_speech_complete_after_windows_emits_tail_only():
    """speechComplete tras ventanas -> solo la cola va al LLM, sin duplicar."""

    async def scenario():
        bridge, front = _make_bridge_words()
        bridge.streaming = True
        bridge.upstream = object()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        first = "el ciclo del agua produce lluvia intensa."
        second = first + " y genera rios caudalosos en la montana"
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "jev:new", "raw": {}}),
            patch.object(llm_mod, "generate_slide",
                         return_value=fake_slide) as gen,
        ):
            bridge._note_meta_event({"type": "speechStart", "turnId": "ttail"})
            bridge._note_meta_event({"type": "transcript", "turnId": "ttail",
                                     "transcript": first, "final": False})
            await bridge.on_audio_frame(_loud_frame())
            await _drain_bridge(bridge)
            assert gen.call_count == 1
            bridge._note_meta_event({"type": "speechComplete", "turnId": "ttail",
                                     "transcript": second})
            await bridge.handle_speech_complete({"type": "speechComplete",
                                                 "turnId": "ttail",
                                                 "transcript": second})
            await _drain_bridge(bridge)
        # Ventana (delta = texto completo) + cola (solo lo nuevo).
        assert gen.call_count == 2
        assert gen.call_args_list[0][0][0] == first
        assert gen.call_args_list[1][0][0] == "y genera rios caudalosos en la montana"
        assert "ttail" not in bridge.last_forced_text
        assert "ttail" not in bridge.partial_by_turn
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_speech_complete_after_windows_empty_tail_filtered():
    """speechComplete sin texto nuevo tras ventanas -> slide_filtered, sin LLM."""

    async def scenario():
        bridge, front = _make_bridge_words()
        bridge.streaming = True
        bridge.upstream = object()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        text = "el ciclo del agua produce lluvia intensa."
        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False}
        with (
            patch.object(jev_mod, "decide_slide_action",
                         return_value={"relevant": True, "action": "new",
                                       "reason": "jev:new", "raw": {}}),
            patch.object(llm_mod, "generate_slide",
                         return_value=fake_slide) as gen,
        ):
            bridge._note_meta_event({"type": "speechStart", "turnId": "tnotail"})
            bridge._note_meta_event({"type": "transcript", "turnId": "tnotail",
                                     "transcript": text, "final": False})
            await bridge.on_audio_frame(_loud_frame())
            await _drain_bridge(bridge)
            assert gen.call_count == 1
            bridge._note_meta_event({"type": "speechComplete", "turnId": "tnotail",
                                     "transcript": text})
            await bridge.handle_speech_complete({"type": "speechComplete",
                                                 "turnId": "tnotail",
                                                 "transcript": text})
            await asyncio.sleep(0.05)
        assert gen.call_count == 1
        filtered = [m for m in front.sent if m.get("type") == "slide_filtered"]
        assert len(filtered) == 1
        assert filtered[0]["turnId"] == "tnotail"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


# --- Imágenes generativas progresivas (vivo efímero, sin R2) ---

def _img_response(url: str = "https://img.example.com/a.webp") -> FakeResponse:
    return FakeResponse(200, {"data": [{"url": url}]})


def test_generate_image_apagada_sin_request(monkeypatch):
    """Flag off -> None sin tocar la red."""
    import httpx as _httpx

    from backend.presentation_api.utils import image_generation as img_mod

    monkeypatch.delenv("ENABLE_IMAGE_GENERATION", raising=False)
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    with patch.object(_httpx.AsyncClient, "post", new=AsyncMock()) as mock_post:
        assert asyncio.run(img_mod.generate_image("a cat")) is None
        assert mock_post.await_count == 0


def test_generate_image_sin_key_o_prompt_vacio(monkeypatch):
    """Sin key o con prompt vacío -> None sin request."""
    import httpx as _httpx

    from backend.presentation_api.utils import image_generation as img_mod

    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with patch.object(_httpx.AsyncClient, "post", new=AsyncMock()) as mock_post:
        assert asyncio.run(img_mod.generate_image("a cat")) is None
        assert mock_post.await_count == 0
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    with patch.object(_httpx.AsyncClient, "post", new=AsyncMock()) as mock_post:
        assert asyncio.run(img_mod.generate_image("   ")) is None
        assert mock_post.await_count == 0


def test_generate_image_payload_rapido_y_url(monkeypatch):
    """Payload veloz (low/url/webp, 1 intento) y devuelve la URL https."""
    import httpx as _httpx

    from backend.presentation_api.utils import image_generation as img_mod

    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    mock_post = AsyncMock(return_value=_img_response())
    with patch.object(_httpx.AsyncClient, "post", mock_post):
        url = asyncio.run(img_mod.generate_image("a red bicycle"))
    assert url == "https://img.example.com/a.webp"
    _, kwargs = mock_post.call_args
    body = kwargs["json"]
    assert kwargs.get("headers", {}).get("Authorization") == "Bearer LLM_test"
    assert "api.meta.ai/v1/images/generations" in mock_post.call_args[0][0]
    assert body["model"] == "muse-image-1.0"
    assert body["n"] == 1
    assert body["response_format"] == "url"
    assert body["reasoning_strength"] == "low"
    assert body.get("stream") is False


def test_generate_image_timeout_y_b64_a_none(monkeypatch):
    """Timeout o respuesta b64 (fase vivo-url-only) -> None, nunca lanza."""
    import httpx as _httpx

    from backend.presentation_api.utils import image_generation as img_mod

    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")

    def _boom(*args, **kwargs):
        raise _httpx.TimeoutException("slow")

    with patch.object(_httpx.AsyncClient, "post", side_effect=_boom):
        assert asyncio.run(img_mod.generate_image("a cat")) is None
    b64 = FakeResponse(200, {"data": [{"b64_json": "AAAA"}]})
    with patch.object(_httpx.AsyncClient, "post", new=AsyncMock(return_value=b64)):
        assert asyncio.run(img_mod.generate_image("a cat")) is None
    err = FakeResponse(400, {"error": "bad"}, text='{"error":"bad"}')
    with patch.object(_httpx.AsyncClient, "post", new=AsyncMock(return_value=err)):
        assert asyncio.run(img_mod.generate_image("a cat")) is None


def test_generate_image_cache_no_regenera(monkeypatch):
    """Mismo prompt normalizado -> segunda llamada sale del cache LRU."""
    import httpx as _httpx

    from backend.presentation_api.utils import image_generation as img_mod

    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")
    monkeypatch.setenv("MODEL_API_KEY", "LLM_test")
    img_mod._cache.clear()
    mock_post = AsyncMock(return_value=_img_response())
    with patch.object(_httpx.AsyncClient, "post", mock_post):
        first = asyncio.run(img_mod.generate_image("  A Red Bicycle "))
        second = asyncio.run(img_mod.generate_image("a red bicycle"))
    assert first == second == "https://img.example.com/a.webp"
    assert mock_post.await_count == 1


def test_ws_slide_progresivo_luego_image_updated():
    """Slide de texto inmediato + slide_image_updated después, mismo seq."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import image_generation as img_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        fake_slide = {"layout": "split_media", "title": "Bici", "text": "una bici roja",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False,
                      "imagen_prompt": "a red bicycle on a hill", "imagen_hashtag": "bicycle"}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch.object(img_mod, "generate_image",
                         new=AsyncMock(return_value="https://img.example.com/a.webp")),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-img"))
            for task in list(bridge.pending_tasks.values()):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
            for task in list(bridge.image_tasks):
                try:
                    await asyncio.wait_for(task, timeout=2)
                except Exception:
                    pass
        slides = [m for m in front.sent if m.get("type") == "slide"]
        updates = [m for m in front.sent if m.get("type") == "slide_image_updated"]
        assert len(slides) == 1
        assert slides[0]["turnId"] == "t-img"
        assert slides[0]["imagen_prompt"] == "a red bicycle on a hill"
        assert len(updates) == 1
        assert updates[0]["turnId"] == "t-img"
        assert updates[0]["seq"] == slides[0]["seq"]
        assert updates[0]["topicVersion"] == slides[0]["topicVersion"]
        assert updates[0]["image"] == "https://img.example.com/a.webp"
        # El texto salió antes que la imagen (progresivo, no bloqueante).
        kinds = [m["type"] for m in front.sent
                 if m.get("type") in ("slide", "slide_image_updated")]
        assert kinds == ["slide", "slide_image_updated"]
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_ws_image_stale_no_emite_update():
    """Si la versión cambió antes de terminar la imagen, no se emite patch."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import image_generation as img_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        started = asyncio.Event()

        async def slow_image(prompt: str):
            started.set()
            await asyncio.sleep(0.5)
            return "https://img.example.com/a.webp"

        fake_slide = {"layout": "split_media", "title": "Bici", "text": "una bici roja",
                      "bullets": [], "keywords": [], "relevant": True, "filtered": False,
                      "imagen_prompt": "a red bicycle on a hill"}
        with (
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
            patch.object(img_mod, "generate_image", side_effect=slow_image),
            patch("backend.realtime_proxy.is_relevant", return_value=True),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-stale-img"))
            assert await asyncio.wait_for(started.wait(), timeout=2)
            bridge.confirm_topic_version(bridge.current_topic_version + 1)
            await asyncio.sleep(0.8)
        updates = [m for m in front.sent if m.get("type") == "slide_image_updated"]
        assert updates == []
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


# --- Slice 1: gate keep/update/new + live sessions store + resume REST ---

def _jev_answers(choice: str, conf: float, on_p: float = 0.95) -> dict:
    probs = {"keep": 0.05, "update": 0.05, "new": 0.05}
    probs[choice] = conf
    return {"answers": {
        "on_topic": {"type": "noul", "noul": on_p},
        "slide_action": {"type": "choice", "choice": choice,
                         "confidence": conf, "probabilities": probs},
    }}


def test_jev_parse_invalid_append_choice_fail_open():
    """Choice append (removed action) -> fail-open with the true reason."""
    from backend.presentation_api.utils import jev_client as jev_mod

    assert "append" not in jev_mod.SLIDE_ACTION_QUESTION
    assert "append" not in jev_mod._VALID_ACTIONS
    parsed = jev_mod.parse_decision_payload(_jev_answers("append", 0.9))
    assert parsed["action"] == "new"
    assert parsed["reason"] == "fail-open: invalid-choice"
    parsed_base = jev_mod.parse_decision_payload(
        _jev_answers("append", 0.9), has_current_slide=True)
    assert parsed_base["action"] == "keep"
    assert parsed_base["reason"] == "fail-open: invalid-choice"


def test_jev_new_threshold_downgrade():
    """Weak new (<0.80, >=0.65): keep with base, new without."""
    from backend.presentation_api.utils import jev_client as jev_mod

    weak_new = _jev_answers("new", 0.70)
    assert jev_mod.parse_decision_payload(weak_new)["action"] == "new"
    downgraded = jev_mod.parse_decision_payload(
        weak_new, has_current_slide=True)
    assert downgraded["action"] == "keep"
    assert downgraded["reason"] == "jev:keep-downgraded"
    strong = jev_mod.parse_decision_payload(
        _jev_answers("new", 0.90), has_current_slide=True)
    assert strong["action"] == "new"


def test_jev_fail_open_with_without_slide():
    """Fail-open conservador: sin slide -> new, con slide -> keep."""
    from backend.presentation_api.utils import jev_client as jev_mod

    assert jev_mod.parse_decision_payload(None,
                                          has_current_slide=True)["action"] == "keep"
    assert jev_mod.parse_decision_payload(
        {"answers": {"slide_action": {"choice": "borrar"}}},
        has_current_slide=True)["action"] == "keep"
    low = {"answers": {"on_topic": {"probability": 0.9},
                       "slide_action": {"choice": "keep", "confidence": 0.1}}}
    assert jev_mod.parse_decision_payload(low,
                                          has_current_slide=True)["action"] == "keep"
    assert jev_mod.parse_decision_payload(low)["action"] == "new"
    # decide_slide_action sin key: mapea segun haya slide base o no.
    assert jev_mod.decide_slide_action("t", [], "general", "x", None)["action"] == "new"
    base = {"titulo": "T", "resumen": "r", "layout": "title_text"}
    assert jev_mod.decide_slide_action("t", [], "general", "x", base)["action"] == "keep"


def test_jev_payload_rich_slide_actual_and_history_cap():
    """Payload con slide_actual rico + historial capado a 8."""
    from backend.presentation_api.utils import jev_client as jev_mod

    history = [{"titulo": f"T{i}", "layout": "title_text",
                "resumen": f"r{i}", "keywords": ["k"]} for i in range(10)]
    payload = jev_mod.build_payload(
        "tema", ["k"], "general", "turno",
        {"layout": "bullets_flex", "titulo": "T", "resumen": "r",
         "segundos_desde_creacion": 30, "turnos_desde_creacion": 3},
        historial_reciente=history,
    )
    actual = payload["state"]["slide_actual"]
    assert actual["layout"] == "bullets_flex"
    assert "capacidad_restante" not in actual
    assert "elementos_actuales" not in actual
    assert actual["segundos_desde_creacion"] == 30
    assert actual["turnos_desde_creacion"] == 3
    assert len(payload["state"]["historial_reciente"]) == 8
    assert payload["state"]["historial_reciente"][0]["titulo"] == "T2"


def test_live_sessions_ttl_seq_and_update():
    """Store: 2h TTL, stale seq rejected, update replaces without history."""
    from backend.presentation_api.utils import live_sessions as live

    entry = live.get_or_create("u-store-1", "s-store-1")
    slide = {"layout": "bullets_flex", "title": "T", "titulo": "T",
             "text": "x", "texto": "x", "bullets": ["alpha"],
             "cards": [], "steps": [], "chips": [], "stats": [],
             "keywords": []}
    assert live.record_new(entry, slide, 1, "t1-1") is True
    assert live.record_new(entry, slide, 1, "t1-1") is False  # stale seq
    updated = dict(slide, title="T2", titulo="T2")
    assert live.record_update(entry, updated, 1, "t1-1") is False  # stale seq
    assert live.record_update(entry, updated, 2, "t1-1") is True
    assert entry["current_slide"]["title"] == "T2"
    assert len(entry["history"]) == 0  # update no archiva
    # TTL: entrada vieja se lee como ausente.
    entry["updated_at"] = live._now() - live.SESSION_TTL_S - 1
    assert live.get("u-store-1", "s-store-1") is None
    live.discard("u-store-1", "s-store-1")


def test_live_sessions_history_max_and_version_reset():
    """Historial max 8; cambio de topicVersion archiva y limpia base."""
    from backend.presentation_api.utils import live_sessions as live

    entry = live.get_or_create("u-store-2", "s-store-2")
    for i in range(10):
        live.record_new(entry, {"layout": "title_text", "title": f"T{i}",
                                "titulo": f"T{i}", "text": "x", "texto": "x",
                                "keywords": []}, i + 1, f"t{i}-{i + 1}")
    assert len(entry["history"]) == 8
    assert entry["history"][0]["titulo"] == "T1"
    live.reset_for_topic_version(entry, 2, "nuevo tema")
    assert entry["current_slide"] is None
    assert entry["topic_version"] == 2
    assert entry["topic"] == "nuevo tema"
    assert len(entry["history"]) == 8  # T9 archivado, T0 fuera
    slide_actual, historial = live.build_jev_context(entry)
    assert slide_actual == {} and len(historial) == 8
    assert len(entry["jev_context_cache"]) <= 2500
    live.discard("u-store-2", "s-store-2")


def test_ws_update_carries_replaces_id():
    """Update con base -> slide_replaced con el id real del slide previo."""

    async def scenario():
        bridge, front = _make_bridge()
        from backend.presentation_api.utils import jev_client as jev_mod
        from backend.presentation_api.utils import llm_client as llm_mod

        fake_slide = {"layout": "title_text", "title": "T", "text": "x",
                      "bullets": [], "keywords": [],
                      "relevant": True, "filtered": False}
        decisions = [
            {"relevant": True, "action": "new", "reason": "jev:new", "raw": {}},
            {"relevant": True, "action": "update", "reason": "jev:update", "raw": {}},
        ]
        with (
            patch.object(jev_mod, "decide_slide_action", side_effect=decisions),
            patch.object(llm_mod, "generate_slide", return_value=fake_slide),
        ):
            await bridge.handle_speech_complete(_speech_complete("t-u1"))
            await _drain_bridge(bridge)
            await bridge.handle_speech_complete(_speech_complete("t-u2"))
            await _drain_bridge(bridge)
        replaced = [m for m in front.sent if m.get("type") == "slide_replaced"]
        assert len(replaced) == 1
        assert replaced[0]["turnId"] == "t-u2"
        assert replaced[0]["replaces"] == "t-u1"
        assert replaced[0]["targetSlideId"] == "t-u1-1"
        await bridge.cancel_slide_tasks()

    asyncio.run(scenario())


def test_rest_live_session_resume_and_discard():
    """GET resume check + DELETE descarte para el usuario actual."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    entry = live.get_or_create("dev-local")
    live.record_new(entry, {"layout": "title_text", "title": "T", "titulo": "T",
                            "text": "x", "texto": "x", "keywords": []},
                    entry["last_recorded_seq"] + 1,
                    f"seed-{entry['last_recorded_seq'] + 1}")
    sid = entry["live_session_id"]
    client = TestClient(app_mod)
    r = client.get("/api/presentations/live-session")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_saved"] is True
    assert body["live_session_id"] == sid
    assert body["slide_count"] >= 1
    assert body["updated_at"]
    d = client.delete(f"/api/presentations/live-session/{sid}")
    assert d.status_code == 200 and d.json()["discarded"] is True
    d2 = client.delete(f"/api/presentations/live-session/{sid}")
    assert d2.json()["discarded"] is False


def _slides_test_slide(title: str, layout: str = "title_text", **extra) -> dict:
    base = {"layout": layout, "title": title, "titulo": title,
            "text": f"text-{title}", "texto": f"text-{title}",
            "bullets": [f"b-{title}"], "keywords": ["k"],
            "cards": [], "steps": [], "chips": [], "stats": []}
    base.update(extra)
    return base


def _override_user(app_mod, user_id: str):
    from backend.presentation_api.utils.auth import require_auth

    async def _ov():
        return {"user_id": user_id, "created_at": None}

    app_mod.dependency_overrides[require_auth] = _ov


def test_live_session_slides_order_and_meta_consistent():
    """Slides endpoint returns paint-ordered full slides; meta count matches."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    user = "u-slides-order"
    sid = "sess-order-1"
    live.discard(user, sid)
    entry = live.get_or_create(user, sid)
    entry["topic"] = "clima"
    for i, title in enumerate(["Intro", "Causas", "Efectos"], start=1):
        assert live.record_new(entry, _slides_test_slide(title), i, f"turn{i}-{i}") is True
    _override_user(app_mod, user)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["live_session_id"] == sid
        assert body["topic"] == "clima"
        assert body["updated_at"]
        slides = body["slides"]
        assert len(slides) == 3
        assert [s["title"] for s in slides] == ["Intro", "Causas", "Efectos"]
        assert [s["seq"] for s in slides] == [1, 2, 3]
        assert [s["id"] for s in slides] == ["turn1-1", "turn2-2", "turn3-3"]
        for s in slides:
            for key in ("layout", "title", "text", "bullets", "cards",
                        "steps", "chips", "stats", "code", "image",
                        "html", "palette", "topicVersion"):
                assert key in s, f"missing {key} in {s.get('id')}"
            assert isinstance(s["html"], str) and s["html"]
            assert s["topicVersion"] >= 1
        assert "user_id" not in body
        m = client.get("/api/presentations/live-session")
        assert m.status_code == 200, m.text
        assert m.json()["slide_count"] == len(slides) == 3
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(user, sid)


def test_live_session_slides_ownership():
    """User A cannot read user B session (404, no leakage)."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    owner, other, sid = "u-owner-a", "u-other-b", "sess-owner-1"
    live.discard(owner, sid)
    live.discard(other, sid)
    entry = live.get_or_create(owner, sid)
    assert live.record_new(entry, _slides_test_slide("Secret"), 1, "t-1") is True
    _override_user(app_mod, other)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 404, r.text
        assert "user" not in r.text.lower() or "user_id" not in r.json().get("detail", "")
    finally:
        app_mod.dependency_overrides.clear()
    _override_user(app_mod, owner)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 200, r.text
        assert len(r.json()["slides"]) == 1
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(owner, sid)
        live.discard(other, sid)


def test_live_session_slides_404_unknown_and_expired():
    """Unknown id and expired entry both read as 404."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    user, sid = "u-slides-404", "sess-404-1"
    live.discard(user, sid)
    _override_user(app_mod, user)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 404, r.text
        entry = live.get_or_create(user, sid)
        assert live.record_new(entry, _slides_test_slide("T"), 1, "t-1") is True
        entry["updated_at"] = live._now() - live.SESSION_TTL_S - 1
        r2 = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r2.status_code == 404, r2.text
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(user, sid)


def test_live_session_slides_update_reflected():
    """Update replaces content in place; order and id kept."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    user, sid = "u-slides-mut", "sess-mut-1"
    live.discard(user, sid)
    entry = live.get_or_create(user, sid)
    assert live.record_new(entry, _slides_test_slide("Base"), 1, "base-1") is True
    _override_user(app_mod, user)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 200, r.text
        slides = r.json()["slides"]
        assert len(slides) == 1
        assert slides[0]["id"] == "base-1"
        updated = dict(slides[0])
        updated.update({"title": "Base v2", "titulo": "Base v2",
                        "text": "nuevo", "texto": "nuevo"})
        stored = {k: v for k, v in updated.items()
                  if k not in ("id", "seq", "topicVersion", "html",
                               "palette", "palette_id", "audience")}
        assert live.record_update(entry, stored, 2, "base-1") is True
        r2 = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r2.status_code == 200, r2.text
        slides2 = r2.json()["slides"]
        assert len(slides2) == 1
        assert slides2[0]["title"] == "Base v2"
        assert slides2[0]["id"] == "base-1"
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(user, sid)


def test_display_scale_clamp_and_invalid_keeps_previous():
    """set_display_scale clamps to 0.8-1.3; invalid input keeps previous."""
    from backend.presentation_api.utils import live_sessions as live

    user, sid = "u-scale-clamp", "sess-scale-1"
    live.discard(user, sid)
    entry = live.get_or_create(user, sid)
    try:
        assert live.get_display_scale(entry) == 1.0
        assert live.set_display_scale(entry, 1.2) is True
        assert live.get_display_scale(entry) == 1.2
        assert live.set_display_scale(entry, 2.0) is True
        assert live.get_display_scale(entry) == 1.3
        assert live.set_display_scale(entry, 0.2) is True
        assert live.get_display_scale(entry) == 0.8
        assert live.set_display_scale(entry, "oops") is False
        assert live.set_display_scale(entry, None) is False
        assert live.set_display_scale(entry, float("nan")) is False
        assert live.get_display_scale(entry) == 0.8
        assert live.clamp_display_scale("1.1") == 1.1
        assert live.clamp_display_scale(object()) is None
    finally:
        live.discard(user, sid)


def test_rest_live_session_display_scale_exposed():
    """Meta + slides endpoints expose the stored displayScale (default 1.0)."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    user, sid = "u-scale-rest", "sess-scale-2"
    live.discard(user, sid)
    entry = live.get_or_create(user, sid)
    assert live.record_new(entry, _slides_test_slide("T"), 1, "t-1") is True
    _override_user(app_mod, user)
    try:
        client = TestClient(app_mod)
        m = client.get("/api/presentations/live-session")
        assert m.status_code == 200, m.text
        assert m.json()["displayScale"] == 1.0
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 200, r.text
        assert r.json()["displayScale"] == 1.0
        assert live.set_display_scale(entry, 1.3) is True
        m2 = client.get("/api/presentations/live-session")
        assert m2.json()["displayScale"] == 1.3
        r2 = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r2.json()["displayScale"] == 1.3
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(user, sid)


def test_live_session_display_scale_ownership():
    """Scale is per (user, session): other users get 404, never the value."""
    from fastapi.testclient import TestClient

    from backend.presentation_api import app as app_mod
    from backend.presentation_api.utils import live_sessions as live

    owner, other, sid = "u-scale-own", "u-scale-oth", "sess-scale-3"
    live.discard(owner, sid)
    live.discard(other, sid)
    entry = live.get_or_create(owner, sid)
    assert live.record_new(entry, _slides_test_slide("Secret"), 1, "t-1") is True
    assert live.set_display_scale(entry, 0.9) is True
    _override_user(app_mod, other)
    try:
        client = TestClient(app_mod)
        r = client.get(f"/api/presentations/live-session/{sid}/slides")
        assert r.status_code == 404, r.text
        assert "0.9" not in r.text
        m = client.get("/api/presentations/live-session")
        assert m.status_code == 200, m.text
        assert m.json()["has_saved"] is False
    finally:
        app_mod.dependency_overrides.clear()
        live.discard(owner, sid)
        live.discard(other, sid)
