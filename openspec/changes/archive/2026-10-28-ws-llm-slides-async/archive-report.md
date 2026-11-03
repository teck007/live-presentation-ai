# Archive Report: Async LLM Slides over WebSocket

**Change**: `ws-llm-slides-async`
**Archived to**: `openspec/changes/archive/2026-10-28-ws-llm-slides-async/`
**Date**: 2026-10-28
**Mode**: openspec-only, interactive session, no commits (all code remains in working tree)

## Final State (at close — authoritative over intermediate snapshots)

Per the Final-State Authority hierarchy, this report describes the change AT CLOSE.
`apply-progress.md` and any earlier verify snapshots are history, not current state.

- **Working tree, no commits**: `backend/realtime_proxy.py` (session-only topic, merged
  session+event keywords, empty-only short-circuit on `len < 3`, `seq`/dedupe/
  `Semaphore(2)`/version guards intact, `request_regen`), `llm_client.py` (hardened
  `SLIDE_SYSTEM_PROMPT`: strict semantic filter with topic, free mode without topic,
  topic in timing log), `realtimeClient.ts` + `useRealtimeTranscription.ts`
  (`pendingConfig` queue flushed on `onOpen`), `App.vue`, `test_main.py` — **20/20 passing**.
- **Rule in force (model-decides)**: only empty/short transcripts (`< 3` chars trimmed)
  short-circuit to silent `slide_filtered`; every other turn reaches the LLM and only the
  model decides `relevant` true/false. Session topic is authoritative (event topic ignored
  for filtering); keywords merge session + event (cap 10). `is_relevant` remains only as
  the LLM-failure fallback inside `_fallback_slide`.
- **Specs amended to the model-decides rule**: delta specs `realtime-slide-generation`
  and `live-generation-pipeline` plus `design.md` were updated post-verify and are merged
  below. Stale `is_relevant` pre-filter references were removed from the change docs;
  main specs now state the model-decides rule (see Specs Synced).
- **Verification (final)**: `pytest backend/test_main.py -v` → **20/20**;
  `cd frontend && npm run build` → green (`vue-tsc --noEmit` + vite, 35 modules).
  Last `sdd-verify`: **PASS WITH WARNINGS** — 9/19 full checks plus 10 partial
  (build-only), 0 critical. W1 closed by the model-decides amendment in this cycle;
  W2/W3 accepted (no new JS test runner installed; stale `is_relevant` mocks documented).
  No `verify-report.md` file was persisted in the change folder; verification facts above
  come from explicit orchestrator final-state facts, which outrank the absent snapshot.
- **Tasks**: 17/17 checkboxes complete (Phases 1–5, including the Phase 5 topic-filter fix
  batch). No stale unchecked tasks remain.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `realtime-slide-generation` | Updated | 3 modified (Non-Blocking Shared Generation Tasks → model-decides + `to_thread` + session topic/merged keywords; Concurrency Cap → `Semaphore(2)` + arrival-order `seq`; Versioned Event Contract → `slide_pending` + single terminal + silent `filtered` + pre-emit drop), 1 added (Text-Only First Slice) |
| `live-generation-pipeline` | Updated | 1 modified (FIFO-1 scoped to flag-off), 2 added (Flag-Off HTTP Fallback Only; Keyword Derivation Unchanged on HTTP Fallback) |
| `topic-versioning` | Updated | 1 modified (Confirm Cancels In-Flight Work → explicit WS pre-emit rule), 1 added (Pre-Paint Version Guard) |
| `speculative-slides` | Updated | 2 modified (Never Emit Before speechComplete → WS async coverage; Default Off → WS path stays non-speculative) |

`(Previously: …)` delta annotations were dropped during merge, matching the
`2026-10-28-live-latency` archive precedent. All non-delta requirements preserved.

## Archive Contents

- `proposal.md` ✅
- `specs/` (4 domains) ✅
- `design.md` ✅ (model-decides rule)
- `tasks.md` ✅ (17/17 complete)
- `apply-progress.md` ✅ (TDD evidence: remediation R1–R3 + topic-filter fix batch)
- `archive-report.md` ✅ (this file)
- `verify-report.md` ❌ absent — facts recorded above from orchestrator final-state

## Source of Truth Updated

- `openspec/specs/realtime-slide-generation/spec.md`
- `openspec/specs/live-generation-pipeline/spec.md`
- `openspec/specs/topic-versioning/spec.md`
- `openspec/specs/speculative-slides/spec.md`

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
No commits were made per session instruction; code ships as working-tree changes.
Ready for the next change.

## Known Follow-Ups (accepted, non-blocking)

- W2: no JS test runner (vitest absent, not installed per policy) — frontend contract pinned
  from the backend + `npm run build` green.
- W3: stale `is_relevant` mocks documented in tests; `is_relevant` itself retained in
  `topic_cleaner.py` and as the `_fallback_slide` path only.
