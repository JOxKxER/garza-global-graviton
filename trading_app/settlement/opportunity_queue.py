"""Opportunity queue: while capital is locked/settling, the probability
engine keeps scanning and ranking candidate trades here so the highest-alpha
staged opportunity can execute the moment buying power frees up, instead of
re-scanning from scratch after every settlement event.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..analytics.probability_engine import Signal


@dataclass(order=True)
class _QueueEntry:
    sort_key: float
    seq: int
    opportunity: "StagedOpportunity" = field(compare=False)


@dataclass
class StagedOpportunity:
    symbol: str
    signal: Signal
    notional_required: float
    staged_at: datetime

    @property
    def alpha_score(self) -> float:
        """Ranking score: probability-weighted edge magnitude. Higher is
        more attractive. Deliberately simple/transparent -- swap this out
        for a fancier scoring function if you have one you trust."""
        return abs(self.signal.edge) * self.signal.probability


class OpportunityQueue:
    def __init__(self, max_staleness_seconds: float = 300.0):
        self.max_staleness_seconds = max_staleness_seconds
        self._heap: List[_QueueEntry] = []
        self._counter = itertools.count()

    def stage(self, opportunity: StagedOpportunity) -> None:
        # heapq is a min-heap; negate the score so the highest alpha pops first.
        entry = _QueueEntry(sort_key=-opportunity.alpha_score, seq=next(self._counter), opportunity=opportunity)
        heapq.heappush(self._heap, entry)

    def _prune_stale(self, now: datetime) -> None:
        fresh = [
            e for e in self._heap
            if (now - e.opportunity.staged_at).total_seconds() <= self.max_staleness_seconds
        ]
        if len(fresh) != len(self._heap):
            heapq.heapify(fresh)
            self._heap = fresh

    def pop_best_affordable(self, now: datetime, available_buying_power: float) -> Optional[StagedOpportunity]:
        """Pops and returns the highest-alpha opportunity that fits within
        available_buying_power, discarding any stale entries encountered
        along the way (a stale signal must be re-validated by the caller
        before acting on it, not executed blindly once cash frees up)."""
        self._prune_stale(now)
        skipped: List[_QueueEntry] = []
        result: Optional[StagedOpportunity] = None
        while self._heap:
            entry = heapq.heappop(self._heap)
            if (now - entry.opportunity.staged_at).total_seconds() > self.max_staleness_seconds:
                continue  # drop stale entry entirely
            if entry.opportunity.notional_required <= available_buying_power:
                result = entry.opportunity
                break
            skipped.append(entry)
        for entry in skipped:
            heapq.heappush(self._heap, entry)
        return result

    def __len__(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
