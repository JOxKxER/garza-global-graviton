import threading
import time

from trading_app.swarm.bot_base import SwarmBot
from trading_app.swarm.bus import MessageBus


class _FlakyBot(SwarmBot):
    """Fails every other step but never enough consecutive times to trip
    the escalation threshold."""

    name = "flaky_bot"
    poll_interval_seconds = 0.01
    max_consecutive_failures = 3

    def __init__(self, bus_db_path):
        super().__init__(bus_db_path)
        self.call_count = 0

    def step(self, bus: MessageBus) -> None:
        self.call_count += 1
        if self.call_count % 2 == 0:
            raise RuntimeError("simulated transient failure")


class _AlwaysFailBot(SwarmBot):
    name = "always_fail_bot"
    poll_interval_seconds = 0.01
    max_consecutive_failures = 3

    def step(self, bus: MessageBus) -> None:
        raise RuntimeError("simulated persistent failure")


class _NeverInterruptibleBot(SwarmBot):
    name = "never_interruptible_bot"
    poll_interval_seconds = 0.01

    def step(self, bus: MessageBus) -> None:
        pass

    def is_safe_to_restart(self) -> bool:
        return False


def test_transient_failures_do_not_kill_the_bot_thread(tmp_path):
    db_path = str(tmp_path / "bus.db")
    bot = _FlakyBot(db_path)
    stop_event = threading.Event()
    thread = threading.Thread(target=bot.run, args=(stop_event,))
    thread.start()

    time.sleep(0.3)  # let it run through several failure/success cycles
    assert thread.is_alive()

    stop_event.set()
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_persistent_failures_escalate_to_thread_exit(tmp_path):
    db_path = str(tmp_path / "bus.db")
    bot = _AlwaysFailBot(db_path)
    stop_event = threading.Event()
    thread = threading.Thread(target=bot.run, args=(stop_event,))
    thread.start()

    thread.join(timeout=5)  # should exit on its own -- never needs stop_event
    assert not thread.is_alive()

    bus = MessageBus(db_path)
    assert bus.status("always_fail_bot") == "FAILED"


def test_default_bot_is_always_safe_to_restart(tmp_path):
    bot = _FlakyBot(str(tmp_path / "bus.db"))
    assert bot.is_safe_to_restart() is True


def test_bot_can_override_is_safe_to_restart(tmp_path):
    bot = _NeverInterruptibleBot(str(tmp_path / "bus.db"))
    assert bot.is_safe_to_restart() is False
