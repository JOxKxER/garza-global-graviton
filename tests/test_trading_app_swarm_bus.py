from trading_app.swarm.bus import MessageBus


def test_publish_and_consume_basic(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    bus.publish("topic_a", {"value": 1}, producer="test")
    messages = bus.consume("topic_a", consumer="c1")
    assert len(messages) == 1
    assert messages[0].payload == {"value": 1}
    assert messages[0].producer == "test"


def test_consumed_message_is_not_returned_again(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    bus.publish("topic_a", {"value": 1}, producer="test")
    first = bus.consume("topic_a", consumer="c1")
    second = bus.consume("topic_a", consumer="c1")
    assert len(first) == 1
    assert len(second) == 0


def test_two_consumers_never_claim_the_same_message(tmp_path):
    db_path = str(tmp_path / "bus.db")
    producer_bus = MessageBus(db_path)
    for i in range(5):
        producer_bus.publish("topic_a", {"i": i}, producer="test")

    consumer_a = MessageBus(db_path)
    consumer_b = MessageBus(db_path)

    claimed_a = consumer_a.consume("topic_a", consumer="a", limit=3)
    claimed_b = consumer_b.consume("topic_a", consumer="b", limit=3)

    ids_a = {m.id for m in claimed_a}
    ids_b = {m.id for m in claimed_b}
    assert ids_a.isdisjoint(ids_b)
    assert len(ids_a) + len(ids_b) == 5  # all 5 messages accounted for, no duplicates, none lost


def test_pending_count_reflects_unclaimed_messages(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    for i in range(4):
        bus.publish("topic_a", {"i": i}, producer="test")
    assert bus.pending_count("topic_a") == 4
    bus.consume("topic_a", consumer="c1", limit=2)
    assert bus.pending_count("topic_a") == 2


def test_heartbeat_and_staleness(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    assert bus.last_heartbeat("bot_x") is None
    bus.heartbeat("bot_x", "RUNNING")
    staleness = bus.last_heartbeat("bot_x")
    assert staleness is not None
    assert staleness < 2.0  # just wrote it, should be near-zero seconds old
    assert bus.status("bot_x") == "RUNNING"


def test_shared_state_round_trip(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    assert bus.get_shared_state("some_key", default="fallback") == "fallback"
    bus.set_shared_state("some_key", {"nested": 123})
    assert bus.get_shared_state("some_key") == {"nested": 123}


def test_shared_state_persists_across_bus_instances(tmp_path):
    """Simulates a bot restart: a fresh MessageBus instance against the same
    db file must see state written by a previous instance."""
    db_path = str(tmp_path / "bus.db")
    MessageBus(db_path).set_shared_state("circuit_breaker_tripped", True)
    fresh_bus = MessageBus(db_path)
    assert fresh_bus.get_shared_state("circuit_breaker_tripped") is True
