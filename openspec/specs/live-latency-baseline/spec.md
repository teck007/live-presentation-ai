# Live Latency Baseline Specification

## Purpose

Establish the turnId-keyed latency baseline from speechComplete to painted slide, so later phases prove improvement with p50/p95 over approximately 20 phrases.

## Requirements

### Requirement: TurnId-Keyed Latency Timestamps

The system MUST record, keyed by turnId, timestamps for speechComplete received, LLM request start, LLM response end, and slide paint.

#### Scenario: Full pipeline yields four ordered timestamps

- GIVEN a final transcript with turnId `t1`
- WHEN the turn flows through generation to a painted slide
- THEN one record exists for `t1` with all four timestamps in non-decreasing order

#### Scenario: Filtered turn records no paint timestamp

- GIVEN a final transcript the LLM marks filtered
- WHEN generation completes without painting
- THEN the record holds the first three timestamps plus an explicit filtered marker

#### Scenario: Missing turnId never breaks the pipeline

- GIVEN a final event without a turnId
- WHEN generation runs
- THEN no baseline record is written AND the slide pipeline proceeds normally

### Requirement: p50/p95 Aggregation Over Sample Window

The system MUST compute p50 and p95 end-to-end latency (speechComplete to paint) over a window of approximately 20 completed phrases.

#### Scenario: Twenty phrases yield p50 and p95

- GIVEN 20 completed phrase records with end-to-end durations
- WHEN aggregation runs
- THEN it reports p50 and p95 derived from exactly those durations

#### Scenario: Partial window reports provisional values

- GIVEN fewer than 20 completed records
- WHEN aggregation runs
- THEN it reports statistics flagged as incomplete rather than failing

### Requirement: Extended LLM Log Line

The system MUST extend the `[llm]` log with turnId, topicVersion, block count, and elapsed seconds on every outcome (success, filtered, fallback).

#### Scenario: Success logs identity and duration

- GIVEN a completed LLM call for turnId `t1` at topicVersion 3
- WHEN the call returns
- THEN one `[llm]` line contains `t1`, version 3, block count, and elapsed time

#### Scenario: Fallback logs the cause

- GIVEN an LLM call that raises
- WHEN the fallback slide is returned
- THEN one `[llm]` line records the turnId and the failure cause

### Requirement: Acceptance Verification

This capability MUST be verified by `pytest backend/test_main.py -v` and `cd frontend && npm run build` passing with no new failures.

#### Scenario: Green suite and build

- GIVEN the implemented baseline
- WHEN the backend suite and frontend build run
- THEN both exit zero
