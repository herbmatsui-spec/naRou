"""
Pub/Sub Event Bus System
Decouples systems by allowing them to subscribe to and publish events.
"""

from typing import Any, Callable, Dict, List

# --- Event Constants ---
EVENT_BEFORE_DAMAGE = "EVENT_BEFORE_DAMAGE"
EVENT_ON_MOVE = "EVENT_ON_MOVE"


class EventBus:
    """Singleton event bus for pub/sub messaging."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.subscribers: Dict[str, List[Callable]] = {}
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Remove a callback from a specific event type."""
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribed callbacks."""
        if event_type in self.subscribers:
            # Create a copy of the list to allow safe modification during iteration
            for callback in list(self.subscribers[event_type]):
                callback(data)

    def clear(self) -> None:
        """Clear all subscribers (useful for testing or state reset)."""
        self.subscribers.clear()


# Global singleton instance
event_bus = EventBus()
