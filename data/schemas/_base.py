"""
Core type definitions and base classes for data-driven schema pipeline.
Provides shared enums, base models, and utilities for all generated data classes.
"""
from __future__ import annotations

import sys
from pathlib import Path
try:
    import pydantic
except ImportError:
    _stubs = Path(__file__).resolve().parent.parent.parent / "stubs"
    if str(_stubs) not in sys.path:
        sys.path.insert(0, str(_stubs))

from typing import Any, Dict, List, Optional, Literal, Union, ClassVar
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel



class ItemCategory(str, Enum):
    WEAPON = "weapon"
    SHIELD = "shield"
    HELM = "helm"
    ARMOR = "armor"
    RING = "ring"
    POTION = "potion"
    SCROLL = "scroll"
    FOOD = "food"
    SPELLBOOK = "spellbook"
    TOOL = "tool"
    ROD = "rod"
    ORE = "ore"


class Quality(str, Enum):
    BAD = "bad"
    NORMAL = "normal"
    GOOD = "good"
    MIRACLE = "miracle"
    GOD = "god"


class SkillCategory(str, Enum):
    COMBAT = "combat"
    MAGIC = "magic"
    CRAFT = "craft"
    SOCIAL = "social"


class EffectType(str, Enum):
    DAMAGE_BONUS = "damage_bonus"
    CRIT_CHANCE = "crit_chance"
    MP_COST_REDUCTION = "mp_cost_reduction"
    UNLOCK_SKILL = "unlock_skill"
    HEAL_AMOUNT = "heal_amount"
    STAT_BONUS = "stat_bonus"
    RESISTANCE = "resistance"
    UNLOCK_RECIPE = "unlock_recipe"


class EffectTarget(str, Enum):
    MELEE = "melee"
    SPELL = "spell"
    SELF = "self"
    RANGED = "ranged"
    PET = "pet"
    ALL = "all"


class QuestType(str, Enum):
    MAIN = "main"
    GUILD = "guild"
    PROCEDURAL = "procedural"
    FACTION = "faction"
    PET = "pet"


class ObjectiveType(str, Enum):
    KILL = "kill"
    COLLECT = "collect"
    VISIT = "visit"
    HARVEST = "harvest"
    CRAFT = "craft"
    TALK = "talk"


class RewardType(str, Enum):
    GOLD = "gold"
    PLATINUM = "platinum"
    ITEM = "item"
    EXP = "exp"
    SKILL_POINT = "skill_point"
    FACTION_REP = "faction_rep"
    TITLE = "title"


class PrerequisiteType(str, Enum):
    QUEST_COMPLETE = "quest_complete"
    LEVEL = "level"
    SKILL = "skill"
    FACTION_REP = "faction_rep"
    GUILD_RANK = "guild_rank"


class AIType(str, Enum):
    MELEE = "melee"
    RANGED = "ranged"
    CASTER = "caster"
    FLEE = "flee"
    GUARD = "guard"


class DataModel(BaseModel):
    """Base Pydantic model with common configuration"""
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @classmethod
    def from_yaml(cls, path: str) -> "DataModel":
        import yaml
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(yaml.safe_load(f))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataModel":
        return cls.model_validate(data)


@dataclass(frozen=True, slots=True)
class DataClassBase:
    """Base for generated frozen dataclasses (slots=True for performance)"""
    pass


@dataclass(frozen=True, slots=True)
class EffectData(DataClassBase):
    """Common effect structure used across skills, items, etc."""
    type: EffectType
    value: float
    target: EffectTarget
    condition: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PrerequisiteData(DataClassBase):
    """Common prerequisite structure"""
    type: PrerequisiteType
    value: str
    min_value: Optional[int] = None


@dataclass(frozen=True, slots=True)
class RewardData(DataClassBase):
    """Common reward structure"""
    type: RewardType
    value: Union[str, int]
    count: int = 1


@dataclass(frozen=True, slots=True)
class ObjectiveData(DataClassBase):
    """Common quest objective structure"""
    type: ObjectiveType
    target: str
    count: int


@dataclass(frozen=True, slots=True)
class DropEntryData(DataClassBase):
    """Monster drop table entry"""
    item_id: str
    chance: float
    min_count: int = 1
    max_count: int = 1


@dataclass(frozen=True, slots=True)
class MonsterTableEntryData(DataClassBase):
    """Dungeon monster spawn table entry"""
    monster_id: str
    weight: float
    min_level: int
    max_level: int


@dataclass(frozen=True, slots=True)
class ItemTableEntryData(DataClassBase):
    """Dungeon item spawn table entry"""
    item_id: str
    weight: float
    min_level: int = 1
    max_level: int = 999


def validate_id_format(value: str, prefix: str) -> str:
    """Validate ID follows the required prefix pattern"""
    import re
    pattern = f"^{re.escape(prefix)}[a-z_][a-z0-9_]*$"
    if not re.match(pattern, value):
        raise ValueError(f"ID '{value}' must match pattern '{pattern}'")
    return value


__all__ = [
    "ItemCategory", "Quality", "SkillCategory", "EffectType", "EffectTarget",
    "QuestType", "ObjectiveType", "RewardType", "PrerequisiteType", "AIType",
    "DataModel", "DataClassBase", "EffectData", "PrerequisiteData",
    "RewardData", "ObjectiveData", "DropEntryData",
    "MonsterTableEntryData", "ItemTableEntryData", "validate_id_format",
]