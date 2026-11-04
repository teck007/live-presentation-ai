# AGENTS.md

## Stack
- Backend: FastAPI app `backend.presentation_api:app` (routers: transcription, presentations with `/api` prefix, credits, contact).
- Ingesta principal: WS `/ws/transcribe` como productor principal de slides async, con gate de decisión Jev (fail-open), ventanas de evaluación y contexto de fusión.
- Slides: 21 layouts (registry `frontend/src/components/slides/slideLayouts.ts`, ids en `frontend/src/types.ts:23-44`) sobre 13 componentes Vue; paletas y catálogo en `backend/presentation_api/utils/slide_designs.py`; render HTML de servidor + ruta de componentes Vue en `SlideCanvas`; imágenes generativas progresivas solo para vivo efímero.
- Frontend: Vue 3 + Vite + TypeScript + Tailwind 4. Sin `vue-router` en dependencias al 2026-11-04: `App.vue` actúa como shell (no existen rutas `/` y `/live` con router en el código).
- Requirements: Python 3.10+, Node 18+, ffmpeg (required for audio conversion).

## Run
```bash
# Backend
source .venv/bin/activate
uvicorn backend.presentation_api:app --port 8000

# Frontend
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

## Env
| Variable | Default | Scope |
|---|---|---|
| `MODEL_API_KEY` | (empty, format `LLM_...`) | Backend only. Never expose in frontend. |
| `META_ASR_URL` | `https://api.meta.ai/v1/asr/transcribe` | Backend |
| `ASR_MODEL` | `muse-voice-transcribe-1.0` | Backend |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend (`frontend/.env`) |
| `OPENROUTER_API_KEY` | (empty) | Backend only. Gate Jev. Never expose in frontend. |
| `JEV_MODEL` | `typesafe/jev-1.13` | Backend |
| `JEV_TOPIC_P` | `0.6` | Backend |
| `JEV_ACTION_CONF` | `0.65` | Backend |
| `JEV_NEW_CONF` | `0.80` | Backend |
| `JEV_TIMEOUT_MS` | `4000` | Backend |
| `SLIDE_WINDOW_S` | `10` | Backend |
| `SLIDE_CONTEXT_CHARS` | `600` | Backend |
| `RESEND_API_KEY` | (empty, declarado; sin uso verificado en código al 2026-11-04) | Backend only. Never expose in frontend. |
| `CLERK_SECRET_KEY` | (empty, declarado; sin uso verificado en código al 2026-11-04) | Backend only. Never use `VITE_*` prefix. |
| `VITE_CLERK_PUBLISHABLE_KEY` | (empty, declarado; sin uso verificado en código al 2026-11-04) | Frontend (`frontend/.env`) |

## Conventions
- Conventional Commits in Spanish, one work unit per commit.
- LLM returns plain JSON with layout id (`SlideLayoutId`, 21 ids en `frontend/src/types.ts:23-44`). Slide design lives in `slide_designs.py` (HTML de servidor) + `SlideCanvas` / `Slide*.vue`.
- Dedupe realtime transcripts by `turnId` en triple capa: origen, `useRealtimeTranscription` (`hasFinalTurn`) + `useLivePresentation` (`wsOwnedTurnIds` / `pendingWsTurns`); single-producer: si el WS reclama el `turnId`, el POST no compite.
- 4s debounce (`DEBOUNCE_MS = 4000` en `useLivePresentation.ts:9`) before calling the LLM slide-generation endpoint; solo turnos finales.
- `topic_cleaner.py` produces topic/keywords/cleaned text; `enrich_event` in `realtime_proxy.py` attaches them to realtime events. `is_relevant()` existe (`topic_cleaner.py:255`) pero no es pre-filtro: el LLM decide con el campo `relevant`.
- Pendiente de verificación en código al 2026-11-04 (declarado, sin evidencia: sin `vue-router`/Clerk/Resend en dependencias, `contact.py` es stub): rutas `/` (landing) y `/live` (estudio) con vue-router, tema claro/oscuro (default SO + persistencia), auth Clerk (email/Google/Facebook dev), trial 24h desde registro de uso libre con contador invisible, contacto Resend a contacto@devstudio.cl.

## Do not commit
`.env`, `.atl/`, `PROPUESTA_CAMBIOS.md`, `node_modules/`, `dist/`, `__pycache__/`, `.venv/`

## Tests / Build
```bash
pytest backend/test_main.py backend/test_slide_designs.py -v
cd frontend && npm run build  # vue-tsc --noEmit && vite build
```

## Security
- Never expose `MODEL_API_KEY` in frontend code or `VITE_*` vars.
- CORS `*` is MVP-only; restrict origins before production.
