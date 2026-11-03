# Design: Async LLM Slides over WebSocket

## Technical Approach

Move slide generation off the HTTP live path into `/ws/transcribe`. `RealtimeBridge` dedupes `speechComplete` by `turnId`, assigns arrival-order `seq`, emits `slide_pending`, and spawns `asyncio.create_task` gated by a per-connection `Semaphore(2)` that runs blocking `generate_slide` via `to_thread` with the session topic and merged keywords. Only empty/short transcripts (<3 chars trimmed) short-circuit to silent `slide_filtered`; every other turn reaches the LLM and only the model decides relevance via the strict semantic prompt (free mode when the session topic is empty). Every event carries `turnId`/`seq`/`topicVersion`; stale results drop at pre-emit (backend) and pre-paint (frontend). Frontend inserts by `seq`; the existing debounce→POST path stays as flag-off fallback with a single-producer guard. Text-only slice.

## Architecture Decisions

| Decision | Options | Tradeoff | Decision + Rationale |
|---|---|---|---|
| Concurrency model | (a) per-connection `Semaphore(2)` + `create_task` + `to_thread` / (b) global semaphore / (c) inline await | (b) couples connections; (c) blocks relay | (a): relay never waits for LLM; cap 2 bounds Meta/OpenAI cost; `to_thread` isolates sync OpenAI client without rewriting `llm_client`. |
| Ordering | (a) mandatory `seq`, frontend reorder-or-discard / (b) display on arrival | (b) simpler but scrambles narrative | (a): LLM latency varies; `seq` is the only cheap total order. Late completions with `seq <= maxPainted` drop. |
| Staleness | (a) pre-emit + pre-paint version check + cancel-on-close / (b) server check only | (b) races the confirm round-trip | (a): topic confirm cancels tasks and bumps version; either guard alone leaks stale paints under race. Belt and suspenders. |
| Event contract | (a) `slide_pending` + one terminal (`slide`/`slide_filtered`/`slide_error`, `slide_replaced`/`slide_removed` for regen) / (b) terminal only | (a) one extra frame per turn | (a): `pending` drives spinner + is the flag-on signal that suppresses the HTTP fallback for that `turnId`; silent `filtered` keeps UI clean but logs explain. |
| Fallback | (a) flag gates single producer / (b) run both, last-wins | (b) double-paints and double-bills LLM | (a): flag-on → WS only; flag-off → debounce→POST FIFO-1. No turn is produced by both. |

## Data Flow

Happy path (flag on):

```
Meta WS ──speechComplete(t1)──▶ Bridge ──dedupe turnId──▶ seq=4 assign
  Bridge ──slide_pending{t1,4,v2}──▶ Frontend (spinner, mark t1 WS-owned)
  Bridge ──create_task(sem→to_thread(generate_slide))──▶ LLM
  LLM ──slide dict──▶ Bridge ──version==current?──▶ send slide{t1,4,v2} ──▶ Frontend ──seq insert + version==current?──▶ paint
```

Stale / filtered / fallback:

```
confirm(v2→v3): cancel tasks[v2], drop queue ──▶ late v2 result ──▶ pre-emit drop (no event)
slide{v1} arrives after confirm(v3): pre-paint drop (no DOM change)
empty (<3 chars trimmed): no task ──▶ slide_filtered{t,seq,v} ──▶ log only, no LLM call
model relevant=false: task ran ──▶ slide_filtered{t,seq,v} ──▶ log only
topic empty: free mode, model relevant=true ──▶ slide; topic set: strict semantic filter
topic source: session topic authoritative, event topic ignored; keywords = session + event merged (cap 10)
flag off: no slide_pending expected ──▶ debounce 4s ──▶ POST /api/presentations/generate (FIFO-1) ──▶ paint
flag on + slide_pending seen for t1: HTTP queue skips t1 (no double-paint)
```

State per connection: `seq_counter`, `current_version`, `seen_turnIds`, `pending_tasks{turnId: Task}`, `Semaphore(2)`. Version source is the confirmed topic; regen reuses the same `turnId` with new `seq`.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/realtime_proxy.py` | Modify | `RealtimeBridge`: seq/version state, `slide_pending` emit, task spawn, semaphore, pre-emit check, cancel-on-close |
| `backend/presentation_api/utils/llm_client.py` | Modify | Reuse `generate_slide` unmodified via `to_thread`; no signature change |
| `backend/presentation_api/utils/topic_cleaner.py` | Reuse | `topic_cleaner` for `enrich_event` keywords/cleaned only; no bridge pre-filter (empty-only short-circuit); `is_relevant` remains only as the LLM-failure fallback inside `_fallback_slide` |
| `frontend/src/api/realtimeClient.ts` | Modify | Pass through new `ServerEvent` variants (no filtering) |
| `frontend/src/types.ts` | Modify | `SlidePending/Slide/SlideFiltered/SlideError` events + `seq`/`topicVersion` fields |
| `frontend/src/composables/useRealtimeTranscription.ts` | Modify | TurnId dedupe coordination; expose `topicVersion`; ignore slide events for transcript state |
| `frontend/src/composables/useLivePresentation.ts` | Modify | Seq-ordered insert, stale/filtered drop, pending counter, flag-off HTTP fallback guard |
| `frontend/src/App.vue` | Modify | Wire flag + version into composables; route WS-owned turns away from `queueTranscript` |

## Interfaces / Contracts

```python
# Backend → frontend (JSON text frames)
{"type": "slide_pending", "turnId": str, "seq": int, "topicVersion": int}
{"type": "slide", "turnId": str, "seq": int, "topicVersion": int,
 "layout": "title_text|title_bullets|text_image|quote",
 "title": str, "text": str, "bullets": [str], "keywords": [str]}
{"type": "slide_filtered", "turnId": str, "seq": int, "topicVersion": int}
{"type": "slide_error", "turnId": str, "seq": int, "topicVersion": int, "message": str}
```

```ts
type SlideWsEvent =
  | { type: "slide_pending"; turnId: string; seq: number; topicVersion: number }
  | { type: "slide"; turnId: string; seq: number; topicVersion: number; layout: SlideLayoutId; title: string; text: string; bullets: string[]; keywords: string[] }
  | { type: "slide_filtered" | "slide_error"; turnId: string; seq: number; topicVersion: number; message?: string };
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `seq` monotonic; turnId dedupe; empty-only short-circuit; model-decides relevance (off-topic calls LLM, free mode ignores event topic); version pre-emit drop | `pytest` with fake `generate_slide`, bump version mid-task |
| Integration | Semaphore(2) non-blocking relay; cancel-on-close; pending→terminal pairing | WS loopback test, slow-LLM stub, assert relay frames interleave |
| E2E | Out-of-order paint order; stale never paints; filtered silent; flag-off HTTP restores | `npm run build` + manual/Playwright: delay completions, confirm topic mid-flight |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. `to_thread` offloads an in-process sync HTTP call; no new shell, command, or repo automation.

## Migration / Rollout

No migration. Flag-off restores debounce→POST with zero code revert. Rollback: revert `realtime_proxy.py` + frontend listener commits; HTTP fallback covers flow.

## Open Questions

- [ ] Flag transport: env-only or per-session `config` frame? (Propose env default + `config` override, matching `silencePauseMs`.)
- [ ] `topicVersion` authority: who bumps on confirm — frontend event or backend state? (Propose backend-owned, broadcast to frontend.)
