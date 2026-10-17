"""
Tests for world_event_hooks.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from world_event_hooks import EventMonitor
from world_event_system import WorldEvent, WorldEventSystem, WorldEventType


def test_event_monitor_creation():
    """Test that an EventMonitor can be created."""
    monitor = EventMonitor()
    assert monitor is not None
    assert hasattr(monitor, '_handlers')
    assert hasattr(monitor, '_active_events')


def test_register_handler():
    """Test registering a handler for an event type."""
    monitor = EventMonitor()

    def dummy_handler(event):
        pass

    monitor.register_handler(WorldEventType.WAR, dummy_handler)
    assert dummy_handler in monitor._handlers[WorldEventType.WAR]


def test_unregister_handler():
    """Test unregistering a handler."""
    monitor = EventMonitor()

    def dummy_handler(event):
        pass

    monitor.register_handler(WorldEventType.PLAGUE, dummy_handler)
    assert dummy_handler in monitor._handlers[WorldEventType.PLAGUE]

    monitor.unregister_handler(WorldEventType.PLAGUE, dummy_handler)
    assert dummy_handler not in monitor._handlers[WorldEventType.PLAGUE]


def test_update_no_events():
    """Test update when there are no active events."""
    monitor = EventMonitor()
    # Should not raise any exception
    monitor.update()


if __name__ == "__main__":
    test_event_monitor_creation()
    test_register_handler()
    test_unregister_handler()
    test_update_no_events()
    print("All tests passed!")
