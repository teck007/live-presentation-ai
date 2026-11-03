# Apply Progress: Async LLM Slides over WebSocket

Mode: Strict TDD (test runner `pytest backend/test_main.py -v` per `openspec/config.yaml`).

## Cumulative task state (merge with tasks.md, no overwrite)

All tasks in `tasks.md` remain `[x]` (U1 backend + U2 frontend, applied pre-remediation).
This file adds the remediation batch (verify-FAIL recovery) on top — no prior completion lost.

- Phase 1 (types/realtimeClient): [x] kept
- Phase 2 (backend seq/version/pending/terminal): [x] kept
- Phase 3 (frontend order/stale/fallback): [x] kept
- Phase 4 (tests/verify): [x] kept
- Remediation R1 (regen `slide_replaced`/`slide_removed` backend + frontend + tests): [x] done
- Remediation R2 (contract pin + text-only assert + `slide_error` on LLM failure): [x] done
- Remediation R3 (TDD evidence artifact = this file): [x] done

## Remediation scope decision

Verify-FAIL offered Option A (implement regen) if it fits in <100 prod lines, else Option B
(defer regen in spec). Chose **Option A**: prod diff is ~65 lines
(`realtime_proxy.py` ~30: `request_regen` + `is_regen` terminal mapping;
`types.ts` ~18: two events + union + guard; `useLivePresentation.ts` ~25:
paint-time replace, remove case, ordered buffering). No spec edit needed —
`realtime-slide-generation` already requires `slide_replaced`/`slide_removed`.

Frontend unit tests (5x `handleSlideEvent`) were requested only if vitest exists.
`frontend/package.json` has no vitest/runner — per instructions no new framework
was installed; the contract is pinned from the backend instead
(pending/terminal shapes, version guards via existing stale tests, text-only assert,
`slide_error` on LLM failure).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| U1 backend tasks (pre-existing) | `backend/test_main.py` | Unit | ✅ 11/11 baseline kept | ✅ prior batch | ✅ prior batch | ✅ dedupe/seq/stale/filtered/non-blocking/sem-cap | ➖ none needed |
| U2 frontend wiring (pre-existing) | build only | Build | ✅ `npm run build` green pre/post | ➖ structural wiring | ✅ `vue-tsc` + vite pass | ➖ no runner (vitest absent, not installed per policy) | ➖ none needed |
| R1 regen `request_regen` + replaced/removed | `backend/test_main.py` | Unit | ✅ 11/11 before edit | ✅ 3 fail `AttributeError: request_regen` | ✅ 17/17 after impl | ✅ 3 cases: replaced-new-seq / filtered→removed / unknown→False | ➖ minimal, no duplication |
| R2 contract/text-only/error | `backend/test_main.py` | Unit | ✅ same baseline | ✅ written vs existing code (pin behavior) | ✅ 17/17 | ✅ terminal-unico + no-media-keys + error-sin-slide | ➖ none needed |
| R3 frontend regen handling | `npm run build` | Build | ✅ green pre/post | ➖ type-level (new variants) | ✅ `vue-tsc --noEmit` + vite pass | ➖ backend triangulates behavior; no JS runner | ➖ alias `SlidePaintEvent` after parser rejected multiline generic |

### Test Summary

- **Total tests written (remediation)**: 6 backend (`contract_shapes`, `text_only_no_media`,
  `error_on_llm_failure`, `regen_replaced`, `regen_filtered_removed`, `regen_unknown_rejected`)
- **Total tests passing**: 17/17 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (17), Build (`npm run build` green)
- **Approval tests**: none — no refactoring of existing behavior (only additive regen path;
  existing 11 tests untouched and still green)
- **Pure functions created**: 0 (stateful bridge/composable by design; regen reuses `_run_slide_task`)

## Deviations from design

None. `request_regen` follows the design contract: same `turnId`, new arrival-order `seq`,
pre-emit version check inherited from `_run_slide_task`, terminal `slide_replaced`
(success) / `slide_removed` (filtered) instead of `slide` / `slide_filtered`.
Unknown `turnId` is rejected (`False`, no event) so regen can never fabricate a slide.
Frontend paints `slide_replaced` through the same `drainInOrder` gate (order + pre-paint
guard preserved) and removes the prior slide of the turn at paint time.

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `.venv/bin/python -m pytest backend/test_main.py -v` → 17 passed |
| Runtime harness + result | `cd frontend && npm run build` (`vue-tsc --noEmit && vite build`) → built clean (35 modules) |
| Rollback boundary | `backend/realtime_proxy.py` (`request_regen` + `is_regen` branches), `frontend/src/types.ts` (2 events), `frontend/src/composables/useLivePresentation.ts` (2 cases + paint-time replace), `backend/test_main.py` (6 tests). Revert these hunks only; HTTP fallback untouched. |

## Status

Remediation complete. Ready for re-verify.

---

## Fix batch: topic-filter (agreed rule, no commits)

Rule: `topic == ""` -> free mode, everything goes to the LLM.
`topic != ""` -> everything goes to the LLM with that topic; only the model
decides `relevant` true/false semantically. The `is_relevant` pre-filter is
removed from the path; the only short-circuit left is empty/short transcript.

Scope (this batch only, working tree, no commits):
- `backend/realtime_proxy.py` `handle_speech_complete`: topic comes ONLY from
  `current_topic` (event topic ignored for filtering); keywords merge
  session + event (no `or`); empty/short (<3 chars) -> `slide_filtered` without
  LLM. `seq`/dedupe/`Semaphore(2)`/version check/cancel-on-close unchanged.
- `backend/presentation_api/utils/llm_client.py`: hardened `SLIDE_SYSTEM_PROMPT`
  (strict semantic filter with topic, free mode without topic); signature
  unchanged; topic added to the timing log.
- `frontend/src/api/realtimeClient.ts` + `useRealtimeTranscription.ts` +
  `frontend/src/App.vue`: queue `{topic, topicVersion}` config until `onOpen`
  (flush in `onopen`); fixes `sendSessionConfig`-after-`start()` race.
- `backend/test_main.py`: updated `test_ws_filtered_silence_no_llm` to the new
  rule (empty-only) + 3 new tests (off-topic with topic calls LLM and uses
  session topic; empty never calls LLM; free mode ignores event topic).

### TDD Cycle Evidence (fix batch)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Backend topic-filter rule | `backend/test_main.py` | Unit | ✅ 17/17 baseline | ✅ 2 failed (`offtopic_calls_llm`, `free_mode_ignores_event_topic`; empty already filtered) | ✅ 20/20 after fix | ✅ 3 cases: off-topic-with-topic / empty-short / free-mode + updated `filtered_silence` to empty-only | ➖ minimal, no duplication |
| LLM prompt hardening | build + unit | Unit | ✅ same baseline | ➖ prompt text (no runner change) | ✅ 20/20 + topic in log | ✅ free-mode vs strict-mode wording in one prompt | ➖ none needed |
| Frontend config queue | `npm run build` | Build | ✅ green pre/post | ➖ race (no JS runner; vitest absent) | ✅ `vue-tsc --noEmit` + vite pass (35 modules) | ➖ client-level + composable-level queue (two layers, one race) | ➖ none needed |

### Test Summary (fix batch)

- **Total tests written**: 3 new (`offtopic_calls_llm`, `empty_no_llm`, `free_mode_ignores_event_topic`) + 1 updated (`filtered_silence_no_llm` -> empty-only)
- **Total tests passing**: 20/20 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (20), Build (`npm run build` green)
- **Approval tests**: none — behavior change is spec-driven by the agreed rule (old `is_relevant=False` short-circuit superseded)
- **Pure functions created**: 0 (stateful bridge/composable by design)

### Work Unit Evidence (fix batch)

| Evidence | Value |
|---|---|
| Focused test command + result | `.venv/bin/python -m pytest backend/test_main.py -v` → 20 passed |
| Runtime harness + result | `cd frontend && npm run build` (`vue-tsc --noEmit && vite build`) → built clean (35 modules) |
| Rollback boundary | `handle_speech_complete` filter hunk + `SLIDE_SYSTEM_PROMPT` hunk + `pendingConfig` queue hunks (`realtimeClient.ts`, `useRealtimeTranscription.ts`, `App.vue` comment) + 4 test hunks. Revert these hunks only; regen/version/seq logic untouched. |

### Status (fix batch)

Fix complete. Ready for re-verify. No commits per session instruction.
