"""TurnId-keyed live latency baseline (U1, change live-latency).

Local-clock records for the live path: speechComplete received, LLM
request start/end, and slide paint. Paint is observed at render with the
local clock (no new wire contract); the backend store aggregates the
spans it can observe and computes p50/p95 over a sliding window of
approximately 20 completed phrases.

All methods are no-raise by contract: instrumentation must never break
the live slide pipeline, so empty turnIds are ignored silently.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

#: Completed-phrase window for p50/p95 aggregation (~20 per spec).
BASELINE_WINDOW = 20


@dataclass
class LatencyRecord:
    """Four ordered timestamps for one final turn, plus filter marker."""

    turn_id: str
    complete_at: float | None = None
    llm_start: float | None = None
    llm_end: float | None = None
    paint_at: float | None = None
    filtered: bool = False

    def as_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "complete_at": self.complete_at,
            "llm_start": self.llm_start,
            "llm_end": self.llm_end,
            "paint_at": self.paint_at,
            "filtered": self.filtered,
        }


class LatencyStore:
    """In-memory turnId store with p50/p95 over the last ``window`` paints."""

    def __init__(self, window: int = BASELINE_WINDOW) -> None:
        self._window = max(1, window)
        self._records: dict[str, LatencyRecord] = {}

    @property
    def count(self) -> int:
        return len(self._records)

    def _touch(self, turn_id: object) -> LatencyRecord | None:
        tid = (str(turn_id) if turn_id is not None else "").strip()
        if not tid:
            return None
        rec = self._records.get(tid)
        if rec is None:
            rec = LatencyRecord(turn_id=tid)
            self._records[tid] = rec
        return rec

    def record_complete(self, turn_id: object, ts: float) -> None:
        rec = self._touch(turn_id)
        if rec is not None:
            rec.complete_at = ts

    def record_llm_start(self, turn_id: object, ts: float) -> None:
        rec = self._touch(turn_id)
        if rec is not None:
            rec.llm_start = ts

    def record_llm_end(self, turn_id: object, ts: float) -> None:
        rec = self._touch(turn_id)
        if rec is not None:
            rec.llm_end = ts

    def record_paint(self, turn_id: object, ts: float) -> None:
        rec = self._touch(turn_id)
        if rec is not None:
            rec.paint_at = ts

    def mark_filtered(self, turn_id: object) -> None:
        rec = self._touch(turn_id)
        if rec is not None:
            rec.filtered = True

    def get(self, turn_id: object) -> dict | None:
        tid = (str(turn_id) if turn_id is not None else "").strip()
        if not tid:
            return None
        rec = self._records.get(tid)
        return rec.as_dict() if rec is not None else None

    def end_to_end(self, turn_id: object) -> float | None:
        """speechComplete-to-paint seconds, or None when paint is missing."""
        rec = self.get(turn_id)
        if rec is None or rec["paint_at"] is None or rec["complete_at"] is None:
            return None
        return rec["paint_at"] - rec["complete_at"]

    def durations(self) -> list[float]:
        """End-to-end durations of painted turns, oldest first, window-capped."""
        out: list[float] = []
        for rec in self._records.values():
            if rec.paint_at is not None and rec.complete_at is not None:
                out.append(rec.paint_at - rec.complete_at)
        return out[-self._window :]

    def summary(self) -> dict:
        """p50/p95 over the window; provisional when fewer than ``window``."""
        data = self.durations()
        n = len(data)
        if not data:
            return {"n": 0, "p50": None, "p95": None, "provisional": True}
        ordered = sorted(data)
        p50 = statistics.median(ordered)
        rank = max(1, math.ceil(0.95 * n))
        p95 = ordered[min(rank, n) - 1]
        return {
            "n": n,
            "p50": p50,
            "p95": p95,
            "provisional": n < self._window,
        }


#: Process-wide baseline store (window ~20). Import and record; never gate.
baseline = LatencyStore(window=BASELINE_WINDOW)
