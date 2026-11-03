# Topic Versioning Specification

## Purpose

Make topic changes feel instant and safe: hide on confirm, cancel stale work, and regenerate only ever-visible slides in original order under a new version.

## Requirements

### Requirement: Debounced Confirm

The system MUST confirm a topic change only after 500ms without further typing, bumping topicVersion exactly once per confirm.

#### Scenario: Typing pause confirms once

- GIVEN keystrokes then 500ms of silence
- WHEN the debounce elapses
- THEN exactly one confirm fires with topicVersion incremented by one

#### Scenario: Continuous typing never confirms

- GIVEN keystrokes less than 500ms apart
- WHEN time passes
- THEN no confirm fires AND topicVersion is unchanged

### Requirement: Confirm Cancels In-Flight Work

The system MUST cancel in-flight generations (frontend abort and backend task cancel) and drop queued-but-unstarted work for the old version on confirm.

#### Scenario: Old-version result is discarded

- GIVEN a generation for version 1 still running
- WHEN version 2 is confirmed
- THEN the task is cancelled AND a late version-1 result is never emitted or painted

### Requirement: Instant Hide With Registry

The system MUST hide all visible slides instantly on confirm and MUST record each in an internal registry keyed by turnId with seq, transcript, and version.

#### Scenario: Confirm hides everything at once

- GIVEN three visible slides
- WHEN the topic is confirmed
- THEN zero slides are visible AND the registry holds all three entries

### Requirement: Ordered Background Regeneration

The system MUST relaunch finals for registry entries under the new version, MUST preserve original seq positions, MUST cap concurrency at 2 with viewed-first priority, and MUST check version before emitting.

#### Scenario: Regen keeps order

- GIVEN registry entries with seq 1 to 3
- WHEN regeneration completes out of order
- THEN slides reappear in seq order

### Requirement: Outcome Handling Per Slide

The system MUST reappear a slide in seq position when relevant, MUST remove it when filtered, and MUST keep it hidden with an error plus retry affordance when generation fails.

#### Scenario: Filtered regen removes

- GIVEN a filtered regen result for `t5`
- WHEN applied
- THEN no slide for `t5` exists AND the order of the rest is intact

#### Scenario: Failed regen is retryable

- GIVEN a regen that raises for `t6`
- WHEN applied
- THEN `t6` stays hidden with an error AND a retry is available

### Requirement: Canvas Follows turnId

The canvas MUST track the active slide by turnId rather than index, so replace and remove operations keep position and never steal focus from a user navigating back.

#### Scenario: Removal keeps position

- GIVEN the user viewing `t2` of three slides
- WHEN `t2` is removed by regen
- THEN the view moves to the neighbor at that position, not to the latest

### Requirement: Ever-Visible Scope

The system MUST reevaluate ONLY slides visible at confirm time; turns that never produced a visible slide MUST NOT be regenerated.

#### Scenario: Never-visible turn is skipped

- GIVEN a past turn that was filtered and never painted
- WHEN a topic is confirmed
- THEN no regeneration runs for that turn

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented versioning
- WHEN the backend suite and frontend build run
- THEN both exit zero
