"""Proposal 6-9 (Seasonal Live Content): announcement, feedback, analytics, reuse.

Consolidated managers for the seasonal content pipeline proposal. These are
tooling/process systems that operate on world-event data.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import yaml
import logging
import time


logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return {}


# ============================================================
# 提案6: Event announcement / countdown
# ============================================================

class EventAnnouncer:
    def __init__(self, announcement_period: int = 7 * 86400):
        self.announcement_period = announcement_period  # seconds before start

    def build_announcement(self, event: dict, start_time: float,
                          now: Optional[float] = None) -> dict:
        now = now if now is not None else time.time()
        countdown = max(0, int(start_time - now))
        announced = (start_time - now) <= self.announcement_period
        return {
            "event_id": event.get("id"),
            "name": event.get("name"),
            "teaser": event.get("description"),
            "announced": announced,
            "countdown_sec": countdown,
            "theme": event.get("theme", event.get("name")),
        }

    def active_countdowns(self, events: Dict[str, dict], starts: Dict[str, float],
                          now: Optional[float] = None) -> List[dict]:
        out = []
        for eid, ev in events.items():
            if eid in starts:
                out.append(self.build_announcement(ev, starts[eid], now))
        return out


# ============================================================
# 提案7: Post-event feedback & carry-over
# ============================================================

class EventFeedbackManager:
    def __init__(self):
        self._feedback: List[dict] = []
        self._legends: List[dict] = []

    def submit_survey(self, event_id: str, satisfaction: int, improvements: List[str]) -> None:
        self._feedback.append({
            "event_id": event_id,
            "satisfaction": satisfaction,
            "improvements": improvements,
            "ts": time.time(),
        })

    def average_satisfaction(self, event_id: str) -> float:
        vals = [f["satisfaction"] for f in self._feedback if f["event_id"] == event_id]
        return sum(vals) / len(vals) if vals else 0.0

    def record_legend(self, event_id: str, title: str, story: str) -> None:
        self._legends.append({"event_id": event_id, "title": title, "story": story})


# ============================================================
# 提案8: Balance data collection & analysis
# ============================================================

@dataclass
class EventAction:
    event_id: str
    player_id: str
    action_type: str
    value: float = 1.0


class EventAnalyticsManager:
    def __init__(self):
        self._actions: List[EventAction] = []

    def record(self, action: EventAction) -> None:
        self._actions.append(action)

    def participation_rate(self, event_id: str, total_players: int) -> float:
        participants = {a.player_id for a in self._actions if a.event_id == event_id}
        return len(participants) / total_players if total_players else 0.0

    def reward_balance(self, event_id: str) -> Dict[str, float]:
        rewards = [a.value for a in self._actions
                   if a.event_id == event_id and a.action_type == "reward"]
        if not rewards:
            return {"avg": 0.0, "count": 0.0, "max": 0.0}
        return {
            "avg": sum(rewards) / len(rewards),
            "count": float(len(rewards)),
            "max": max(rewards),
        }


# ============================================================
# 提案9: Event resource reuse & extensibility
# ============================================================

class EventResourceManager:
    """Validates world-event assets for modular reuse and schema compatibility."""

    CURRENT_SCHEMA = 1

    def __init__(self, path: str = "data/world_events.yaml"):
        self._data: Dict[str, Any] = {}
        self.load(path)

    def load(self, path: str = "data/world_events.yaml") -> None:
        self._data = _load_yaml(path)
        logger.info(f"Loaded world events resource bundle")

    def get_events(self) -> Dict[str, dict]:
        return self._data.get("world_events", {})

    def schema_compatible(self, event: dict) -> bool:
        """Newer schema versions with extra fields must still load old events.

        An event is compatible if it has at least an id and name (the minimum
        required baseline). Extra fields are ignored for backward compatibility.
        """
        return bool(event.get("id")) and bool(event.get("name"))

    def reusable_assets(self, event_id: str) -> Dict[str, Any]:
        """Return modular asset references for an event (images/sound/story)."""
        ev = self.get_events().get(event_id, {})
        return {
            "id": event_id,
            "story_triggers": ev.get("story_triggers", []),
            "effects": ev.get("effects", {}),
            "modules": ["story", "effects", "rewards"],
        }

    def validate_all(self) -> List[str]:
        errors = []
        for eid, ev in self.get_events().items():
            if not self.schema_compatible(ev):
                errors.append(f"{eid}: missing id/name")
        return errors
