# Delta for live-generation-pipeline

## MODIFIED Requirements

### Requirement: Single-Concurrency FIFO With Dedupe

The system MUST process final turns through a FIFO queue with concurrency 1 only when the WS async path is flag-off, MUST skip turns whose turnId was already sent, MUST skip turns duplicating the last sent text, and MUST preserve arrival order for the rest.

(Previously: FIFO-1 always active regardless of WS flag.)

#### Scenario: Queued turns keep arrival order

- GIVEN final `a` generating while final `b` arrives
- WHEN both are queued
- THEN `a` completes before `b` starts AND slides appear in arrival order

#### Scenario: Duplicates are dropped without LLM calls

- GIVEN turnId `t1` already sent, then `t1` again and a new turnId with identical text
- WHEN each arrives
- THEN both repeats are dropped with no LLM call

## ADDED Requirements

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
