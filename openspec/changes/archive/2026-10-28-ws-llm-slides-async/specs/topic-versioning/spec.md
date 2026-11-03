# Delta for topic-versioning

## MODIFIED Requirements

### Requirement: Confirm Cancels In-Flight Work

The system MUST cancel in-flight generations (frontend abort and backend task cancel, including WS `create_task` handles) and drop queued-but-unstarted work for the old version on confirm; any WS task whose `topicVersion` no longer matches current MUST be dropped at the pre-emit check with no event sent.

(Previously: cancelled frontend/backend work with no explicit WS pre-emit rule.)

#### Scenario: Old-version result is discarded

- GIVEN a generation for version 1 still running
- WHEN version 2 is confirmed
- THEN the task is cancelled AND a late version-1 result is never emitted or painted

#### Scenario: Finished-but-stale task emits nothing

- GIVEN a WS task for version 1 finishing after the bump to version 2
- WHEN its pre-emit check runs
- THEN no `slide` event is emitted

## ADDED Requirements

### Requirement: Pre-Paint Version Guard

The frontend MUST compare each arriving `slide` event's `topicVersion` against current before painting, and MUST discard stale events even if they passed the server check.

#### Scenario: Late event never paints

- GIVEN a `slide` for version 1 arriving after confirm of version 2
- WHEN the paint guard evaluates it
- THEN nothing is painted AND order of current slides is unchanged
