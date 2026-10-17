"""Unit tests for the EventBus in core_framework."""

from __future__ import annotations

from core_framework import EventBus


def test_subscribe_publish():
    bus = EventBus()
    received: list[int] = []
    bus.subscribe("damage", lambda data: received.append(data))
    bus.publish("damage", 42)
    assert received == [42]


def test_unsubscribe():
    bus = EventBus()
    received: list[int] = []
    bus.subscribe("tick", lambda data: received.append(data))
    bus.unsubscribe("tick", bus._subscribers["tick"][0])
    bus.publish("tick", 1)
    assert received == []


def test_publish_no_subscribers_is_safe():
    bus = EventBus()
    bus.publish("nothing", 1)  # should not raise


def test_subscriber_exception_is_isolated():
    bus = EventBus()
    calls: list[int] = []

    def bad(data):
        calls.append(data)
        raise RuntimeError("boom")

    bus.subscribe("e", bad)
    # Should not propagate the subscriber exception to the publisher.
    bus.publish("e", 7)
    assert calls == [7]
