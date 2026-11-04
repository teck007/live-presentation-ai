# Presentaciones en vivo con transcripción e IA

Para el profesor que expone en clase y necesita apoyo visual sin diseñar slides.
Habla al micrófono y la aplicación transcribe en tiempo real, filtra lo irrelevante y genera slides acordes al tema automáticamente.

## Flujo principal (`/live`)

1. Abrir `/live` e iniciar sesión (trial de 24 h desde el primer uso).
2. Definir **tema** (ej. Fotosíntesis) y **audiencia** (niños / estudiantes / general / profesionales / expertos).
3. Pulsar **Iniciar en vivo**: se genera la portada `hero_cover` (seq 0) sin bloquear el micrófono.
4. Hablar: el subtítulo parcial aparece en vivo y los slides se pintan solos a medida que el contenido es relevante.
5. Lo fuera de tema se filtra sin pintar. Las imágenes generativas llegan de forma progresiva, sin bloquear el texto.
6. Fallback por lotes: si no hay micrófono, grabar audio y pulsar **Transcribir**.

## Arquitectura

- **WS productor único `/ws/transcribe`**: el frontend envía PCM 24 kHz; el backend lo reenvía a Meta realtime y emite eventos enriquecidos (`topic`, `keywords`, `cleaned`) más eventos `slide_*`. Dedupe por `turnId`, orden por `seq`, descarte stale por `topicVersion`.
- **Fallback POST `/api/transcribe`**: `multipart/form-data` (máx. 32 MB), conversión con ffmpeg a WAV mono 16-bit 24 kHz. Regla single-producer: si el WS reclama el `turnId`, el POST no compite.
- **Gate Jev fail-open**: cada ventana de voz se evalúa con el modelo de decisiones (`typesafe/jev-1.13` vía OpenRouter). Si el gate falla o expira (`JEV_TIMEOUT_MS`), el flujo continúa sin bloquear.
- **Ventanas de evaluación**: ventana de voz acumulada (`SLIDE_WINDOW_S`), objetivo de palabras y límites de voz/contenido configurables; fusión con contexto de transcripts (`SLIDE_CONTEXT_CHARS`).
- **Slides**: 21 layouts sobre 13 componentes Vue (`slideLayouts.ts`, `frontend/src/types.ts`); diseño de servidor en `slide_designs.py` + ruta de componentes en `SlideCanvas`. Concurrencia limitada: 2 slides / 3 imágenes en paralelo.
- **Sesiones en memoria**: TTL 2 h con reanudación (Continuar / Nueva). Bloqueo de hilo evitado con `asyncio.to_thread` para LLM, Jev, ffmpeg, auth Clerk (incluido handler WS) y Resend.
- **Auth + trial**: Clerk (JWT por request) y trial persistido en JSON local. Sin `VITE_*` con secretos: `MODEL_API_KEY` y demás keys solo existen en backend.

## Rutas frontend

| Ruta | Descripción |
|---|---|
| `/` | Landing pública |
| `/live` | Estudio en vivo (requiere login + trial activo; sin Clerk configurado abre en dev) |
| `/sign-in` | Inicio de sesión (Clerk) |
| `/sign-up` | Registro (Clerk) |
| `/trial-expired` | Fin del trial (sin guard, evita loops) |

Shell: `App.vue` es `router-view` + navbar persistente. Tema claro/oscuro (default del SO + persistencia) e i18n ES/EN.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| WS | `/ws/transcribe` | Transcripción realtime + eventos `slide_*` (requiere JWT si hay auth) |
| POST | `/api/transcribe` | Transcripción de archivo (`multipart/form-data`, máx. 32 MB) |
| POST | `/api/presentations/generate` | Genera un slide desde `{transcript, topic, keywords}` |
| GET | `/api/presentations/live-session` | Estado de sesión guardada (resume) |
| GET | `/api/presentations/live-session/{id}/slides` | Snapshot de slides para reanudar |
| DELETE | `/api/presentations/live-session/{id}` | Descarta la sesión guardada |
| GET | `/api/presentations/layouts` | Catálogo de los 21 layouts |
| GET | `/api/trial/status` | Estado del trial (requiere JWT) |
| POST | `/api/contact` | Formulario de contacto (Resend) |
| GET | `/health`, `/api/presentations/health`, `/api/credits/health`, `/api/contact/health` | Health checks |

## Requisitos

- Python 3.10+, Node.js 18+, ffmpeg (obligatorio para convertir audio a WAV 24 kHz):
  - macOS: `brew install ffmpeg` · Ubuntu/Debian: `sudo apt install ffmpeg`
- Keys: Meta Muse (`MODEL_API_KEY`, formato `LLM_...`), OpenRouter (`OPENROUTER_API_KEY`, gate Jev), Clerk (backend + frontend), Resend (contacto, opcional en dev).

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest
cp .env.example .env   # completar MODEL_API_KEY y demás keys
```

```bash
cd frontend
cp .env.example .env   # ajustar VITE_API_BASE_URL si aplica
npm install
```

## Cómo correrlo

```bash
# Terminal 1 (backend, desde la raíz)
source .venv/bin/activate
uvicorn backend.presentation_api:app --port 8000

# Terminal 2 (frontend)
cd frontend && npm run dev
# Abrir http://localhost:5173/live
```

> El micrófono requiere `localhost` o HTTPS. Safari no soporta `audio/webm`: el frontend graba en `audio/mp4` y el backend lo convierte igual con ffmpeg.

## Cómo conseguir las keys

1. **Meta Muse**: portal de desarrolladores de Meta → proyecto con acceso a Muse Voice → key `LLM_...` → `MODEL_API_KEY`.
2. **OpenRouter**: cuenta en OpenRouter → API key → `OPENROUTER_API_KEY` (gate Jev, endpoint Decisions).
3. **Clerk**: aplicación en Clerk → `CLERK_SECRET_KEY` (backend) + `VITE_CLERK_PUBLISHABLE_KEY` (frontend).
4. **Resend** (opcional en dev): API key → `RESEND_API_KEY` + `CONTACT_TO` / `CONTACT_FROM`.

## Variables de entorno

| Variable | Alcance | Default |
|---|---|---|
| `MODEL_API_KEY` | Backend | (vacía, formato `LLM_...`) |
| `META_ASR_URL` | Backend | `https://api.meta.ai/v1/asr/transcribe` |
| `META_REALTIME_URL` | Backend | `wss://api.meta.ai/v1/asr/realtime` |
| `ASR_MODEL` | Backend | `muse-voice-transcribe-1.0` |
| `OPENROUTER_API_KEY` | Backend | (vacía) |
| `JEV_MODEL` | Backend | `typesafe/jev-1.13` |
| `JEV_TOPIC_P` | Backend | `0.6` |
| `JEV_ACTION_CONF` | Backend | `0.65` |
| `JEV_NEW_CONF` | Backend | `0.80` |
| `JEV_TIMEOUT_MS` | Backend | `4000` |
| `SLIDE_WINDOW_S` | Backend | `10` |
| `WINDOW_DUTY_CYCLE` | Backend | (vacía = siempre activa) |
| `WINDOW_TARGET_WORDS` | Backend | `18` |
| `WINDOW_MAX_VOICE_S` | Backend | `12.0` |
| `WINDOW_MIN_CONTENT_WORDS` | Backend | `5` |
| `WINDOW_GRACE_S` | Backend | `2.5` |
| `SLIDE_CONTEXT_CHARS` | Backend | `600` |
| `LLM_TIMEOUT_S` | Backend | `15` |
| `MAX_COMPLETION_TOKENS` | Backend | `1600` |
| `TRIAL_HOURS` | Backend | `24` |
| `TRIAL_STORE_PATH` | Backend | (vacía = ruta local por defecto) |
| `CLERK_SECRET_KEY` | Backend | (vacía) |
| `RESEND_API_KEY` | Backend | (vacía) |
| `CONTACT_TO` | Backend | `contacto@devstudio.cl` |
| `CONTACT_FROM` | Backend | `onboarding@resend.dev` |
| `ENABLE_IMAGE_GENERATION` | Backend | `false` |
| `MUSE_IMAGE_MODEL` | Backend | `muse-image-1.0` |
| `MUSE_IMAGE_SIZE` | Backend | `1536x1024` |
| `REALTIME_SILENCE_PAUSE_MS` | Backend | `15000` |
| `REALTIME_PRE_ROLL_MS` | Backend | `500` |
| `REALTIME_VAD_THRESHOLD` | Backend | `0.02` |
| `VITE_API_BASE_URL` | Frontend | `http://localhost:8000` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend | (vacía) |
| `VITE_WS_SLIDES_ENABLED` | Frontend | (flag: WS como productor único de slides) |

## Tests

```bash
source .venv/bin/activate
pytest backend/test_main.py backend/test_slide_designs.py backend/test_auth_trial_contact.py -v  # 125 passed
```

```bash
cd frontend && npm run build  # vue-tsc --noEmit + vite build, limpio (191 módulos)
```

## Límites y costo

- Archivo máx. **32 MB** (413 si se supera); duración aprox. **10 min** por pedido.
- Costo de referencia transcripción: **$0.18/hora** de audio. Formato exigido por Meta: **WAV** (conversión automática con ffmpeg).

## Limitaciones MVP

- Sesiones en memoria con TTL 2 h: se pierden al reiniciar; no apto multi-worker.
- Trial persistido en JSON local (no base de datos real).
- CORS `*` (solo MVP; restringir orígenes antes de producción).
- `credits` es stub; `database.py`, `web_search.py` e `image.py` son TODO.
- Sin exportación a PPT/PDF.
