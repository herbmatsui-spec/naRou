"""
World Event System Module (Steps 67-71)
"""

from __future__ import annotations
import os
import yaml
import random
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


# Step 68: WorldEventData
@dataclass
class WorldEventData:
    """ワールドイベントデータ (Step 68)"""
    id: str
    name: str = ""
    description: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    duration: int = 100
    effects: Dict[str, Any] = field(default_factory=dict)
    story_triggers: List[str] = field(default_factory=list)


# Step 69, 70: WorldEventRegistry
class WorldEventRegistry:
    """ワールドイベントレジストリ (Step 69, 70)"""
    _instance: Optional[WorldEventRegistry] = None

    def __new__(cls) -> WorldEventRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._events = {}
        return cls._instance

    def load(self, file_path: str = "data/world_events.yaml") -> None:
        """YAMLからワールドイベントを読み込む (Step 70)"""
        self._events = {}
        if not os.path.exists(file_path):
            self._events["blood_moon"] = WorldEventData(
                id="blood_moon", name="血の月", duration=100
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        e_dict = raw.get("world_events", {})
        for eid, edata in e_dict.items():
            self._events[eid] = WorldEventData(
                id=eid,
                name=edata.get("name", eid),
                description=edata.get("description", ""),
                trigger_conditions=edata.get("trigger_conditions", {}),
                duration=int(edata.get("duration", 100)),
                effects=edata.get("effects", {}),
                story_triggers=edata.get("story_triggers", [])
            )

    def get(self, event_id: str) -> Optional[WorldEventData]:
        return self._events.get(event_id)

    def all_events(self) -> Dict[str, WorldEventData]:
        return dict(self._events)


REGISTRY = WorldEventRegistry()


# Step 71: WorldEventManager
class WorldEventManager:
    """ワールドイベント発生・進行管理 (Step 71)"""
    def __init__(self, registry: Optional[WorldEventRegistry] = None):
        self.registry = registry or REGISTRY

    def check_event_triggers(self, player: "Entity", engine: Optional[Any] = None) -> Optional[WorldEventData]:
        """イベント発生判定 (Step 71)"""
        for eid, edata in self.registry.all_events().items():
            if eid not in player.active_world_events:
                cond = edata.trigger_conditions
                chance = cond.get("chance", 0.05)
                if random.random() < chance:
                    return edata
        return None

    def trigger_event(self, player: "Entity", event_id: str, engine: Optional[Any] = None) -> bool:
        """イベントを発生 (Step 71)"""
        edata = self.registry.get(event_id)
        if not edata or not player:
            return False

        if event_id not in player.active_world_events:
            player.active_world_events.append(event_id)

        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"🌌【世界変動】『{edata.name}』が発生した！ {edata.description}", (255, 100, 100))

        return True

    def update_active_events(self, player: "Entity", engine: Optional[Any] = None) -> None:
        """アクティブイベントの進行 (Step 71)"""
        pass
