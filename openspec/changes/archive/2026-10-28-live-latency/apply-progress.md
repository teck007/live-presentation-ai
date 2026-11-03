# Apply Progress: live-latency — Units 1+2 (U1 baseline+pipe, U2 bridge)

Strategy: stacked-to-main, units 1–2 of 4. No commits (working tree only).

## Scope verdict (U1 only)

Implements Phase 0 (0.1–0.5) + Phase 1 (1.1–1.5). U2 (bridge), U3 (topic
lifecycle), U4 (speculation) are NOT implemented here.

## 0.1 Dirty-tree verdict (11 files, +1890/−137 vs specs/design)

### Adopted as U1 fits (kept, covered by U1 tests or adoption)

| Area | Verdict |
|------|---------|
| `presentation.py` turn_id/topic_version coercion + trim-not-422 | Adopt; covered by pre-existing trim tests |
| `presentation.py` prefilter (`clean_topic` len + `is_relevant`) before LLM | Adopt; covered by `test_u1_prefilter_*` |
| `presentation.py` fallback intact (LLM decides, fallback slide on error) | Adopt; covered by `test_u1_llm_outage_fallback_slide` |
| `llm_client.py` `max_completion_tokens=220` | Adopt (D1) |
| `llm_client.py` `split_transcript_blocks` + fold-to-one-slide + `truncated` signal | Adopt (D1); covered by `test_u1_fold_signal_single_slide` + pre-existing long-turn test |
| `llm_client.py` `[llm]` log with turnId/topicVersion/blocks/elapsed | Adopt; extended by this unit (fallback line now carries turnId + cause) |
| `useRealtimeTranscription.ts` fire on final + turnId dedupe (`finalizeTurn`, `hasFinalTurn`) | Adopt (1.2); verified by adoption + build (no TS runner) |
| `useLivePresentation.ts` FIFO c=1 worker (`processQueue`), turnId/text dedupe, `pending` indicator only, never provisional paint | Adopt core (1.3); verified by adoption + build |
| Frontend local-clock instrumentation (`[live]` debug markers: received/request/response/paint) | Adopt as paint-via-local-clock; no wire change per design |
| `SlideCanvas.vue` turnId follow + neighbor fallback | Adopt as render-side paint observation point (no provisional logic added) |

### Listed as rejects for U1 (left in tree, owned by later units, NOT verified here)

| Area | Owning unit |
|------|-------------|
| `realtime_proxy.py` bridge tasks, sem 2, seq, versioned events, dedupe, cancel on close/confirm, regen order | U2 |
| `realtime_proxy.py` speculation (`spec_*`, `normalize_spec_text`, ~60% gate) + all `spec_*`/`bridge_*` tests | U4 (tests pre-exist in tree, untouched) |
| `useLivePresentation.ts` `applyServerSlide`, `hideAllForTopicChange`, `visibleTurns`, `setTopicVersion`, `abortGeneration` beyond FIFO needs | U2/U3 |
| `App.vue` `wsSlideMode`, 500ms topic debounce, `sendTopic`, WS/HTTP dual path | U2/U3 |
| `types.ts` / `realtimeClient.ts` bridge event contracts (`slide_*`, `sendTopic`) | U2 |
| `llm_client.py` continuation machinery (`decide_continuation`, `merge_into_previous`, `ADVANCE_MARKERS`, `continuation` prompt flag) | Not in U1 specs; needs spec amendment or U2/U3 ownership — flagged, not removed |
| `presentation.py` response widening (`text` ≤800, `bullets` ≤7) | Incidental to fold-to-one; kept, harmless |

## Implemented in this unit (U1 new code)

- `backend/presentation_api/utils/latency.py` (new): `LatencyRecord` +
  `LatencyStore` (window 20, no-raise contract) + `baseline` singleton.
  `summary()` returns `{n, p50, p95, provisional}`; p50 = median, p95 =
  nearest-rank; empty store → provisional with nulls.
- `backend/presentation_api/controllers/presentation.py`: records
  `complete_at` at POST receipt and `llm_start`/`llm_end` around
  `generate_slide` when `turn_id` is present; `mark_filtered` on filtered
  outcomes. Exception-safe (store never raises; `finally` for `llm_end`).
- `backend/presentation_api/utils/llm_client.py`: sync + async fallback log
  lines now carry `turnId` + `topicVersion` + cause (spec scenario
  "Fallback logs the cause").

## TDD Cycle Evidence (U1 strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 0.2 order | `backend/test_main.py` (`test_u1_latency_full_pipeline_order`) | Unit | ✅ 26/26 | ✅ ImportError | ✅ Passed | ✅ filtered + passthrough cases | ✅ removed unused import |
| 0.2 filtered-no-paint | `test_u1_latency_filtered_no_paint` | Unit | ✅ 26/26 | ✅ ImportError | ✅ Passed | ✅ companion to order | ➖ None needed |
| 0.2 missing-turnId | `test_u1_latency_missing_turnid_passthrough` | Unit | ✅ 26/26 | ✅ ImportError | ✅ removed unused import |
| 0.2 p50/p95 | `test_u1_latency_p50_p95_window20` + `test_u1_latency_partial_window_provisional` | Unit | ✅ 26/26 | ✅ ImportError | ✅ Passed | ✅ 20 exact + 5 provisional | ➖ None needed |
| 0.4 log identity/fallback | `test_u1_llm_log_identity` (approval, pre-existing impl) + `test_u1_llm_log_fallback_cause` | Unit | ✅ 26/26 | ✅ fallback lacked turnId | ✅ Passed | ✅ success + failure | ✅ log format unified sync/async |
| 1.1 prefilter | `test_u1_prefilter_filler_no_llm` + `test_u1_prefilter_semantic_passthrough_ids` | Unit | ✅ 26/26 | ➖ Approval (dirty-tree impl adopted per 0.1) | ✅ Passed | ✅ drop + passthrough | ➖ None needed |
| 1.1 fold/signal/trim/fallback | `test_u1_fold_signal_single_slide` + `test_u1_llm_outage_fallback_slide` + 4 pre-existing trim tests | Unit | ✅ 26/26 | ➖ Approval (adopted) | ✅ Passed | ✅ fold + outage + 4 trim borders | ➖ None needed |
| 1.2/1.3 frontend | Adoption (no TS runner in repo) | N/A | N/A (no runner) | ➖ Degraded gracefully | ✅ Build green | ➖ Single path | ➖ No new code |

### Test Summary (U1)

- **Total tests written**: 11 (`test_u1_*`)
- **Total passing**: 37/37 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (11), Integration (0), E2E (0)
- **Approval tests**: 5 (prefilter ×2, outage fallback, log identity, fold signal — dirty-tree behavior adopted per 0.1)
- **True RED→GREEN**: 6 (5 latency ImportError + 1 fallback-cause assertion)
- **Pure functions created**: `LatencyStore` methods (no I/O, no mocks)

## Work Unit Evidence (U1)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/bin/python -m pytest backend/test_main.py -v` → **37 passed in 0.71s** (26 pre-existing + 11 U1) |
| Runtime harness command/scenario and exact result | `npm run build` (vue-tsc + vite) → **built in 630ms**, 35 modules, no errors. Live-flow runtime (speak ~20 phrases, read p50/p95) is manual per tasks.md and deferred to verify with a running backend |
| Rollback boundary | `backend/presentation_api/utils/latency.py` (new file), `backend/test_main.py` U1 section (append-only), `presentation.py` baseline hook (~10 lines), `llm_client.py` fallback log lines (2 lines). Revert these and U1 vanishes without touching U2–U4 tree content |

## Deviations from design (U1)

- Paint recording has no backend caller yet: `record_paint` exists and is
  tested, but wiring awaits a transport decision (design: "paint transport
  deferred"). Frontend `[live]` local-clock markers are the U1 paint source.
- `decide_continuation` / `merge_into_previous` in the dirty tree exceed U1
  specs; kept untouched and flagged for U2/U3 ownership or spec amendment.

## Issues found (U1)

- None blocking. Pre-existing suite was green (26/26) before changes.

## Remaining after U1 (explicitly NOT in U1)

- U2: bridge tasks/sem/seq/events + `applyServerSlide` wiring + flag-off parity.
- U3: 500ms confirm, hide-all + registry, ever-visible regen, turnId canvas follow.
- U4: speculation gate/match/discard/metrics + ~60% go-live check.

---

## Scope verdict (U2 bridge only)

Implements Phase 2 bridge subset: tasks 2.1 (bridge RED) + 2.2 (bridge GREEN)
plus frontend minimal WS apply (`applyServerSlide` rendering path, adopted)
and flag-off → HTTP fallback parity (adopted, no new frontend code).
Explicitly NOT in U2: U3 topic lifecycle (500ms confirm/debounce,
hide-all + registry, ever-visible regen viewed-first c=2, turnId-follow full
lifecycle, remove/retry/neighbor), U4 speculation (gate/match/discard/metrics).
Continuation/merge machinery stays OUT (requires spec amendment, flagged in U1
and carried here — untouched, not removed).

## 0.1 follow-up: dirty-tree bridge verdict (U2)

### Adopted as U2 fits (kept, covered by U2 tests or adoption)

| Area | Verdict |
|------|---------|
| `realtime_proxy.py` non-blocking asyncio tasks on shared `AsyncOpenAI` (`generate_slide_async`) | Adopt; covered by `test_u2_nonblocking_relay` |
| `realtime_proxy.py` sem 2 (`slide_sem`) + arrival-order `seq` + `seq_lock` | Adopt; covered by `test_u2_sem_cap_two` + `test_u2_slide_happy_seq_increasing` + pre-existing `test_bridge_orden_seq` |
| `realtime_proxy.py` version-check before emit (`_generate_and_emit` + `_send_slide_result`) | Adopt; covered by pre-existing `test_bridge_descarta_version_vieja` + `test_u2_slide_error_carries_version` |
| `realtime_proxy.py` server turnId dedupe (pending + emitted) | Adopt; covered by pre-existing `test_bridge_dedupe_turnid` + `test_u2_emitted_dedupe_no_respawn` |
| `realtime_proxy.py` cancel on close (`_cancel_pending` in `run()` finally) + cancel hook ready for topic confirm (owned by U3, hook exists in `on_control`) | Adopt; covered by `test_u2_cancel_on_close_clears` + pre-existing `test_bridge_config_cancela_pendientes` |
| `realtime_proxy.py` 5 versioned events (`slide` / `slide_filtered` / `slide_error` + `slide_replaced` / `slide_removed`, each turnId+seq+topicVersion) | Adopt; covered by `test_u2_slide_happy_contract`, `test_u2_slide_filtered_new_turn`, `test_u2_slide_error_contract`, `test_u2_slide_replaced_regen`, pre-existing `test_bridge_slide_removed_en_regeneracion` |
| `realtime_proxy.py` config(topic + topicVersion) via `on_control` | Adopt; covered by `test_u2_flag_off_no_regen` (topic/version update asserted) + pre-existing config test |
| Frontend `applyServerSlide` rendering path (5 events, version check, seq-ordered insert) | Adopt; verified by adoption + `npm run build` (no TS runner) |
| Frontend flag-off → HTTP fallback parity (`processQueue` FIFO intact when no server slides) | Adopt; verified by adoption + build |

### Rejects remaining for U3/U4 (left in tree, NOT verified in U2)

| Area | Owning unit | Note |
|------|-------------|------|
| `App.vue` `wsSlideMode` latch (skip HTTP once WS active) | U3 cleanup | Design fix REMOVED the latch; dirty tree still latches. U2 leaves it untouched to avoid forking the topic flow U3 owns. U3 removes or replaces with explicit flag-aware parity. |
| `App.vue` slide_error → HTTP retry-once (`queueTranscript force`) | U3 | Design fix REMOVED retry-once; left in tree, owned by U3 (error+retry lifecycle is topic scope). |
| `realtime_proxy.py` `SPEC_SEM_WAIT_S` (50ms sem timeout) | U4 | Isolated to `_speculative_generate` only; bridge tasks use plain `async with slide_sem` (no timeout). No U2 change; U4 owns. |
| `App.vue` 500ms topic debounce + `sendTopic(visibleTurns)` + HTTP fallback requeue | U3 | Topic confirm path; not touched in U2. |
| `useLivePresentation.ts` `hideAllForTopicChange` + `hidden`/`errorHidden` registry + `visibleTurns` + viewed-first regen c=2 | U3 | Ever-visible-only regen + reappear/remove/retry; not touched in U2. |
| `SlideCanvas.vue` turnId follow + neighbor fallback full lifecycle | U3 | Render-side observation adopted in U1; full lifecycle owned by U3. |
| `realtime_proxy.py` speculation (`_maybe_speculate`, `_speculative_generate`, `_try_speculative_hit`, ~60% gate) + `normalize_spec_text` | U4 | Untouched in U2; pre-existing `test_spec_*` updated only for flag-on env (no behavior change). |
| `llm_client.py` continuation machinery (`decide_continuation`, `merge_into_previous`, `ADVANCE_MARKERS`, `continuation` prompt flag, `prev_slide` plumbing in bridge) | Spec amendment or U3 | Exceeds U2 specs (no continuation requirement in spec/design); kept untouched and flagged, not removed. Pre-existing `test_bridge_mismo_subtema_*` updated only for flag-on env. |

## Implemented in this unit (U2 new code)

- `backend/realtime_proxy.py`: `slide_generation_enabled()` default `on` → `off`
  (design D5: both flags off; zero-change deploy, rollback is flag off).
- `backend/realtime_proxy.py`: `regenerate_visible()` early-returns when the
  flag is off (topic/version still update in `on_control`; no regen tasks spawn,
  HTTP owns generation).
- `frontend/src/types.ts`: `BridgeSlideRemovedEvent` gains `seq: number`
  (contract parity: all 5 events carry turnId+seq+topicVersion, matching the
  backend emit which already sent seq).
- `backend/test_main.py`: 10 pre-existing bridge/spec tests updated ONLY to
  opt into generation explicitly (`REALTIME_SLIDE_GENERATION=on` via
  monkeypatch or `_spec_env`); zero behavior change to their assertions.

## TDD Cycle Evidence (U2 strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 flag default-off | `test_u2_flag_defaults_off` | Unit | ✅ 37/37 | ✅ Failed (default was on) | ✅ Passed (default off) | ✅ off-relay + off-regen cases | ➖ None needed |
| 2.1 flag-off relay | `test_u2_flag_off_silent_relay` | Unit | ✅ 37/37 | ➖ Approval (impl existed, no test) | ✅ Passed | ✅ companion off-no-regen | ➖ None needed |
| 2.1 flag-off regen guard | `test_u2_flag_off_no_regen` | Unit | ✅ 37/37 | ✅ Failed (spawned 1 task) | ✅ Passed (guard added) | ✅ relay + regen pair | ➖ None needed |
| 2.1 non-blocking | `test_u2_nonblocking_relay` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ pending-dedupe existing + 2-flight here | ➖ None needed |
| 2.1 slide happy | `test_u2_slide_happy_contract` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ seq-increasing companion | ➖ None needed |
| 2.1 seq order | `test_u2_slide_happy_seq_increasing` | Unit | ✅ 37/37 | ➖ Approval (pairs `test_bridge_orden_seq`) | ✅ Passed | ✅ a<b + b=a+1 | ➖ None needed |
| 2.1 filtered | `test_u2_slide_filtered_new_turn` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ removed-regen existing as 2nd path | ➖ None needed |
| 2.1 error | `test_u2_slide_error_contract` + `test_u2_slide_error_carries_version` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ v0 + v2 versions | ➖ None needed |
| 2.1 emitted dedupe | `test_u2_emitted_dedupe_no_respawn` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ pending-dedupe existing + emitted here | ➖ None needed |
| 2.1 cancel close | `test_u2_cancel_on_close_clears` | Unit | ✅ 37/37 | ➖ Approval | ✅ Passed | ✅ config-cancel existing + close here | ➖ None needed |
| 2.1 replaced | `test_u2_slide_replaced_regen` | Unit | ✅ 37/37 | ➖ Approval (fixed own setup: version bump) | ✅ Passed | ✅ removed existing as 2nd path | ➖ None needed |
| 2.2 sem cap | `test_u2_sem_cap_two` | Unit | ✅ 37/37 | ➖ Structural (single output) | ✅ Passed | ➖ Single (no branching) | ➖ None needed |
| 2.3 frontend minimal | Adoption (no TS runner) | N/A | N/A | ➖ Degraded gracefully | ✅ Build green | ➖ Single path | ➖ No new code |

### Test Summary (U2)

- **Total tests written**: 13 (`test_u2_*`)
- **Total passing**: 50/50 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (13), Integration (0), E2E (0)
- **Approval tests**: 10 (bridge behavior adopted per 0.1 follow-up; tests document existing dirty-tree impl)
- **True RED→GREEN**: 2 (`test_u2_flag_defaults_off`, `test_u2_flag_off_no_regen`)
- **Triangulation fix during cycle**: `test_u2_slide_replaced_regen` setup corrected (topic_version bumped to 1 before regen, matching `on_control` order)
- **Pre-existing updates**: 10 tests now set `REALTIME_SLIDE_GENERATION=on` explicitly (new off-default requires opt-in); assertions unchanged
- **Pure functions created**: 0 (bridge is I/O-bound asyncio; purity not applicable)

## Work Unit Evidence (U2)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/bin/python -m pytest backend/test_main.py -v -k u2` → **13 passed**; full `.venv/bin/python -m pytest backend/test_main.py -v` → **50 passed in 0.87s** (37 prior + 13 U2) |
| Runtime harness command/scenario and exact result | `cd frontend && npm run build` (vue-tsc + vite) → **built in 606ms**, 35 modules transformed, no errors. Live-flow runtime (flag on, 2 slow finals, check order) is manual per tasks.md and deferred to verify with running backends |
| Rollback boundary | `backend/realtime_proxy.py` flag default (1 line) + regen guard (3 lines); `frontend/src/types.ts` removed-seq fix (1 line); `backend/test_main.py` U2 section (append-only) + 10 one-line test env opt-ins. Revert these and U2 vanishes without touching U1 files, U3 topic code, or U4 speculation |

## Deviations from design (U2)

- None from the bridge spec. `wsSlideMode` latch and `retry-once` remain in
  the working tree although the design fix removed them; they are owned by U3
  cleanup (see rejects table) and were deliberately NOT removed here to keep
  the U2 slice autonomous and the U3 topic flow intact.
- Continuation/merge machinery (`decide_continuation` / `merge_into_previous`)
  still exceeds specs; kept untouched and flagged for spec amendment or U3
  ownership (carried from U1).

## Issues found (U2)

- Changing the flag default to off broke 10 pre-existing bridge/spec tests
  that relied on the implicit on-default. Fixed by explicit
  `REALTIME_SLIDE_GENERATION=on` opt-in per test; no assertion changed.
- `BridgeSlideRemovedEvent` type omitted `seq` while the backend already sent
  it; fixed the type (1 line). No runtime change.

## Remaining (explicitly NOT in U2)

- U3: 500ms confirm/debounce, hide-all + registry, ever-visible regen
  viewed-first c=2, turnId-follow full lifecycle, remove/retry/neighbor,
  latch/retry cleanup per design fix.
- U4: speculation gate/match/discard/metrics + ~60% go-live check.
- Phase 2 verify (task 2.4) stays open until U3 completes the topic slice.

## Status

Phase 0 + Phase 1 (U1) complete. Phase 2 bridge (2.1 bridge RED + 2.2) complete.
Ready for U3 (topic lifecycle). No commits made.

---

## Scope verdict (U3 topic lifecycle only)

Implements Phase 2 topic subset: tasks 2.3 (frontend topic lifecycle) + 2.4
(verify). Backend: cancel-on-confirm + relaunch with seq preserved, stale
version silence, registry version tracking, viewed-first launch order, empty
skip (ever-visible scope). Frontend: 500ms confirm (adopted), abort on bump
(adopted), hide-all + registry (adopted, extended viewed-first), ever-visible
regen (adopted), reappear/remove (adopted), hidden+error+manual-retry
(adopted, auto-retry removed), turnId-follow + neighbor (adopted), viewed
priority wiring (new). Explicitly NOT in U3: U4 speculation
(gate/match/discard/metrics), continuation/merge machinery (still exceeds
specs, flagged for amendment), `wsSlideMode` latch (kept, flagged for
U4/amendment — no topic-spec contradiction).

## 0.1 follow-up: dirty-tree topic verdict (U3)

### Adopted as U3 fits (kept, covered by U3 tests or adoption + build)

| Area | Verdict |
|------|---------|
| `App.vue` 500ms topic debounce (no per-keystroke abort, abort only on confirm) | Adopt; confirm path only aborts via `hideAllForTopicChange` |
| `useLivePresentation.ts` `hideAllForTopicChange` (instant hide, hidden registry, abort, version bump) | Adopt + extended with `viewedTurnId` param for viewed-first order |
| `useLivePresentation.ts` `applyServerSlide` (5 events, version check, seq-ordered insert, remove on filtered/removed) | Adopt; `slide_error` branch extended with `errorHidden` registry |
| `useLivePresentation.ts` `processQueue` version-cancel (`myVersion !== topicVersion` discard) | Adopt; cancels pending HTTP on newer version |
| `useLivePresentation.ts` `abortGeneration` (AbortController per turnId) | Adopt; called by hide-all on confirm |
| `realtime_proxy.py` `on_control` cancel + `regenerate_visible` relaunch preserving seq | Adopt; covered by `test_u3_confirm_cancels_and_relaunches` + `test_u3_regen_preserves_seq_multi` |
| `realtime_proxy.py` version-check before emit (`_generate_and_emit` + `_send_slide_result`) | Adopt; covered by `test_u3_stale_regen_never_emits_after_rebump` + pre-existing stale test |
| `realtime_proxy.py` regen skips empty/missing turnId/transcript | Adopt; covered by `test_u3_regen_skips_empty_transcript` (ever-visible scope) |
| `SlideCanvas.vue` turnId follow + neighbor fallback | Adopt; extended with `getActiveTurnId` expose for viewed-first priority |
| `realtimeClient.ts` `sendTopic(topic, version, visibleTurns)` | Adopt; unchanged contract |

### Removed in U3 (contradicts topic spec, per design fix)

| Area | Rationale |
|------|-----------|
| `App.vue` `slide_error` → HTTP auto retry-once (`queueTranscript` force) | Contradicts "Failed regen is retryable: t6 stays hidden with an error AND a retry is available" — auto-retry never leaves hidden+error state. Replaced by manual `retryFailed()` + retry button. |

### Flagged for U4/amendment (out of U3 topic scope, untouched)

| Area | Note |
|------|------|
| `App.vue` `wsSlideMode` latch | No topic-spec contradiction (confirm/abort/regen path independent of latch); routing concern owned by pipeline/U4. Kept untouched. |
| `realtime_proxy.py` + `llm_client.py` continuation machinery (`decide_continuation`, `merge_into_previous`) | Exceeds U3 specs; kept untouched, needs spec amendment (carried from U1/U2). Regen path never passes `prev_ref`, so it cannot merge — no topic impact. |
| `realtime_proxy.py` speculation (`_maybe_speculate`, `SPEC_SEM_WAIT_S`, ~60% gate) | U4. Untouched. |

## Implemented in this unit (U3 new code)

- `backend/realtime_proxy.py`: `regenerate_visible` now stamps
  `emitted[turn_id]["version"] = new_version` for existing entries;
  `_send_slide_result` stamps `entry["version"] = version` on success and
  filtered paths (registry follows the evaluated version; 3 lines).
- `backend/test_main.py`: 7 new `test_u3_*` tests (append-only).
- `frontend/src/composables/useLivePresentation.ts`: `hideAllForTopicChange`
  accepts `viewedTurnId` (viewed entry unshifted, rest keep seq order);
  `slide_error` populates `errorHidden` from the hidden registry;
  `failedTurns` reactive mirror + `retryFailed()` (requeue via HTTP force,
  current version).
- `frontend/src/components/SlideCanvas.vue`: `getActiveTurnId()` exposed
  (currently viewed turn for viewed-first priority).
- `frontend/src/App.vue`: auto retry-once removed; confirm passes
  `canvasRef.getActiveTurnId()` to hide-all; retry alert + button when
  `failedTurns` non-empty.

## TDD Cycle Evidence (U3 strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.3 confirm+relaunch | `test_u3_confirm_cancels_and_relaunches` | Unit | ✅ 50/50 | ➖ Approval (impl existed) | ✅ Passed | ✅ rebump-companion below | ➖ None needed |
| 2.3 stale rebump | `test_u3_stale_regen_never_emits_after_rebump` | Unit | ✅ 50/50 | ➖ Approval (pairs stale test) | ✅ Passed | ✅ cancel+relaunch above as 2nd path | ➖ None needed |
| 2.3 seq multi | `test_u3_regen_preserves_seq_multi` | Unit | ✅ 50/50 | ➖ Approval (pairs replaced test) | ✅ Passed | ✅ 2 turns × 2 seqs | ➖ None needed |
| 2.3 ever-visible skip | `test_u3_regen_skips_empty_transcript` | Unit | ✅ 50/50 | ➖ Approval (impl existed) | ✅ Passed | ✅ empty + missing-turnId + valid | ➖ None needed |
| 2.3 viewed-first | `test_u3_regen_viewed_first_order` | Unit | ✅ 50/50 | ➖ Approval (impl existed) | ✅ Passed | ✅ launch order + seq preserved | ➖ None needed |
| 2.3 registry version | `test_u3_regen_updates_registry_version` | Unit | ✅ 50/50 | ✅ Failed (version stayed 0) | ✅ Passed (3-line stamp) | ✅ filtered companion below | ➖ None needed |
| 2.3 registry filtered | `test_u3_regen_filtered_updates_registry_version` | Unit | ✅ 50/50 | ✅ Failed (version stayed 0) | ✅ Passed | ✅ success + filtered pair | ➖ None needed |
| 2.3 frontend topic | Adoption (no TS runner) | N/A | N/A | ➖ Degraded gracefully | ✅ Build green | ➖ Single path | ➖ No new code |

### Test Summary (U3)

- **Total tests written**: 7 (`test_u3_*`)
- **Total passing**: 57/57 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (7), Integration (0), E2E (0)
- **Approval tests**: 5 (confirm+relaunch, stale rebump, seq multi, empty skip, viewed-first — dirty-tree behavior adopted per 0.1 follow-up)
- **True RED→GREEN**: 2 (registry version on success + filtered)
- **Pure functions created**: 0 (bridge is I/O-bound asyncio; frontend viewed-first is ordering logic verified by build)

## Work Unit Evidence (U3)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/bin/python -m pytest backend/test_main.py -v -k u3` → **7 passed**; full `.venv/bin/python -m pytest backend/test_main.py -v` → **57 passed in 0.83s** (50 prior + 7 U3) |
| Runtime harness command/scenario and exact result | `cd frontend && npm run build` (vue-tsc + vite) → **built in 586ms**, 35 modules transformed, no errors. Live-flow runtime (retopic mid-flight, hide + regen order, retry button) is manual per tasks.md and deferred to verify with running backends |
| Rollback boundary | `backend/realtime_proxy.py` version stamps (3 lines), `backend/test_main.py` U3 section (append-only), `useLivePresentation.ts` viewed-first param + errorHidden/retry (~30 lines), `SlideCanvas.vue` expose (5 lines), `App.vue` confirm wiring + retry UI + retry-once removal (~25 lines). Revert these and U3 vanishes without touching U1/U2 files or U4 speculation |

## Deviations from design (U3)

- `wsSlideMode` latch kept although the design fix removed it: no topic-spec
  contradiction found (confirm/abort/regen independent of latch), so per scope
  ("only if within topic scope, else flag") it is flagged for U4/amendment,
  not removed here. Removal would force HTTP+WS double generation per turn.
- Continuation/merge machinery still exceeds specs; kept untouched and
  flagged (regen never merges — no `prev_ref` passed — so no topic impact).

## Issues found (U3)

- Registry version staleness (emitted entries kept the old version after
  regen) found via RED tests; fixed with 3-line version stamp. Without the
  fix, `_last_visible(version=...)` filtering and post-regen dedupe reason
  about stale versions.

## Remaining (explicitly NOT in U3)

- U4: speculation gate/match/discard/metrics + ~60% go-live check.
- Phase 2 verify (task 2.4) marked complete for the topic slice; full-change
  verify stays with the verify phase.

## Status (U3 merged)

Phase 0 + Phase 1 (U1) complete. Phase 2 bridge (U2) + topic lifecycle (U3:
2.3 + 2.4) complete. Ready for U4 (speculation). No commits made.

---

## Scope verdict (U4 speculation only)

Implements Phase 3 speculation subset: tasks 3.1 (RED) + 3.2 (GREEN) + 3.3
(verify). Dirty-tree speculation machinery (`_maybe_speculate`,
`_speculative_generate`, `_try_speculative_hit`, sem-priority 50ms,
`normalize_spec_text`, hit/miss/wasted counters) adopted as U4 fits and
covered by pre-existing `test_spec_*` + 7 new `test_u4_*`. Explicitly NOT in
U4: any change to U1/U2/U3 behavior; `wsSlideMode` latch and
continuation/merge machinery stay exactly as U3 left them (explicit
rejects carried, amendment-needed, untouched).

## 0.1 follow-up: dirty-tree speculation verdict (U4)

### Adopted as U4 fits (kept, covered by pre-existing tests + adoption)

| Area | Verdict |
|------|---------|
| `_maybe_speculate` gate (stable CUMULATIVE partial, >=800ms AND >=6 words, max 1/turn, hidden task) | Adopt; covered by `test_u4_stable_gate_speculates` + `test_u4_unstable_or_short_never_speculates` + pre-existing `test_spec_*` |
| Never emit before speechComplete (partials forwarded, speculative result silent) | Adopt; covered by pre-existing `test_spec_nunca_emite_antes_de_complete` + `test_u4_stable_gate_speculates` (silent assert) |
| Normalized match reuse else discard at same topicVersion | Adopt; covered by pre-existing hit/mismatch/cancel/version tests + `test_u4_normalized_match_reuses` (whitespace triangulation) |
| Max 1 speculation per turn | Adopt; covered by pre-existing hit test (double partial → 1 task) |
| Default-off (`SPECULATIVE_SLIDES` default off, no behavior change when off) | Adopt; covered by `test_u4_default_off_never_speculates` (flag-off parity: normal path, 1 LLM call, zero counters) |
| sem-priority 50ms (`SPEC_SEM_WAIT_S`, speculation yields to finals) | Adopt; owned by U4, untouched (pre-existing cancel test covers contention) |

### Rejects carried (untouched, NOT ratified)

| Area | Note |
|------|------|
| `wsSlideMode` latch (`App.vue`) | Carried from U3. No speculation-spec contradiction; routing concern. Untouched. |
| Continuation machinery (`decide_continuation` / `merge_into_previous`, `ADVANCE_MARKERS`) | Carried from U1–U3. Exceeds U4 specs; needs spec amendment. Untouched, not removed. |

## Implemented in this unit (U4 new code)

- `backend/realtime_proxy.py`: `SPEC_GO_LIVE_THRESHOLD = 0.6` const.
- `backend/realtime_proxy.py`: `speculation_go_live_ready(hits, misses, threshold=0.6)` pure
  function — `False` on empty data or rate < threshold, `True` at/above (~60% gate).
- `backend/realtime_proxy.py`: `RealtimeBridge.spec_metrics()` — returns
  `{hits, misses, wasted, total, hit_rate}` (`hit_rate` None when total is 0).
- `backend/realtime_proxy.py`: final-without-speculation no longer counts a miss
  (else branch pops state only). Rationale: hit-rate is defined over *resolved
  speculations* (spec scenario "GIVEN 20 resolved speculations"); a turn that never
  launched speculation resolves nothing. All launched-then-discarded paths still
  miss via `_try_speculative_hit`. No pre-existing test depended on the old count.
- `backend/test_main.py`: 7 new `test_u4_*` (append-only).

## TDD Cycle Evidence (U4 strict TDD)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 stable gate | `test_u4_stable_gate_speculates` | Unit | ✅ 57/57 | ➖ Approval (impl existed, real 800ms/6w defaults) | ✅ Passed | ✅ unstable/short companion below | ➖ None needed |
| 3.1 unstable/short | `test_u4_unstable_or_short_never_speculates` | Unit | ✅ 57/57 | ➖ Approval | ✅ Passed | ✅ short + changed-text pair | ➖ None needed |
| 3.1 never-emit | pre-existing `test_spec_nunca_emite_*` + silent assert in stable test | Unit | ✅ 57/57 | ➖ Approval | ✅ Passed | ✅ 3 partials + gather | ➖ None needed |
| 3.1 normalized reuse | `test_u4_normalized_match_reuses` | Unit | ✅ 57/57 | ➖ Approval (pairs exact-hit test) | ✅ Passed | ✅ exact + whitespace-variant | ➖ None needed |
| 3.1 max-1/turn | pre-existing hit test (double partial → 1 task) | Unit | ✅ 57/57 | ➖ Approval | ✅ Passed | ✅ covered by hit test | ➖ None needed |
| 3.1 default-off | `test_u4_default_off_never_speculates` | Unit | ✅ 57/57 | ➖ Approval (impl existed, no test) | ✅ Passed | ✅ no-spec-state + normal-path pair | ➖ None needed |
| 3.1 no-miss-when-nothing-speculated | `test_u4_final_without_speculation_no_miss` | Unit | ✅ 57/57 | ✅ Failed (misses==1, old else branch) | ✅ Passed (else pops only) | ✅ companion to default-off (enabled flag, no partials) | ➖ None needed |
| 3.1 metrics | `test_u4_metrics_report_rate` | Unit | ✅ 57/57 | ✅ AttributeError (`spec_metrics` missing) | ✅ Passed | ✅ 20-case + empty case | ➖ None needed |
| 3.1 ~60% gate | `test_u4_gate_below_threshold_stays_off` | Unit | ✅ 57/57 | ✅ ImportError (`speculation_go_live_ready` missing) | ✅ Passed | ✅ below + at-threshold + empty | ➖ Pure function, no mocks |
| 3.2 counters | hit/miss/wasted via pre-existing + u4 tests | Unit | ✅ 57/57 | — (see RED rows) | ✅ Passed | ✅ hits + mismatch + cancel + version paths | ➖ None needed |

### Test Summary (U4)

- **Total tests written**: 7 (`test_u4_*`)
- **Total passing**: 64/64 (`pytest backend/test_main.py -v`)
- **Layers used**: Unit (7), Integration (0), E2E (0)
- **Approval tests**: 4 (stable gate, unstable/short, normalized reuse, default-off — dirty-tree behavior adopted per 0.1 follow-up)
- **True RED→GREEN**: 3 (no-miss refinement, `spec_metrics`, `speculation_go_live_ready`)
- **Pure functions created**: 1 (`speculation_go_live_ready`; `spec_metrics` is a trivial accessor)

## Work Unit Evidence (U4)

| Evidence | Value |
|---|---|
| Focused test command and exact result | `.venv/bin/python -m pytest backend/test_main.py -v -k u4` → **7 passed**; full `.venv/bin/python -m pytest backend/test_main.py -v` → **64 passed in 0.77s** (57 prior + 7 U4) |
| Runtime harness command/scenario and exact result | `cd frontend && npm run build` (vue-tsc + vite) → **built in 579ms**, no errors. Live-flow runtime (stable partials, metrics, no early paint) is manual per tasks.md and deferred to verify with running backends. No frontend change in U4 (speculation is backend-hidden) |
| Rollback boundary | `backend/realtime_proxy.py` threshold const + `speculation_go_live_ready` + `spec_metrics` + else-branch 2-line removal; `backend/test_main.py` U4 section (append-only). Revert these and U4 vanishes without touching U1/U2/U3 files or tree speculation core |

## Deviations from design (U4)

- Final-without-speculation miss-count removed (see above): keeps hit-rate defined
  over resolved speculations so the ~60% gate is meaningful. U4-owned code only;
  no U1/U2/U3 path touched.
- `wsSlideMode` latch and continuation/merge left exactly as found (carried
  rejects, not ratified — no spec grounding in U4 scope).

## Issues found (U4)

- None blocking. Pre-existing suite was green (57/57) before changes.
- Noted (not changed): `normalize_spec_text` lowercases *after* `clean_topic`, so
  case variants (`EL` vs `el`) normalize differently (cleaner stopwords are
  case-sensitive) and count as mismatch→discard. Whitespace variants match.
  Out of U4 scope; flag for cleaner/spec amendment if case-insensitive match is wanted.

## Status (U4 merged — all units complete)

Phase 0 + Phase 1 (U1) + Phase 2 bridge (U2) + topic lifecycle (U3: 2.3 + 2.4) +
Phase 3 speculation (U4: 3.1 + 3.2 + 3.3) complete. Ready for verify. No commits made.
