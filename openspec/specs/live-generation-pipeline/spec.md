# Live Generation Pipeline Specification

## Purpose

Shrink trigger-to-slide latency on the HTTP path: generate on final-transcript arrival with a single-concurrency FIFO, a smaller LLM budget, a cheap prefilter, and topicVersion plumbing. No provisional slide is ever painted.

## Requirements

### Requirement: Immediate Trigger on Final Transcript

The system MUST start generation when a final transcript arrives, with no debounce delay.

#### Scenario: Final arrival starts generation at once

- GIVEN a final transcript with turnId `t1`
- WHEN the final event is received
- THEN generation for `t1` starts without waiting for further silence or timers

### Requirement: Single-Concurrency FIFO With Dedupe

The system MUST process final turns through a FIFO queue with concurrency 1 only when the WS async path is flag-off, MUST skip turns whose turnId was already sent, MUST skip turns duplicating the last sent text, and MUST preserve arrival order for the rest.

#### Scenario: Queued turns keep arrival order

- GIVEN final `a` generating while final `b` arrives
- WHEN both are queued
- THEN `a` completes before `b` starts AND slides appear in arrival order

#### Scenario: Duplicates are dropped without LLM calls

- GIVEN turnId `t1` already sent, then `t1` again and a new turnId with identical text
- WHEN each arrives
- THEN both repeats are dropped with no LLM call

### Requirement: Reduced Token Budget With Truncation

The system MUST cap LLM output at approximately 220 tokens per call and MUST fold over-long transcripts into bounded blocks that still yield exactly one slide, signaling when content was folded.

#### Scenario: Long turn yields one bounded slide

- GIVEN a transcript exceeding the block limit
- WHEN generation runs
- THEN exactly one slide is produced AND folding is signaled

### Requirement: Cheap Prefilter Before the LLM

The system SHOULD apply the `topic_cleaner` prefilter to drop empty, greeting-only, or filler-only transcripts before calling the LLM, while the LLM remains authoritative for semantic relevance.

#### Scenario: Filler is filtered with no LLM call

- GIVEN a final transcript with only greetings or fillers
- WHEN the pipeline receives it
- THEN a filtered response returns without invoking the LLM

#### Scenario: Semantic edge cases reach the LLM

- GIVEN a short but meaningful transcript passing the prefilter
- WHEN the pipeline receives it
- THEN the LLM decides relevance

### Requirement: POST Contract With Fallback and topicVersion

The system MUST send `turn_id` and `topic_version` on POST /api/presentations/generate, MUST trim oversized fields instead of rejecting them, and MUST return a fallback slide when the LLM fails so the live flow never breaks.

#### Scenario: LLM outage still yields a slide

- GIVEN a valid final transcript while the LLM raises
- WHEN POST is called
- THEN a fallback slide response returns

#### Scenario: Oversized payload is trimmed, not rejected

- GIVEN a transcript or topic exceeding length limits
- WHEN POST is called
- THEN the request succeeds with trimmed fields instead of a 422

### Requirement: No Provisional Paints

The system MUST NOT paint any slide before its generation result arrives, and MUST show only the Generating indicator while work is in flight.

#### Scenario: In-flight turn shows indicator only

- GIVEN final `t1` still generating
- WHEN the UI renders
- THEN no slide for `t1` is visible AND the Generating indicator is shown

### Requirement: Flag-Off HTTP Fallback Only

The system MUST route `POST /api/presentations/generate` generation only when the WS flag is off, and MUST NOT run HTTP and WS producers for the same turn simultaneously.

#### Scenario: Flag off restores HTTP path

- GIVEN the flag off and a final transcript with no server slide events
- WHEN the frontend queue runs
- THEN the HTTP queue generates the slide

#### Scenario: Flag on suppresses HTTP

- GIVEN the flag on and a WS `slide_pending` received for `t1`
- WHEN the frontend queue sees `t1`
- THEN no POST is sent for `t1`

### Requirement: Keyword Derivation Unchanged on HTTP Fallback

The system MUST keep HTTP fallback keyword derivation unchanged (request keywords or `analyze_topic`-derived) and MUST NOT apply the WS session-plus-event merge to the HTTP path; on the WS path the session topic is authoritative and session plus event keywords are merged.

#### Scenario: HTTP fallback ignores WS merge

- GIVEN the flag off and a final transcript with no session topic
- WHEN the HTTP fallback runs
- THEN keywords come from the request or `analyze_topic`, not from any WS merge

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented pipeline
- WHEN the backend suite and frontend build run
- THEN both exit zero
