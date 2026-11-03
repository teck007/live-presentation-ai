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

The system MUST run each generation as a non-blocking asyncio task reusing the shared AsyncOpenAI prompt, parse, and fallback logic.

#### Scenario: Slow LLM never blocks relay

- GIVEN a generation in flight for `t1`
- WHEN new realtime events arrive
- THEN they are relayed without waiting for `t1`

### Requirement: Concurrency Cap and Sequence Ordering

The system MUST cap concurrent generations with a semaphore of 2 and MUST assign increasing sequence numbers in arrival order so the frontend can restore order.

#### Scenario: Out-of-order completion restores order

- GIVEN `a` (seq 1) completing after `b` (seq 2)
- WHEN the frontend applies both events
- THEN `a` appears before `b`

### Requirement: Versioned Slide Event Contract

The system MUST emit `slide`, `slide_filtered`, or `slide_error` for new turns and `slide_replaced` or `slide_removed` for regenerations, each carrying turnId, seq, and topicVersion.

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

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented bridge generation
- WHEN the backend suite and frontend build run
- THEN both exit zero
