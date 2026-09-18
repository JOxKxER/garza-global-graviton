"""Tautochrone-derived priority scheduler for isochronous task execution.

Tactical use: the cycloid's tautochrone property -- every starting point
on the curve reaches the bottom in the same time T = pi*sqrt(r/g),
regardless of release height -- is used here as a deterministic,
closed-form mapping from a task's "urgency radius" r to a fixed
per-tier execution time quantum, so time-slice length comes from a
single tunable physical parameter rather than an arbitrary constant.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from itertools import count

STANDARD_GRAVITY_M_S2 = 9.80665


@dataclass(order=True)
class ScheduledTask:
    """A task ordered by its cycloid-derived priority key."""

    priority_key: tuple[float, int]
    task_id: str = field(compare=False)
    time_quantum_seconds: float = field(compare=False)


class TautochronePriorityScheduler:
    """Priority scheduler using tautochrone descent time as tier quantum."""

    def __init__(self, gravity: float = STANDARD_GRAVITY_M_S2) -> None:
        """Set the gravitational constant g used in the descent formula."""
        self.gravity = gravity
        self._heap: list[ScheduledTask] = []
        self._counter = count()

    def calc_descent_time(self, urgency_radius: float) -> float:
        """Evaluate T = pi * sqrt(r / g), the tautochrone descent time.

        Tactical advantage: gives every priority tier a deterministic,
        closed-form time quantum derived from a single tunable radius,
        instead of an arbitrary per-tier constant.
        """
        if urgency_radius <= 0:
            raise ValueError("urgency_radius must be positive")
        return math.pi * math.sqrt(urgency_radius / self.gravity)

    def enqueue(self, task_id: str, urgency_radius: float) -> float:
        """Enqueue a task, assigning it the tier's tautochrone time quantum.

        Tactical advantage: a single call both prioritizes the task
        (smaller radius means smaller descent time means higher
        priority) and assigns its execution time-slice length, both
        derived from one physical parameter.
        """
        time_quantum = self.calc_descent_time(urgency_radius)
        # Tie-break by insertion order to keep scheduling deterministic.
        priority_key = (time_quantum, next(self._counter))
        task = ScheduledTask(priority_key, task_id, time_quantum)
        heapq.heappush(self._heap, task)
        return time_quantum

    def dequeue(self) -> ScheduledTask:
        """Pop the task with the shortest descent time (highest priority)."""
        if not self._heap:
            raise IndexError("scheduler queue is empty")
        return heapq.heappop(self._heap)

    def peek(self) -> ScheduledTask:
        """Return the next task without removing it from the queue."""
        if not self._heap:
            raise IndexError("scheduler queue is empty")
        return self._heap[0]

    def __len__(self) -> int:
        """Return the number of tasks currently queued."""
        return len(self._heap)


if __name__ == "__main__":
    scheduler = TautochronePriorityScheduler()

    quantum_critical = scheduler.enqueue("critical-alert", 0.05)
    quantum_routine = scheduler.enqueue("routine-telemetry", 5.0)
    quantum_background = scheduler.enqueue("background-sync", 50.0)

    assert quantum_critical < quantum_routine < quantum_background, (
        "Smaller urgency radius must yield a shorter descent time."
    )

    first = scheduler.dequeue()
    assert first.task_id == "critical-alert", "Wrong task dequeued first."

    second = scheduler.dequeue()
    assert second.task_id == "routine-telemetry"

    third = scheduler.dequeue()
    assert third.task_id == "background-sync"

    assert len(scheduler) == 0

    # Deterministic tie-break check: identical radius, insertion order wins.
    scheduler.enqueue("tie-a", 1.0)
    scheduler.enqueue("tie-b", 1.0)
    tie_first = scheduler.dequeue()
    assert tie_first.task_id == "tie-a", "Tie-break by insertion order failed."

    print("TautochronePriorityScheduler self-test passed.")
    print(f"Critical quantum: {quantum_critical:.6f}s")
    print(f"Routine quantum: {quantum_routine:.6f}s")
    print(f"Background quantum: {quantum_background:.6f}s")
