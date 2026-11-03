# Speculative Slides Specification

## Purpose

Optionally pre-generate slides on stable cumulative partials to cut perceived latency, without ever showing unconfirmed content. Default off; go-live requires meeting the hit-rate gate.

## Requirements

### Requirement: Stability Gate for Hidden Speculation

The system MUST speculate only on cumulative partials unchanged for at least 800ms AND containing at least 6 words.

#### Scenario: Stable partial speculates

- GIVEN the same cumulative partial for 800ms with 8 words
- WHEN the gate is evaluated
- THEN one hidden generation starts

#### Scenario: Unstable or short partial never speculates

- GIVEN partials changing within 800ms or under 6 words
- WHEN the gate is evaluated
- THEN no generation starts

### Requirement: Never Emit Before speechComplete

The system MUST NOT emit any slide event from speculation or from any WS async task before the matching speechComplete arrives and passes the `seq` ordering gate.

#### Scenario: Early result stays silent

- GIVEN a finished speculative result for `t1` with no final yet
- WHEN the result resolves
- THEN zero slide events are sent for `t1`

#### Scenario: WS task without final emits nothing

- GIVEN a WS task resolving before its speechComplete is recorded
- WHEN the emit gate is evaluated
- THEN no `slide` event is sent

### Requirement: Normalized Match Reuse Else Discard

The system MUST reuse the speculative result only when its normalized text exactly matches the normalized final at the same topicVersion; otherwise it MUST discard it and generate normally.

#### Scenario: Exact match reuses with no second LLM call

- GIVEN a completed speculation whose normalized key equals the final's
- WHEN speechComplete arrives
- THEN the stored result is emitted with no additional LLM call

#### Scenario: Mismatch discards and regenerates

- GIVEN a completed speculation whose normalized text differs from the final
- WHEN speechComplete arrives
- THEN the stored result is discarded AND a normal generation runs

### Requirement: At Most One Speculation Per Turn

The system MUST launch at most one speculative generation per turnId.

#### Scenario: Repeated stable evaluations launch once

- GIVEN two identical stable evaluations for `t1`
- WHEN both pass the gate
- THEN exactly one speculative task exists for `t1`

### Requirement: Default Off

Speculation MUST be disabled by default and enabled only via explicit configuration; the WS async path MUST NOT start speculative tasks while the flag is off.

#### Scenario: Default session never speculates

- GIVEN default configuration and stable partials
- WHEN partials arrive
- THEN no speculative task starts

#### Scenario: WS path stays non-speculative

- GIVEN the WS async flag on with speculation still default-off
- WHEN a stable partial arrives
- THEN only the final-driven task path may run

### Requirement: Hit-Rate Metrics and Go-Live Gate

The system MUST track speculation hits, misses, and wasted LLM calls, and the feature MUST stay off by default until measured hit-rate reaches approximately 60%.

#### Scenario: Twenty speculations report a rate

- GIVEN 20 resolved speculations
- WHEN metrics are read
- THEN hits, misses, wasted counts, and the hit-rate are reported

#### Scenario: Gate below threshold keeps default off

- GIVEN a measured hit-rate below approximately 60%
- WHEN go-live is evaluated
- THEN speculation remains default-off

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented speculation
- WHEN the backend suite and frontend build run
- THEN both exit zero
