"""Common lifecycle for every swarm bot: heartbeats, a stop event, and a
two-tier fault-isolation policy.

Tier 1 (inside this base class): a single failed `step()` is logged and
tolerated -- the loop keeps going. This absorbs transient issues (e.g. one
bad API response) without even needing a restart.

Tier 2 (the orchestrator): if a bot accumulates too many consecutive step
failures, `run()` re-raises so the bot's *thread* exits; the orchestrator
detects that and starts a fresh instance of just that bot after a backoff --
every other bot keeps running untouched, since they only ever interact
through the message bus, never through shared in-process state.
"""

from __future__ import annotations

import abc
import logging
import threading

from .bus import MessageBus

log = logging.getLogger("trading_app.swarm")


class SwarmBot(abc.ABC):
    name: str = "unnamed_bot"
    poll_interval_seconds: float = 1.0
    max_consecutive_failures: int = 5

    def __init__(self, bus_db_path: str):
        self.bus_db_path = bus_db_path

    @abc.abstractmethod
    def step(self, bus: MessageBus) -> None:
        """One unit of work. Raise on failure; the base class decides
        whether that's tolerated or should escalate to a thread restart."""

    def is_safe_to_restart(self) -> bool:
        """Override to return False while a non-interruptible unit of work
        is in flight (see ExecutionBot) -- the orchestrator checks this
        before restarting a failed bot and will wait rather than yank a
        thread out from under an in-progress order submission."""
        return True

    def run(self, stop_event: threading.Event) -> None:
        bus = MessageBus(self.bus_db_path)
        consecutive_failures = 0
        try:
            bus.heartbeat(self.name, "STARTING")
            while not stop_event.is_set():
                try:
                    self.step(bus)
                    consecutive_failures = 0
                    bus.heartbeat(self.name, "RUNNING")
                except Exception:
                    consecutive_failures += 1
                    log.exception("%s: step failed (%d/%d consecutive)", self.name,
                                  consecutive_failures, self.max_consecutive_failures)
                    bus.heartbeat(self.name, "DEGRADED")
                    if consecutive_failures >= self.max_consecutive_failures:
                        bus.heartbeat(self.name, "FAILED")
                        raise
                stop_event.wait(self.poll_interval_seconds)
        finally:
            # Don't clobber a FAILED status recorded above with STOPPED --
            # the orchestrator (and tests) need to distinguish "this bot
            # exited normally" from "this bot escalated after repeated
            # failures and needs a fresh restart."
            if bus.status(self.name) != "FAILED":
                bus.heartbeat(self.name, "STOPPED")
            bus.close()
