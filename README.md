# Live Presentation — transcripción en vivo + slides con IA

Transcripción en tiempo real y generación de slides en formato JSON mediante un modelo de lenguaje (LLM).

## Arquitectura

- **Realtime WS `/ws/transcribe`:** el frontend envía PCM a 24 kHz y el backend lo reenvía a Meta. `enrich_event` agrega `topic`, `keywords` y `cleaned` a cada evento.
- **Fallback `POST /api/transcribe`:** recibe audio en `multipart/form-data`, lo convierte con ffmpeg a WAV mono de 16-bit a 24 kHz. Límite de 32 MB por archivo.
- **Generación de slides `POST /api/presentations/generate`:** recibe `{transcript, topic, keywords}` y devuelve `{layout, title, text, bullets, keywords, filtered}`.
- **Frontend:** `App.vue` actúa como shell con `AppSidebar` (controles) y `SlideCanvas` (componentes en `slides/`). Los composables `useRealtimeTranscription` y `useLivePresentation` gestionan la conexión realtime con debounce de 4 s y deduplicación por `turnId`.

La clave `MODEL_API_KEY` solo existe en el backend. El frontend nunca la utiliza.

Motor: `muse-voice-transcribe-1.0`, endpoint `POST https://api.meta.ai/v1/asr/transcribe`.
Modo `PUSH_TO_TALK`, sesgo de idioma español, sin diarización.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| WS | `/ws/transcribe` | Transcripción en tiempo real (PCM 24 kHz, eventos enriquecidos) |
| POST | `/api/transcribe` | Transcripción de archivo (`multipart/form-data`, máx. 32 MB) |
| POST | `/api/presentations/generate` | Generación de slide desde `{transcript, topic, keywords}` |

## Requisitos

- Python 3.10+
- Node.js 18+ y npm
- ffmpeg (obligatorio para convertir el audio del navegador a WAV 24 kHz):
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
- Una API key de Meta con formato `LLM_...`

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest
cp .env.example .env
# Editar .env y colocar la key real en MODEL_API_KEY
```

Frontend:

```bash
cd frontend
cp .env.example .env
# Editar .env y ajustar VITE_API_BASE_URL si el backend no corre en http://localhost:8000
npm install
```

## Cómo correrlo

Terminal 1 (backend):

```bash
source .venv/bin/activate
uvicorn backend.presentation_api:app --port 8000
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

Abrir el navegador en http://localhost:5173, grabar la voz y presionar **Transcribir**.

> Nota: el micrófono requiere servir la app en `localhost` o bajo HTTPS.
> Safari no soporta `audio/webm`; en ese caso el frontend graba en MP4
> (`audio/mp4`) y el backend lo convierte igual con ffmpeg.

## Cómo conseguir la key

1. Entrar al portal de desarrolladores de Meta y crear un proyecto con acceso a Muse Voice.
2. Generar una API key (empieza con `LLM_...`).
3. Copiarla en `.env` como `MODEL_API_KEY=LLM_...`. Nunca incluirla en el frontend.

## Límites y costo

- Tamaño máximo por archivo: **32 MB** (el backend responde 413 si se supera).
- Duración máxima aproximada: **10 minutos** por pedido.
- Costo de referencia: **$0.18 por hora** de audio transcrito.
- Formato requerido por Meta: **WAV**. El navegador suele enviar otro formato,
  por eso el backend lo convierte automáticamente con ffmpeg.

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| MODEL_API_KEY | (vacía) | Key `LLM_...`, solo backend. Nunca exponer en el frontend |
| OPENROUTER_API_KEY | (vacía) | Key de OpenRouter para el gate Jev, solo backend. Nunca usar `VITE_*` |
| JEV_MODEL | typesafe/jev-1.13 | Modelo del gate de decisiones (endpoint Decisions, no chat) |
| JEV_TOPIC_P | 0.6 | Umbral de probabilidad on-topic para considerar relevante |
| JEV_ACTION_CONF | 0.65 | Confianza mínima de slide_action; debajo hay fail-open |
| JEV_TIMEOUT_MS | 2500 | Timeout del gate Jev; en error/timeout hay fail-open al flujo actual |
| SLIDE_WINDOW_S | 10 | Ventana de voz acumulada (VAD-time) que fuerza evaluación sin speechComplete; 0 = off |
| WINDOW_DUTY_CYCLE | (vacío) | Ciclo de trabajo de la ventana, ej. `10/30`; vacío = siempre activa |
| SLIDE_CONTEXT_CHARS | 600 | Cola de caracteres de transcripts para fusión en update |
| META_ASR_URL | https://api.meta.ai/v1/asr/transcribe | Endpoint de Meta |
| ASR_MODEL | muse-voice-transcribe-1.0 | Modelo de transcripción |
| VITE_API_BASE_URL | http://localhost:8000 | URL del backend (frontend, archivo `frontend/.env`) |

## Tests

```bash
source .venv/bin/activate
pytest backend/test_main.py -v
```

Build del frontend:

```bash
cd frontend
npm run build
```
