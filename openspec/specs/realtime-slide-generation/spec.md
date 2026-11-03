# Realtime Slide Generation Specification

## Purpose

Move slide generation into the realtime bridge as non-blocking background tasks with ordered, versioned events, keeping the HTTP pipeline as fallback when the flag is off.

## Requirements

### Requirement: Topic and Flag Configuration

The system MUST accept session topic plus topicVersion through config events, and MUST run server-side generation only when the slide-generation flag is on.

#### Scenario: Flag off means silent relay

- GIVEN the flag off and a speechComplete event
- WHEN the bridge relays it
- THEN no generation task starts AND no slide events are emitted

### Requirement: Non-Blocking Shared Generation Tasks

The system MUST run each non-empty generation as a non-blocking `asyncio.create_task` that calls `to_thread(generate_slide)` with the session topic and merged keywords, reusing the shared prompt, parse, and fallback logic. Only transcripts shorter than 3 characters after trimming MUST short-circuit to `slide_filtered` without calling the LLM; every other transcript MUST reach the LLM and only the model decides relevance. When the session topic is empty the model MUST run in free mode; when set it MUST apply the strict semantic filter.

#### Scenario: Slow LLM never blocks relay

- GIVEN a generation in flight for `t1`
- WHEN new realtime events arrive
- THEN they are relayed without waiting for `t1`

#### Scenario: Empty transcript short-circuits without LLM

- GIVEN a final transcript shorter than 3 characters after trimming
- WHEN the bridge evaluates it
- THEN no task is spawned AND a silent `slide_filtered` is recorded with no LLM call

#### Scenario: Off-topic reaches the model when a topic is set

- GIVEN a session topic set and a final transcript on another topic
- WHEN the bridge evaluates it
- THEN a task is spawned with the session topic and merged keywords AND `slide_filtered` is emitted only if the model returns `relevant=false`

#### Scenario: Free mode without session topic

- GIVEN an empty session topic and a non-empty final transcript
- WHEN the bridge evaluates it
- THEN a task is spawned AND the model returns `relevant=true`

### Requirement: Concurrency Cap and Sequence Ordering

The system MUST cap concurrent generations with a `Semaphore(2)` and MUST assign increasing `seq` numbers in arrival order; the frontend MUST restore order by `seq` and discard late completions that break it.

#### Scenario: Out-of-order completion restores order

- GIVEN `a` (seq 1) completing after `b` (seq 2)
- WHEN the frontend applies both events
- THEN `a` appears before `b`

#### Scenario: Third arrival waits for a slot

- GIVEN two generations holding the semaphore
- WHEN a third eligible final arrives
- THEN it waits without blocking relay until a slot frees

### Requirement: Versioned Slide Event Contract

The system MUST emit `slide_pending` on task spawn, then exactly one of `slide`, `slide_filtered`, or `slide_error` for new turns (or `slide_replaced` / `slide_removed` for regens), each carrying mandatory `turnId`, `seq`, and `topicVersion`; `slide_filtered` MUST stay silent in UI and visible only in logs; any result whose `topicVersion` is stale MUST be dropped before emit.

#### Scenario: Pending announces work

- GIVEN an eligible final `t1` assigned seq 4 at version 2
- WHEN the task is spawned
- THEN a `slide_pending` with `t1`, seq 4, version 2 is emitted

#### Scenario: Filtered regeneration removes the slide

- GIVEN a filtered regeneration result for `t5` at version 2
- WHEN the bridge emits
- THEN the event is `slide_removed` with turnId `t5` and version 2

#### Scenario: Stale version never emits

- GIVEN a result computed for version 1 after the session moved to version 2
- WHEN the task finishes
- THEN nothing is emitted

### Requirement: Server-Side TurnId Dedupe

The system MUST start at most one generation task per turnId and MUST ignore repeat finals for already-emitted turns.

#### Scenario: Duplicate final spawns nothing

- GIVEN turnId `t1` already emitted or in flight
- WHEN the same speechComplete arrives again
- THEN no new task is created

### Requirement: Cancel on Close

The system MUST cancel all pending generation and speculation tasks when the frontend connection closes.

#### Scenario: Close cancels work

- GIVEN tasks in flight for `t1` and `t2`
- WHEN the connection closes
- THEN both tasks are cancelled AND no further events are sent

### Requirement: HTTP Fallback When Flag Is Off

The system MUST keep the HTTP generation queue fully functional when server-side generation is off, so disabling the flag restores prior behavior.

#### Scenario: Flag off restores HTTP path

- GIVEN the flag off and a final transcript
- WHEN the frontend receives it with no server slide events
- THEN the HTTP queue generates the slide

### Requirement: Text-Only First Slice

The system MUST produce text-only content in this slice; image and media fields MUST be absent or empty.

#### Scenario: First slice has no media

- GIVEN any successful generation in this slice
- WHEN the `slide` event is emitted
- THEN it carries title and bullets only with no image payload

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented bridge generation
- WHEN the backend suite and frontend build run
- THEN both exit zero
