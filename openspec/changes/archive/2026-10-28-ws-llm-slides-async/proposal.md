# Proposal: Async LLM Slides over WebSocket

## Intent

Remove slide latency from the live path: `speechComplete → 4s debounce → blocking POST /api/presentations/generate` stalls slides behind the LLM. Move generation into `/ws/transcribe` as non-blocking tasks emitting ordered, versioned events.

## Scope

### In Scope

- WS `slide_pending` / `slide` / `slide_filtered` / `slide_error` on `/ws/transcribe`; each carries `turnId`, `seq`, `topicVersion`.
- Backend `asyncio.create_task` + `to_thread(generate_slide)` + `Semaphore(2)`; `is_relevant` first; topic from config.
- Arrival order: mandatory `seq`; frontend reorders or discards late completions.
- Staleness: drop in-flight results on `topicVersion` bump (no emit/paint).
- Off-topic: silent `slide_filtered`; no visible noise.
- Frontend pushes slides directly; POST generate stays as flag-off fallback.
- Text-only first slice.

### Out of Scope

- Images/media; batch `POST /api/transcribe` changes.
- Speculation tuning; token unification (220 vs 500 stays diverged).
- Removing 4s debounce / FIFO-1 on HTTP fallback.

## Capabilities

### New Capabilities

- None — first slice reuses existing capabilities.

### Modified Capabilities

- `realtime-slide-generation`: add `slide_pending`; pin `to_thread` + Semaphore(2) + arrival-order.
- `live-generation-pipeline`: HTTP path is flag-off fallback only (FIFO-1, 220 tokens stay).
- `topic-versioning`: version-bump discard applies to WS tasks.
- `speculative-slides`: stays default-off; never-emit-before-final holds.

## Approach

- `realtime_proxy.py`: dedupe `turnId`, assign `seq`, emit `slide_pending`, spawn task; version check before emit.
- Frontend: `realtimeClient.ts` handler; `useLivePresentation` inserts by `seq`, drops stale/filtered; flag-off keeps debounce→POST.
- Implications: flag gates a single producer; `slide_filtered` visible only in logs; order/regen shared with topic-versioning.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/realtime_proxy.py` | Modified | Task spawn, semaphore, seq/version, event emit |
| `backend/presentation_api/utils/llm_client.py` | Modified | Reuse `generate_slide` / `is_relevant` via `to_thread` |
| `frontend/src/api/realtimeClient.ts` | Modified | New event types + listener |
| `frontend/src/composables/useLivePresentation.ts` | Modified | Seq-order insert, stale/filtered handling |
| `frontend/src/composables/useRealtimeTranscription.ts` | Modified | TurnId dedupe coordination |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Out-of-order completions | Med | Mandatory `seq`; reorder-or-discard |
| Stale paint after topic change | Med | Pre-emit + pre-paint version check |
| Semaphore starvation | Low | Cap 2 + cancel-on-close |
| Double-paint WS + HTTP | Low | Flag gates one producer |

## Rollback Plan

- Per `openspec/config.yaml` `rules.proposal`: flag off restores debounce→POST with zero code revert. If WS events misbehave, revert `realtime_proxy.py` + listener commits; HTTP fallback covers flow. No migration to undo.

## Dependencies

- None new; reuses existing key, proxy, LLM client.

## Success Criteria

- [ ] Final-to-slide p50 drops vs baseline; relay never blocks.
- [ ] Out-of-order, stale, filtered, flag-off cases per rules.
- [ ] `pytest backend/test_main.py -v` and `cd frontend && npm run build` pass.
