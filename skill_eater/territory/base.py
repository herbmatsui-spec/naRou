"""
skill_eater_territory_system.py
Aの世界（スキル喰い） 派閥テリトリー・勢力図システム
Phase 1: データ構造定義 (Steps 1-12)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from skill_eater_economy_system import FactionState


class TerritoryActionType(str, Enum):
    PATROL = "patrol"
    RAID = "raid"
    PROPAGANDA = "propaganda"
    SABOTAGE = "sabotage"
    NEGOTIATE_CEASEFIRE = "negotiate_ceasefire"


TERRITORY_ACTION_COSTS = {
    TerritoryActionType.PATROL: {"action_points": 1, "aldo": 100, "cooldown": 1},
    TerritoryActionType.RAID: {"action_points": 3, "aldo": 500, "cooldown": 3},
    TerritoryActionType.PROPAGANDA: {"action_points": 2, "aldo": 300, "cooldown": 2},
    TerritoryActionType.SABOTAGE: {"action_points": 3, "aldo": 800, "cooldown": 4},
    TerritoryActionType.NEGOTIATE_CEASEFIRE: {"action_points": 2, "aldo": 2000, "cooldown": 5},
}

TERRITORY_ACTION_BASE_SUCCESS = {
    TerritoryActionType.PATROL: 0.95,
    TerritoryActionType.RAID: 0.50,
    TerritoryActionType.PROPAGANDA: 0.40,
    TerritoryActionType.SABOTAGE: 0.30,
    TerritoryActionType.NEGOTIATE_CEASEFIRE: 0.35,
}


@dataclass
class District:
    id: str
    name: str
    controlling_faction: str = "neutral"
    stability: int = 50
    resource_output: int = 100
    defense_level: int = 1
    hidden_dungeon_entrance: bool = False
    exclusive_shop_unlocked: bool = False
    turn_controlled: int = 0
    sabotage_remaining: int = 0
    adjacent_districts: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.stability = max(0, min(100, self.stability))
        self.resource_output = max(0, self.resource_output)
        self.defense_level = max(1, self.defense_level)
        self.turn_controlled = max(0, self.turn_controlled)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "controlling_faction": self.controlling_faction,
            "stability": self.stability,
            "resource_output": self.resource_output,
            "defense_level": self.defense_level,
            "hidden_dungeon_entrance": self.hidden_dungeon_entrance,
            "exclusive_shop_unlocked": self.exclusive_shop_unlocked,
            "turn_controlled": self.turn_controlled,
            "sabotage_remaining": self.sabotage_remaining,
            "adjacent_districts": self.adjacent_districts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> District:
        return cls(
            id=data["id"],
            name=data["name"],
            controlling_faction=data.get("controlling_faction", "neutral"),
            stability=data.get("stability", 50),
            resource_output=data.get("resource_output", 100),
            defense_level=data.get("defense_level", 1),
            hidden_dungeon_entrance=data.get("hidden_dungeon_entrance", False),
            exclusive_shop_unlocked=data.get("exclusive_shop_unlocked", False),
            turn_controlled=data.get("turn_controlled", 0),
            sabotage_remaining=data.get("sabotage_remaining", 0),
            adjacent_districts=data.get("adjacent_districts", []),
        )


@dataclass
class ActionResult:
    success: bool
    message: str
    effects: dict[str, Any] = field(default_factory=dict)
    audio_cue: str | None = None
    emote_cue: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "effects": self.effects,
            "audio_cue": self.audio_cue,
            "emote_cue": self.emote_cue,
        }


@dataclass
class SabotageEffect:
    district_id: str
    remaining_turns: int
    original_output: int
    original_defense: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "district_id": self.district_id,
            "remaining_turns": self.remaining_turns,
            "original_output": self.original_output,
            "original_defense": self.original_defense,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SabotageEffect:
        return cls(
            district_id=data["district_id"],
            remaining_turns=data["remaining_turns"],
            original_output=data["original_output"],
            original_defense=data["original_defense"],
        )


@dataclass
class CeasefireAgreement:
    faction_a: str
    faction_b: str
    remaining_turns: int
    terms: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "faction_a": self.faction_a,
            "faction_b": self.faction_b,
            "remaining_turns": self.remaining_turns,
            "terms": self.terms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CeasefireAgreement:
        return cls(
            faction_a=data["faction_a"],
            faction_b=data["faction_b"],
            remaining_turns=data["remaining_turns"],
            terms=data.get("terms", {}),
        )


@dataclass
class ActionLog:
    turn: int
    actor_faction: str
    action_type: str
    target_district: str | None
    target_faction: str | None
    success: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "actor_faction": self.actor_faction,
            "action_type": self.action_type,
            "target_district": self.target_district,
            "target_faction": self.target_faction,
            "success": self.success,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionLog:
        return cls(
            turn=data["turn"],
            actor_faction=data["actor_faction"],
            action_type=data["action_type"],
            target_district=data.get("target_district"),
            target_faction=data.get("target_faction"),
            success=data["success"],
            message=data["message"],
        )


TERRITORY_ACTION_AUDIO_MAP = {
    TerritoryActionType.PATROL: "chop.ogg",
    TerritoryActionType.RAID: ["doorOpen_2.ogg", "handleCoins.ogg"],
    TerritoryActionType.PROPAGANDA: "bookOpen.ogg",
    TerritoryActionType.SABOTAGE: ["knifeSlice.ogg", "creak.ogg"],
    TerritoryActionType.NEGOTIATE_CEASEFIRE: "negotiation_chime.ogg",
}

TERRITORY_ACTION_EMOTE_MAP = {
    TerritoryActionType.PATROL: "emote_stars.png",
    TerritoryActionType.RAID: "emote_exclamations.png",
    TerritoryActionType.PROPAGANDA: "emote_speech.png",
    TerritoryActionType.SABOTAGE: "emote_alert.png",
    TerritoryActionType.NEGOTIATE_CEASEFIRE: "emote_heart.png",
}

EVENT_AUDIO_MAP = {
    "faction_war": "territory_capture_fanfare.ogg",
    "betrayal": "riot_crowd.ogg",
    "third_party": "doorOpen_2.ogg",
    "midas_raid": ["metalLatch.ogg", "riot_crowd.ogg"],
}

EVENT_EMOTE_MAP = {
    "faction_war": "emote_exclamations.png",
    "betrayal": "emote_alert.png",
    "third_party": "emote_exclamations.png",
    "midas_raid": "emote_alert.png",
}


class DynamicEventType(str, Enum):
    FACTION_WAR = "faction_war"
    BETRAYAL = "betrayal"
    THIRD_PARTY = "third_party"
    MIDAS_RAID = "midas_raid"


@dataclass
class DynamicEvent:
    id: str
    name: str
    description: str
    event_type: DynamicEventType
    trigger_condition: dict[str, Any]
    duration: int
    effects: dict[str, Any]
    faction_scope: list[str]
    is_active: bool = False
    remaining_turns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type.value,
            "trigger_condition": self.trigger_condition,
            "duration": self.duration,
            "effects": self.effects,
            "faction_scope": self.faction_scope,
            "is_active": self.is_active,
            "remaining_turns": self.remaining_turns,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DynamicEvent:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            event_type=DynamicEventType(data["event_type"]),
            trigger_condition=data["trigger_condition"],
            duration=data["duration"],
            effects=data["effects"],
            faction_scope=data["faction_scope"],
            is_active=data.get("is_active", False),
            remaining_turns=data.get("remaining_turns", 0),
        )


class TerritoryActionBase(ABC):
    def __init__(self, action_type: TerritoryActionType):
        self.action_type = action_type
        self.costs = TERRITORY_ACTION_COSTS[action_type]
        self.base_success = TERRITORY_ACTION_BASE_SUCCESS[action_type]

    @abstractmethod
    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        pass

    @abstractmethod
    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        pass

    @abstractmethod
    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        pass

    def get_audio_cue(self) -> str | list[str]:
        return TERRITORY_ACTION_AUDIO_MAP.get(self.action_type, "")

    def get_emote_cue(self) -> str:
        return TERRITORY_ACTION_EMOTE_MAP.get(self.action_type, "")


