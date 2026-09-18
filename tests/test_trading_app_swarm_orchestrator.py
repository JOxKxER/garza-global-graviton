import threading
import time

from trading_app.swarm.bot_base import SwarmBot
from trading_app.swarm.bus import MessageBus
from trading_app.swarm.orchestrator import SwarmOrchestrator


class _NoOpBot(SwarmBot):
    """A bot that never fails and never consumes anything -- used as a
    stable core bot in tests so backlog-driven scaling can be tested in
    isolation from real signal computation."""

    poll_interval_seconds = 0.01

    def __init__(self, bus_db_path: str, name: str):
        super().__init__(bus_db_path)
        self.name = name

    def step(self, bus: MessageBus) -> None:
        pass


class _AlwaysFailBot(SwarmBot):
    poll_interval_seconds = 0.01
    max_consecutive_failures = 2

    def __init__(self, bus_db_path: str, name: str):
        super().__init__(bus_db_path)
        self.name = name

    def step(self, bus: MessageBus) -> None:
        raise RuntimeError("simulated persistent failure")


def _fast_orchestrator(db_path: str, **overrides) -> SwarmOrchestrator:
    defaults = dict(
        signal_matrix_backlog_scale_up_threshold=3,
        signal_matrix_backlog_scale_down_threshold=0,
        min_signal_matrix_workers=1,
        max_signal_matrix_workers=3,
        restart_backoff_seconds=0.05,
        restart_wait_for_safe_seconds=2.0,
        heartbeat_stale_seconds=1.0,
        monitor_interval_seconds=0.1,
    )
    defaults.update(overrides)
    return SwarmOrchestrator(db_path, **defaults)


def test_start_launches_all_registered_bots_alive(tmp_path):
    db_path = str(tmp_path / "bus.db")
    orchestrator = _fast_orchestrator(db_path)
    orchestrator.register("bot_a", lambda: _NoOpBot(db_path, "bot_a"))
    orchestrator.register("bot_b", lambda: _NoOpBot(db_path, "bot_b"))
    orchestrator.register_signal_matrix_factory(lambda wid: _NoOpBot(db_path, f"signal_matrix_bot_{wid}"))

    orchestrator.start(initial_signal_matrix_workers=1)
    time.sleep(0.2)
    try:
        status = {s["name"]: s for s in orchestrator.status()}
        assert status["bot_a"]["alive"]
        assert status["bot_b"]["alive"]
        assert status["signal_matrix_bot_1"]["alive"]
    finally:
        orchestrator.stop(timeout_seconds=5)


def test_scales_up_when_backlog_exceeds_threshold(tmp_path):
    db_path = str(tmp_path / "bus.db")
    orchestrator = _fast_orchestrator(db_path)
    orchestrator.register_signal_matrix_factory(lambda wid: _NoOpBot(db_path, f"signal_matrix_bot_{wid}"))
    # No consumer actually drains "market_data_ready" (NoOpBot ignores it),
    # so publishing above the scale-up threshold should trigger growth.
    bus = MessageBus(db_path)
    for i in range(5):
        bus.publish("market_data_ready", {"symbol": f"SYM{i}"}, producer="test")

    orchestrator.start(initial_signal_matrix_workers=1)
    try:
        deadline = time.time() + 3
        worker_count = 1
        while time.time() < deadline:
            worker_count = sum(1 for s in orchestrator.status() if s["is_scalable_worker"])
            if worker_count > 1:
                break
            time.sleep(0.1)
        assert worker_count > 1
    finally:
        orchestrator.stop(timeout_seconds=5)


def test_scales_down_to_minimum_when_backlog_is_empty(tmp_path):
    db_path = str(tmp_path / "bus.db")
    orchestrator = _fast_orchestrator(db_path, min_signal_matrix_workers=1)
    orchestrator.register_signal_matrix_factory(lambda wid: _NoOpBot(db_path, f"signal_matrix_bot_{wid}"))

    orchestrator.start(initial_signal_matrix_workers=1)
    try:
        time.sleep(0.5)  # empty backlog the whole time
        worker_count = sum(1 for s in orchestrator.status() if s["is_scalable_worker"])
        assert worker_count == 1  # never scaled above the minimum
    finally:
        orchestrator.stop(timeout_seconds=5)


def test_failed_bot_is_restarted_in_isolation_without_affecting_others(tmp_path):
    db_path = str(tmp_path / "bus.db")
    orchestrator = _fast_orchestrator(db_path)
    orchestrator.register("stable_bot", lambda: _NoOpBot(db_path, "stable_bot"))
    orchestrator.register("failing_bot", lambda: _AlwaysFailBot(db_path, "failing_bot"))
    orchestrator.register_signal_matrix_factory(lambda wid: _NoOpBot(db_path, f"signal_matrix_bot_{wid}"))

    orchestrator.start(initial_signal_matrix_workers=1)
    try:
        deadline = time.time() + 5
        restarted = False
        while time.time() < deadline:
            status = {s["name"]: s for s in orchestrator.status()}
            if status["failing_bot"]["restart_count"] >= 1:
                restarted = True
                break
            time.sleep(0.1)

        assert restarted
        status = {s["name"]: s for s in orchestrator.status()}
        # The stable bot must never have been touched by the other bot's crash.
        assert status["stable_bot"]["restart_count"] == 0
        assert status["stable_bot"]["alive"]
    finally:
        orchestrator.stop(timeout_seconds=5)
