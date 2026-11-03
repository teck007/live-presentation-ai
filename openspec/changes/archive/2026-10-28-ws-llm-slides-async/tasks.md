# Tasks: Async LLM Slides over WebSocket

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 320–450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend WS tasks → PR 2 frontend seq/flag wiring |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend async tasks, seq/version, pending/terminal events | PR 1 | `pytest backend/test_main.py -v` | WS loopback with slow-LLM stub, confirm mid-flight | Revert `backend/realtime_proxy.py` only; HTTP fallback covers |
| 2 | Frontend seq insert, stale/filtered drop, flag-off fallback | PR 2 | `cd frontend && npm run build` | Manual WS session: out-of-order, stale, flag-off cases | Revert frontend listener commits; flag off restores POST |

## Phase 1: Foundation (event contract and types)

- [x] 1.1 Add `SlideWsEvent` variants with `turnId/seq/topicVersion` to `frontend/src/types.ts`
- [x] 1.2 Pass through new `ServerEvent` variants in `frontend/src/api/realtimeClient.ts` without filtering

## Phase 2: Core Backend (non-blocking generation)

- [x] 2.1 Add `seq_counter`, `seen_turnIds`, `pending_tasks`, `Semaphore(2)` state to `backend/realtime_proxy.py`
- [x] 2.2 Emit `slide_pending` on spawn; run `to_thread(generate_slide)` via `asyncio.create_task`
- [x] 2.3 Short-circuit `is_relevant=false` to silent `slide_filtered` in `backend/realtime_proxy.py`
- [x] 2.4 Enforce pre-emit version check and cancel-on-close/topic-confirm in `backend/realtime_proxy.py`

## Phase 3: Frontend Wiring (order, staleness, fallback)

- [x] 3.1 Insert slides by `seq`, drop `seq <= maxPainted` in `frontend/src/composables/useLivePresentation.ts`
- [x] 3.2 Add pre-paint `topicVersion` guard; log-only `slide_filtered` in `useLivePresentation.ts`
- [x] 3.3 Gate HTTP fallback: skip WS-owned `turnId`, keep FIFO-1 flag-off in `useLivePresentation.ts`
- [x] 3.4 Wire flag + version, route WS turns away from `queueTranscript` in `frontend/src/App.vue`

## Phase 4: Testing and Verification

- [x] 4.1 RED: failing tests for dedupe, seq order, stale pre-emit drop, filtered silence in `backend/test_main.py`
- [x] 4.2 GREEN: make RED tests pass without blocking relay; verify `pytest backend/test_main.py -v`
- [x] 4.3 Verify out-of-order, stale, filtered, flag-off scenarios; run `cd frontend && npm run build`

## Phase 5: Topic-filter fix (agreed rule, no commits)

- [x] 5.1 Backend: session-only topic, merged keywords, empty-only short-circuit in `handle_speech_complete`
- [x] 5.2 LLM prompt: strict semantic filter with topic, free mode without topic, topic in log
- [x] 5.3 Frontend: queue `{topic, topicVersion}` config until `onOpen` (client + composable)
- [x] 5.4 Tests: update `filtered_silence` to empty-only + 3 new rule tests; `pytest backend/test_main.py -v` 20/20 + `npm run build` green
