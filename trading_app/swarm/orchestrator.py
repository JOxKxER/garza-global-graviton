"""Swarm orchestrator: starts the fixed core bots, dynamically scales the
Signal Matrix Bot pool up/down based on observed backlog, and provides
isolated auto-restart for any bot that fails -- without ever touching
another bot's thread or state.
"""

from __future__ import annotations

import itertools
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .bot_base import SwarmBot
from .bots.data_ingestion_bot import TOPIC_MARKET_DATA_READY
from .bus import MessageBus

log = logging.getLogger("trading_app.swarm.orchestrator")

DEFAULT_RESTART_BACKOFF_SECONDS = 3.0
DEFAULT_RESTART_WAIT_FOR_SAFE_SECONDS = 30.0
DEFAULT_HEARTBEAT_STALE_SECONDS = 15.0
DEFAULT_MONITOR_INTERVAL_SECONDS = 2.0


@dataclass
class _BotHandle:
    name: str
    factory: Callable[[], SwarmBot]
    stop_event: threading.Event
    is_scalable_worker: bool = False
    bot: Optional[SwarmBot] = None
    thread: Optional[threading.Thread] = None
    restart_count: int = 0


class SwarmOrchestrator:
    def __init__(
        self,
        bus_db_path: str,
        signal_matrix_backlog_scale_up_threshold: int = 10,
        signal_matrix_backlog_scale_down_threshold: int = 1,
        min_signal_matrix_workers: int = 1,
        max_signal_matrix_workers: int = 4,
        restart_backoff_seconds: float = DEFAULT_RESTART_BACKOFF_SECONDS,
        restart_wait_for_safe_seconds: float = DEFAULT_RESTART_WAIT_FOR_SAFE_SECONDS,
        heartbeat_stale_seconds: float = DEFAULT_HEARTBEAT_STALE_SECONDS,
        monitor_interval_seconds: float = DEFAULT_MONITOR_INTERVAL_SECONDS,
    ):
        self.bus_db_path = bus_db_path
        self.bus = MessageBus(bus_db_path)
        self.scale_up_threshold = signal_matrix_backlog_scale_up_threshold
        self.scale_down_threshold = signal_matrix_backlog_scale_down_threshold
        self.min_signal_matrix_workers = min_signal_matrix_workers
        self.max_signal_matrix_workers = max_signal_matrix_workers
        self.restart_backoff_seconds = restart_backoff_seconds
        self.restart_wait_for_safe_seconds = restart_wait_for_safe_seconds
        self.heartbeat_stale_seconds = heartbeat_stale_seconds
        self.monitor_interval_seconds = monitor_interval_seconds

        self._handles: Dict[str, _BotHandle] = {}
        self._handles_lock = threading.Lock()
        self._worker_id_seq = itertools.count(1)
        self._master_stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def _handles_snapshot(self) -> List[_BotHandle]:
        with self._handles_lock:
            return list(self._handles.values())

    # --- Registration ----------------------------------------------------

    def register(self, name: str, factory: Callable[[], SwarmBot], scalable: bool = False) -> None:
        with self._handles_lock:
            self._handles[name] = _BotHandle(
                name=name, factory=factory, stop_event=threading.Event(), is_scalable_worker=scalable
            )

    def register_signal_matrix_factory(self, factory_maker: Callable[[int], SwarmBot]) -> None:
        """`factory_maker(worker_id)` builds one SignalMatrixBot instance.
        Called once per initial worker at start(), and again whenever the
        orchestrator scales the pool up."""
        self._signal_matrix_factory_maker = factory_maker

    # --- Lifecycle ---------------------------------------------------------

    def _start_bot(self, handle: _BotHandle) -> None:
        handle.stop_event.clear()
        handle.bot = handle.factory()
        handle.thread = threading.Thread(target=handle.bot.run, args=(handle.stop_event,), daemon=True)
        handle.thread.start()
        log.info("Started bot %s (restart_count=%d)", handle.name, handle.restart_count)

    def start(self, initial_signal_matrix_workers: int = 1) -> None:
        for handle in self._handles_snapshot():
            self._start_bot(handle)

        for _ in range(initial_signal_matrix_workers):
            self._spawn_signal_matrix_worker()

        self._monitor_thread = threading.Thread(target=self._supervise_loop, daemon=True)
        self._monitor_thread.start()
        core_count = len(self._handles_snapshot()) - self._count_signal_matrix_workers()
        log.info("Orchestrator started with %d core bots + %d signal matrix workers",
                  core_count, self._count_signal_matrix_workers())

    def stop(self, timeout_seconds: float = 20.0) -> None:
        log.info("Orchestrator stopping all bots...")
        self._master_stop.set()
        handles = self._handles_snapshot()
        for handle in handles:
            handle.stop_event.set()
        for handle in handles:
            if handle.thread:
                handle.thread.join(timeout=timeout_seconds)
        if self._monitor_thread:
            self._monitor_thread.join(timeout=timeout_seconds)
        self.bus.close()
        log.info("Orchestrator fully stopped.")

    # --- Dynamic scaling of the Signal Matrix Bot pool ----------------------

    def _count_signal_matrix_workers(self) -> int:
        return sum(1 for h in self._handles_snapshot() if h.is_scalable_worker)

    def _spawn_signal_matrix_worker(self) -> None:
        worker_id = next(self._worker_id_seq)
        name = f"signal_matrix_bot_{worker_id}"
        factory = lambda wid=worker_id: self._signal_matrix_factory_maker(wid)  # noqa: E731
        handle = _BotHandle(name=name, factory=factory, stop_event=threading.Event(), is_scalable_worker=True)
        with self._handles_lock:
            self._handles[name] = handle
        self._start_bot(handle)
        log.info("Scaled UP: spawned %s (pool size now %d)", name, self._count_signal_matrix_workers())

    def _retire_one_signal_matrix_worker(self) -> None:
        with self._handles_lock:
            scalable = [h for h in self._handles.values() if h.is_scalable_worker]
            if len(scalable) <= self.min_signal_matrix_workers:
                return
            victim = scalable[-1]  # retire the most recently spawned extra worker
            del self._handles[victim.name]
        victim.stop_event.set()
        if victim.thread:
            victim.thread.join(timeout=10)
        log.info("Scaled DOWN: retired %s (pool size now %d)", victim.name, self._count_signal_matrix_workers())

    def _maybe_rescale(self) -> None:
        backlog = self.bus.pending_count(TOPIC_MARKET_DATA_READY)
        workers = self._count_signal_matrix_workers()
        if backlog >= self.scale_up_threshold and workers < self.max_signal_matrix_workers:
            self._spawn_signal_matrix_worker()
        elif backlog <= self.scale_down_threshold and workers > self.min_signal_matrix_workers:
            self._retire_one_signal_matrix_worker()

    # --- Fault detection & isolated restart ---------------------------------

    def _bot_needs_restart(self, handle: _BotHandle) -> bool:
        if handle.thread is None or not handle.thread.is_alive():
            return True
        staleness = self.bus.last_heartbeat(handle.name)
        return staleness is not None and staleness > self.heartbeat_stale_seconds

    def _restart_bot(self, handle: _BotHandle) -> None:
        if handle.bot is not None and not handle.bot.is_safe_to_restart():
            log.info("%s has non-interruptible work in flight; deferring restart.", handle.name)
            return  # try again on the next monitor tick

        log.warning("Restarting bot %s after failure/staleness.", handle.name)
        handle.stop_event.set()
        if handle.thread:
            handle.thread.join(timeout=self.restart_wait_for_safe_seconds)
        handle.restart_count += 1
        time.sleep(self.restart_backoff_seconds)
        if self._master_stop.is_set():
            return
        self._start_bot(handle)

    def _supervise_loop(self) -> None:
        while not self._master_stop.is_set():
            for handle in self._handles_snapshot():
                if self._master_stop.is_set():
                    break
                if self._bot_needs_restart(handle):
                    self._restart_bot(handle)

            if not self._master_stop.is_set():
                self._maybe_rescale()

            self._master_stop.wait(self.monitor_interval_seconds)

    # --- Introspection -------------------------------------------------------

    def status(self) -> List[dict]:
        return [
            {
                "name": h.name,
                "alive": bool(h.thread and h.thread.is_alive()),
                "restart_count": h.restart_count,
                "is_scalable_worker": h.is_scalable_worker,
                "seconds_since_heartbeat": self.bus.last_heartbeat(h.name),
            }
            for h in self._handles_snapshot()
        ]
