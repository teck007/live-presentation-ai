# Delta for speculative-slides

## MODIFIED Requirements

### Requirement: Never Emit Before speechComplete

The system MUST NOT emit any slide event from speculation or from any WS async task before the matching speechComplete arrives and passes the `seq` ordering gate.

(Previously: speculation-only silence rule with no WS async coverage.)

#### Scenario: Early result stays silent

- GIVEN a finished speculative result for `t1` with no final yet
- WHEN the result resolves
- THEN zero slide events are sent for `t1`

#### Scenario: WS task without final emits nothing

- GIVEN a WS task resolving before its speechComplete is recorded
- WHEN the emit gate is evaluated
- THEN no `slide` event is sent

### Requirement: Default Off

Speculation MUST be disabled by default and enabled only via explicit configuration; the WS async path MUST NOT start speculative tasks while the flag is off.

(Previously: default-off with no WS async interaction stated.)

#### Scenario: Default session never speculates

- GIVEN default configuration and stable partials
- WHEN partials arrive
- THEN no speculative task starts

#### Scenario: WS path stays non-speculative

- GIVEN the WS async flag on with speculation still default-off
- WHEN a stable partial arrives
- THEN only the final-driven task path may run
