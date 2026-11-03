# Proposal: live-latency

## Intent

Cut live latency (speechComplete → paint). Today: 4s debounce, overwrite queue, 500-token LLM calls, HTTP-only. No provisional slides; "Generating..." stays.

## Scope

### In Scope

- P0: turnId timestamps (complete → LLM start/end → paint); p50/p95 over ~20 phrases; extend `[llm]` log.
- P1: trigger on final; FIFO c=1 + turnId/text dedupe; tokens 500→~220 + truncation test; `topic_cleaner` prefilter (LLM authoritative); POST + fallback; begin topicVersion.
- P2: config topic+flag; non-blocking tasks; shared AsyncOpenAI prompt/parse/fallback; sem 2; seq buffer; `slide`/`slide_filtered`/`slide_error` + `slide_replaced`/`slide_removed` (turnId+seq+version); server dedupe; cancel on close; flag off → HTTP.
- P3 hidden: stable partials only (≥800ms, ≥6 words); never pre-complete; match-reuse else discard; max 1/turn; default off; metrics; go-live ~60%.
- Topic (B): 500ms typing debounce; confirm cancels in-flight, drops buffer, relaunches finals in seq, version-checks before emit. Visible hide instantly; registry kept; background regen (viewed first, c=2); reappear in seq / removed if filtered / hidden+error+retry on failure. Only ever-visible reevaluated.
- Canvas follows turnId, not index.

### Out of Scope

- Batch flow, CORS, coverage, provisional slides.

## Capabilities

### New Capabilities

- `live-latency-baseline`: instrumentation + p50/p95.
- `live-generation-pipeline`: FIFO, tokens, prefilter, fallback.
- `realtime-slide-generation`: WS tasks, ordering, dedupe, cancel, events.
- `speculative-slides`: hidden speculation, metrics, gate.
- `topic-versioning`: lifecycle, hide/regen/replace, turnId-follow.

### Modified Capabilities

- None (empty `openspec/specs/`).

## Approach

Flaggable sequence: P0 measures; P1 shrinks trigger+payload on POST; P2 WS tasks; P3 gated speculation. topicVersion in config/POST/events/registry from P1.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/realtime_proxy.py` | Modified | relay/tasks/ordering/events |
| `backend/presentation_api/controllers/presentation.py` | Modified | topic_version/fallback |
| `backend/presentation_api/utils/llm_client.py` | Modified | prompt/tokens/AsyncOpenAI |
| `backend/topic_cleaner.py` | Modified | prefilter entry |
| `frontend/src/composables/useLivePresentation.ts` | Modified | queue/abort/registry |
| `frontend/src/composables/useRealtimeTranscription.ts` | Modified | final trigger/dedupe |
| `frontend/src/components/SlideCanvas.vue` | Modified | turnId follow/hide |
| `backend/test_main.py` | Modified | TDD per phase |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 2× LLM cost on topic change | High | Accepted; visible-only, c=2 |
| Out-of-order paint | Med | seq buffer + version check |
| Focus jump on removal | Med | turnId follow; viewed-first |
| Retroactive proposal vs 11 dirty files | High | Diff check pre-spec |

## Rollback Plan

- P0 drop instrumentation; P1 restore debounce/tokens; P2 flag off → HTTP; P3 flag off; topic fail keeps old visible.

## Dependencies

- Meta ASR realtime, `muse-spark-1.3`, ffmpeg, Python 3.10+, Node 18+.

## Success Criteria

- [ ] p50/p95 over ~20 phrases improved.
- [ ] No provisional paints.
- [ ] Topic change hides instantly, order kept, failures retryable.
- [ ] `pytest backend/test_main.py -v` green; flags restore prior behavior.
