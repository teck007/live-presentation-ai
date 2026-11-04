> Built for the Meta Hackathon 2026.

# Live Presentation — Speak. Your slides appear.

Live Presentation lets anyone present any topic without preparing a deck beforehand. Just outline what you want to talk about, set your topic and audience, and start speaking. The platform listens in real time, understands what's relevant, and generates your slides and supporting images as you talk — so you can focus on presenting, not on designing slides.

## Main flow (`/live`)

1. Open `/live` and sign in (24 h trial from first use).
2. Set your **topic** (e.g. Photosynthesis) and **audience** (kids / students / general / professionals / experts).
3. Press **Go live**: the `hero_cover` cover (seq 0) is generated without blocking the mic.
4. Speak: partial subtitles appear live and slides paint themselves as relevant content arrives.
5. Off-topic content is filtered out without painting. Generative images arrive progressively, without blocking the text.
6. Batch fallback: if there is no mic, record audio and press **Transcribe**.

## Architecture

- **Single-producer WS `/ws/transcribe`**: the frontend sends 24 kHz PCM; the backend forwards it to Meta realtime and emits enriched events (`topic`, `keywords`, `cleaned`) plus `slide_*` events. Dedupe by `turnId`, ordering by `seq`, stale discard by `topicVersion`.
- **POST `/api/transcribe` fallback**: `multipart/form-data` (max 32 MB), conversion with ffmpeg to mono 16-bit 24 kHz WAV. Single-producer rule: if the WS claims the `turnId`, the POST does not compete.
- **Fail-open Jev gate**: each voice window is evaluated with the decision model (`typesafe/jev-1.13` via OpenRouter). If the gate fails or times out (`JEV_TIMEOUT_MS`), the flow continues without blocking.
- **Evaluation windows**: accumulated voice window (`SLIDE_WINDOW_S`), word target and configurable voice/content limits; fusion with transcript context (`SLIDE_CONTEXT_CHARS`).
- **Slides**: 21 layouts over 13 Vue components (`slideLayouts.ts`, `frontend/src/types.ts`); server-side design in `slide_designs.py` + component route in `SlideCanvas`. Bounded concurrency: 2 slides / 3 images in parallel.
- **In-memory sessions**: 2 h TTL with resume (Continue / New). Thread blocking avoided with `asyncio.to_thread` for LLM, Jev, ffmpeg, Clerk auth (including the WS handler) and Resend.
- **Auth + trial**: Clerk (JWT per request) and trial persisted in local JSON. No secrets in `VITE_*`: `MODEL_API_KEY` and other keys only exist in the backend.

## Frontend routes

| Route | Description |
|---|---|
| `/` | Public landing |
| `/live` | Live studio (requires login + active trial; opens in dev without Clerk configured) |
| `/sign-in` | Sign in (Clerk) |
| `/sign-up` | Sign up (Clerk) |
| `/trial-expired` | Trial end (no guard, avoids loops) |

Shell: `App.vue` is `router-view` + persistent navbar. Light/dark theme (OS default + persistence) and ES/EN i18n.

## Endpoints

| Method | Route | Description |
|---|---|---|
| WS | `/ws/transcribe` | Realtime transcription + `slide_*` events (requires JWT when auth is on) |
| POST | `/api/transcribe` | File transcription (`multipart/form-data`, max 32 MB) |
| POST | `/api/presentations/generate` | Generates one slide from `{transcript, topic, keywords}` |
| GET | `/api/presentations/live-session` | Saved session state (resume) |
| GET | `/api/presentations/live-session/{id}/slides` | Slide snapshot for resume |
| DELETE | `/api/presentations/live-session/{id}` | Discards the saved session |
| GET | `/api/presentations/layouts` | Catalog of the 21 layouts |
| GET | `/api/trial/status` | Trial status (requires JWT) |
| POST | `/api/contact` | Contact form (Resend) |
| GET | `/health`, `/api/presentations/health`, `/api/credits/health`, `/api/contact/health` | Health checks |

## Requirements

- Python 3.10+, Node.js 18+, ffmpeg (required to convert audio to 24 kHz WAV):
  - macOS: `brew install ffmpeg` · Ubuntu/Debian: `sudo apt install ffmpeg`
- Keys: Meta Muse (`MODEL_API_KEY`, `LLM_...` format), OpenRouter (`OPENROUTER_API_KEY`, Jev gate), Clerk (backend + frontend), Resend (contact, optional in dev).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest
cp .env.example .env   # fill in MODEL_API_KEY and other keys
```

```bash
cd frontend
cp .env.example .env   # adjust VITE_API_BASE_URL if needed
npm install
```

## Running locally

```bash
# Terminal 1 (backend, from the repo root)
source .venv/bin/activate
uvicorn backend.presentation_api:app --port 8000

# Terminal 2 (frontend)
cd frontend && npm run dev
# Open http://localhost:5173/live
```

> The mic requires `localhost` or HTTPS. Safari does not support `audio/webm`: the frontend records `audio/mp4` instead and the backend still converts it with ffmpeg.

## Getting the keys

1. **Meta Muse**: Meta developer portal → project with Muse Voice access → `LLM_...` key → `MODEL_API_KEY`.
2. **OpenRouter**: OpenRouter account → API key → `OPENROUTER_API_KEY` (Jev gate, Decisions endpoint).
3. **Clerk**: Clerk application → `CLERK_SECRET_KEY` (backend) + `VITE_CLERK_PUBLISHABLE_KEY` (frontend).
4. **Resend** (optional in dev): API key → `RESEND_API_KEY` + `CONTACT_TO` / `CONTACT_FROM`.

## Environment variables

| Variable | Scope | Default |
|---|---|---|
| `MODEL_API_KEY` | Backend | (empty, `LLM_...` format) |
| `META_ASR_URL` | Backend | `https://api.meta.ai/v1/asr/transcribe` |
| `META_REALTIME_URL` | Backend | `wss://api.meta.ai/v1/asr/realtime` |
| `ASR_MODEL` | Backend | `muse-voice-transcribe-1.0` |
| `OPENROUTER_API_KEY` | Backend | (empty) |
| `JEV_MODEL` | Backend | `typesafe/jev-1.13` |
| `JEV_TOPIC_P` | Backend | `0.6` |
| `JEV_ACTION_CONF` | Backend | `0.65` |
| `JEV_NEW_CONF` | Backend | `0.80` |
| `JEV_TIMEOUT_MS` | Backend | `4000` |
| `SLIDE_WINDOW_S` | Backend | `10` |
| `WINDOW_DUTY_CYCLE` | Backend | (empty = always on) |
| `WINDOW_TARGET_WORDS` | Backend | `18` |
| `WINDOW_MAX_VOICE_S` | Backend | `12.0` |
| `WINDOW_MIN_CONTENT_WORDS` | Backend | `5` |
| `WINDOW_GRACE_S` | Backend | `2.5` |
| `SLIDE_CONTEXT_CHARS` | Backend | `600` |
| `LLM_TIMEOUT_S` | Backend | `15` |
| `MAX_COMPLETION_TOKENS` | Backend | `1600` |
| `TRIAL_HOURS` | Backend | `24` |
| `TRIAL_STORE_PATH` | Backend | (empty = default local path) |
| `CLERK_SECRET_KEY` | Backend | (empty) |
| `RESEND_API_KEY` | Backend | (empty) |
| `CONTACT_TO` | Backend | `contacto@devstudio.cl` |
| `CONTACT_FROM` | Backend | `onboarding@resend.dev` |
| `ENABLE_IMAGE_GENERATION` | Backend | `false` |
| `MUSE_IMAGE_MODEL` | Backend | `muse-image-1.0` |
| `MUSE_IMAGE_SIZE` | Backend | `1536x1024` |
| `REALTIME_SILENCE_PAUSE_MS` | Backend | `15000` |
| `REALTIME_PRE_ROLL_MS` | Backend | `500` |
| `REALTIME_VAD_THRESHOLD` | Backend | `0.02` |
| `VITE_API_BASE_URL` | Frontend | `http://localhost:8000` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend | (empty) |
| `VITE_WS_SLIDES_ENABLED` | Frontend | (flag: WS as single slide producer) |

## Tests

```bash
source .venv/bin/activate
pytest backend/test_main.py backend/test_slide_designs.py backend/test_auth_trial_contact.py -v  # 125 passed
```

```bash
cd frontend && npm run build  # vue-tsc --noEmit + vite build, clean (191 modules)
```

## Limits and cost

- Max file **32 MB** (413 if exceeded); approx duration **10 min** per request.
- Reference transcription cost: **$0.18/hour** of audio. Format required by Meta: **WAV** (automatic conversion with ffmpeg).

## MVP limitations

- In-memory sessions with 2 h TTL: lost on restart; not multi-worker safe.
- Trial persisted in local JSON (no real database).
- CORS `*` (MVP only; restrict origins before production).
- `credits` is a stub; `database.py`, `web_search.py` and `image.py` are TODO.
- No PPT/PDF export.
