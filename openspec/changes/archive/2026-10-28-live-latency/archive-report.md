# Archive Report: live-latency

**Change**: `live-latency`
**Archived to**: `openspec/changes/archive/2026-10-28-live-latency/`
**Archive date (ISO)**: 2026-10-28
**Artifact store (effective)**: openspec + inline. Session preflight declared `both`,
but Engram is unavailable in executor runtime, so no Engram observation was read or
written; the filesystem audit trail plus this inline return constitute the record.
**Commit policy**: working tree only — no commits, no pushes, no PRs were made in any
phase per session constraint. This archive moves only OpenSpec audit-trail files and
copies delta specs into `openspec/specs/`; it merges no code branch.

## Final State at Close (authoritative)

Source ranking per Final-State Authority: explicit final-state facts in the
orchestrator launch outrank the intermediate snapshots (`apply-progress`,
`verify-report`). Where a fact below cites a snapshot, it is attributed with time.

- **Tasks**: 17/17 complete. Archived `tasks.md` contains zero unchecked
  implementation tasks (`[x]` count 17, `[ ]` count 0, verified at archive time).
  Phase 0 (0.1–0.5), Phase 1 (1.1–1.5), Phase 2 (2.1–2.4 incl. U3 topic slice),
  Phase 3 (3.1–3.3) all done.
- **Tests**: `pytest backend/test_main.py -v` = **64 passed**
  (26 pre-existing + 11 U1 + 13 U2 + 7 U3 + 7 U4). No code fixes were needed after
  verify; the suite was green at verification time and nothing changed it since.
- **Build**: `cd frontend && npm run build` = green (vue-tsc + vite, 35 modules).
- **Scenarios**: 47/47 evidenced — 37 via passing backend unit tests, 10 frontend-only
  scenarios via `vue-tsc` + `vite build` exit 0 plus source inspection, per the
  project's testing strategy (no TS runner exists in the repo).
- **Design**: D1–D6 followed (per `verify-report` coherence matrix, at verification time).
- **Behavioral invariants at close**: no provisional paints; both flags default off;
  ever-visible-only regen; hide-instantly on confirm; turnId-follow canvas enforced.
- **Verify verdict**: PASS WITH WARNINGS, 0 blockers, 0 criticals. No CRITICAL issue
  exists, so the archive-blocking critical gate does not trigger.

## Native Review Gate (recorded explicitly)

No structured `reviewGate` status was provided in the launch, and no native review
artifacts exist for this change (verified at archive time:
`openspec/changes/live-latency/reviews/` absent — no transaction, ledger, receipt,
bundle, or gate-context). This change was developed and archived under the session's
working-tree-only constraint (no commits, no pushes, no PRs), so no PR/review flow
was ever engaged and no receipt could govern it. This archive performs no code merge —
it moves only spec/design/task audit files and copies specs to the source of truth —
and `verify-report` records 0 criticals / 0 blockers. The close is therefore recorded
as a **working-tree archive with no native receipt**, explicitly authorized by the
orchestrator launch, not as a reviewed merge.

## Specs Synced

`openspec/specs/` was empty before this archive (proposal-declared: no modified
capabilities), so every delta spec was a full spec and was copied verbatim
(byte-identical, confirmed by `diff` per domain). No destructive merge occurred;
`rules.archive` ("warn before merging destructive deltas") required no warning.

| Domain | Action | Details |
|--------|--------|---------|
| live-latency-baseline | Created | 4 requirements, 8 scenarios |
| live-generation-pipeline | Created | 7 requirements, 10 scenarios |
| realtime-slide-generation | Created | 8 requirements, 9 scenarios |
| topic-versioning | Created | 8 requirements, 10 scenarios |
| speculative-slides | Created | 7 requirements, 10 scenarios |

Totals: 34 requirements, 47 scenarios — matching the verify compliance matrix
(34/34 requirements, 47/47 scenarios at verification time).

## Archive Contents

- proposal.md ✅
- specs/ (5 domains) ✅
- design.md (final PASS version) ✅
- tasks.md (17/17 complete, no stale checkboxes) ✅
- apply-progress.md (U1+U2+U3+U4 merged intermediate snapshot) ✅
- verify-report.md (204 lines, verdict pass-with-warnings, intermediate snapshot) ✅
- archive-report.md (this file) ✅

## Source of Truth Updated

- `openspec/specs/live-latency-baseline/spec.md`
- `openspec/specs/live-generation-pipeline/spec.md`
- `openspec/specs/realtime-slide-generation/spec.md`
- `openspec/specs/topic-versioning/spec.md`
- `openspec/specs/speculative-slides/spec.md`

Active changes directory no longer contains `live-latency` (only `archive/` remains).

## Intermediate Snapshots (history, not final state)

- `apply-progress.md` describes U1+U2+U3+U4 unit evidence at apply time (test
  progressions 37 → 50 → 57 → 64, per-unit rollback boundaries). Valid history of
  what each unit proved when written.
- `verify-report.md` (orchestrator-persisted via filesystem copy from the
  `/tmp/live-latency-verify-candidate.md` candidate, 204 lines, verdict
  pass-with-warnings) describes verification-time evidence: 64/64 tests, green build,
  47/47 scenarios, D1–D6 followed, warnings W1–W3 and suggestions S1–S2. No work
  occurred after it that would change its numbers (per launch final-state facts).

## Known Carries (NOT resolved in archive — recorded for follow-up)

1. Continuation/merge machinery (`decide_continuation`, `merge_into_previous`,
   `ADVANCE_MARKERS`) exceeds all five specs — needs spec amendment or removal.
2. `wsSlideMode` latch in `App.vue` exceeds specs (design fix removed it) — needs
   amendment or removal; removal would force HTTP+WS double generation per turn.
3. `normalize_spec_text` case quirk: lowercases after `clean_topic` whose stopwords
   are case-sensitive, so case variants mismatch and discard.
4. No coverage tool (`pytest-cov`/`coverage` absent) — changed-file coverage argued by
   construction only.
5. No frontend test runner — 10 frontend scenarios rest on build + inspection evidence.
6. Verify warnings W1–W3 and suggestions S1–S2 remain open, non-blocking per verify
   verdict.

## Working-Tree State at Close

`git status --short` at last pre-archive check: 11 modified app files
(`presentation.py`, `llm_client.py`, `realtime_proxy.py`, `test_main.py`, `App.vue`,
`presentation.ts`, `realtimeClient.ts`, `SlideCanvas.vue`, `useLivePresentation.ts`,
`useRealtimeTranscription.ts`, `types.ts`) plus untracked
`PROPUESTA_CAMBIOS.md`, `backend/presentation_api/utils/latency.py`, and `openspec/`.
No commits, pushes, or PRs were made. The implementation lives in the working tree;
this archive closes the planning/verification trail, not the code integration.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
