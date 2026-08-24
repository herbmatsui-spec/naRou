import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

# --- Event Constants ---
EVENT_BEFORE_DAMAGE = "EVENT_BEFORE_DAMAGE"
EVENT_ON_MOVE = "EVENT_ON_MOVE"


class EventBus:
    """Pub/Sub Event Bus for decoupled system messaging."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    @property
    def _subscribers(self) -> Dict[str, List[Callable[[Any], None]]]:
        return self.subscribers

    @_subscribers.setter
    def _subscribers(self, value: Dict[str, List[Callable[[Any], None]]]) -> None:
        self.subscribers = value

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> bool:
        """Remove a callback from a specific event type."""
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            return True
        return False

    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribed callbacks."""
        if event_type in self.subscribers:
            for callback in list(self.subscribers[event_type]):
                try:
                    callback(data)
                except Exception as e:
                    logger.error(
                        f"Error handling event {event_type} in {callback}: {e}",
                        exc_info=True,
                    )

    def clear(self) -> None:
        """Clear all subscribers (useful for testing or state reset)."""
        self.subscribers.clear()


# Global event bus instance for convenience/backward compatibility
event_bus = EventBus()

