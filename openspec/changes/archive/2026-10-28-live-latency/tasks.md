# Tasks: live-latency

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1200–1600 (dirty +1890/−137) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | U1 base+pipe → U2 bridge → U3 topic → U4 spec |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | P0 baseline + P1 pipeline | PR 1 | `pytest backend/test_main.py -v -k baseline` | Speak 20 phrases, read p50/p95 | Drop instrumentation; restore debounce/tokens |
| 2 | P2 bridge tasks/seq/events | PR 2 | `pytest backend/test_main.py -v -k bridge` | Flag on, 2 slow finals, check order | Flag off → HTTP owns generation |
| 3 | P2 topic lifecycle/regen | PR 3 | `pytest backend/test_main.py -v -k topic` | Retopic mid-flight, check hide + regen | Keep old visible; disable regen |
| 4 | P3 speculation + gate | PR 4 | `pytest backend/test_main.py -v -k speculation` | Stable partials, check metrics, no early paint | Flag off (default); no behavior change |

## Phase 0: Baseline (adopt dirty tree + instrument)

- [x] 0.1 Diff dirty tree vs specs/design; adopt fits, list rejects.
- [x] 0.2 RED: 4-timestamp order, filtered-no-paint, no-turnId passthrough, p50/p95 ~20 + provisional.
- [x] 0.3 GREEN: turnId store (complete, llm_start/end, paint); paint via local clock, no wire change; window ~20.
- [x] 0.4 Extend `[llm]`: turnId, version, blocks, elapsed on all outcomes.
- [x] 0.5 Verify: `pytest backend/test_main.py -v` + `cd frontend && npm run build`.

## Phase 1: HTTP pipeline

- [x] 1.1 RED: instant trigger, FIFO c=1, dedupe zero-LLM, fold-to-one + signal, trim-not-422, fallback.
- [x] 1.2 GREEN `useRealtimeTranscription.ts`: fire on final; turnId/text dedupe.
- [x] 1.3 GREEN `useLivePresentation.ts`: FIFO c=1 + dedupe; indicator only, never provisional paint.
- [x] 1.4 GREEN `llm_client.py` (~220, fold+signal) + prefilter; `presentation.py` ids, trim-not-422, fallback.
- [x] 1.5 Verify: `pytest backend/test_main.py -v` + `cd frontend && npm run build`.

## Phase 2: Bridge + topic versioning

- [x] 2.1 RED (U2 bridge subset): flag-off relay; sem-2 reorder; 5 versioned events; stale silence; dedupe; cancel close/confirm. Topic RED (500ms bump; hide+registry; viewed-first c=2; remove/retry; neighbor) → U3.
- [x] 2.2 GREEN `realtime_proxy.py` (U2): config(topic+version+flag); tasks on shared AsyncOpenAI; sem 2, seq, version-check, dedupe, cancel on close/confirm.
- [x] 2.3 GREEN frontend: 500ms confirm + abort; hide-all + registry; ever-visible regen viewed-first c=2; turnId follow + neighbor fallback.
- [x] 2.4 Verify: `pytest backend/test_main.py -v` + `cd frontend && npm run build`.

## Phase 3: Speculation (default off)

- [x] 3.1 RED: 800ms/6-word gate; never-emit-before-complete; normalized match-reuse vs discard; max-1/turn; default-off; metrics + ~60% gate.
- [x] 3.2 GREEN: hidden tasks one/turnId; exact-match reuse else discard; hit/miss/wasted counters.
- [x] 3.3 Verify: `pytest backend/test_main.py -v` + `cd frontend && npm run build`; gate off below ~60%.
