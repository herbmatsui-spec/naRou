"""
skill_eater_system.py
Aの世界（スキル喰い）コアデータ構造および管理システム
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class SkillTier(str, Enum):
    COMMON = "Common"
    RARE = "Rare"
    UNIQUE = "Unique"
    CONCEPT = "Concept"
    EATER = "Eater"


class SkillType(str, Enum):
    ACTIVE = "Active"
    PASSIVE = "Passive"
    CRAFT = "Craft"
    META = "Meta"


@dataclass
class SkillEffect:
    effect_type: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillEffect:
        data_copy = dict(data)
        effect_type = data_copy.pop("type", "Unknown")
        target = data_copy.pop("target", "Self")
        return cls(effect_type=effect_type, target=target, params=data_copy)


@dataclass
class SkillDef:
    id: str
    name: str
    tier: SkillTier
    type: SkillType
    mp_cost: int = 0
    cooldown: int = 0
    market_value: int = 0
    tags: list[str] = field(default_factory=list)
    flavor_text: str = ""
    effects: list[SkillEffect] = field(default_factory=list)
    is_illegal: bool = False
    memory_usage: int = 1
    is_encrypted: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillDef:
        tier_val = SkillTier(data.get("tier", "Common"))
        type_val = SkillType(data.get("type", "Passive"))
        effects_data = data.get("effects", [])
        effects = [SkillEffect.from_dict(e) for e in effects_data]

        return cls(
            id=data["id"],
            name=data["name"],
            tier=tier_val,
            type=type_val,
            mp_cost=data.get("mp_cost", 0),
            cooldown=data.get("cooldown", 0),
            market_value=data.get("market_value", 0),
            tags=data.get("tags", []),
            flavor_text=data.get("flavor_text", ""),
            effects=effects,
            is_illegal=data.get("is_illegal", False),
            memory_usage=data.get(
                "memory_usage",
                (
                    1
                    if tier_val == SkillTier.COMMON
                    else (
                        2
                        if tier_val == SkillTier.RARE
                        else (4 if tier_val == SkillTier.UNIQUE else 5)
                    )
                ),
            ),
            is_encrypted=data.get(
                "is_encrypted", tier_val in [SkillTier.UNIQUE, SkillTier.CONCEPT]
            ),
        )


class SkillEaterRegistry:
    _instance: SkillEaterRegistry | None = None

    def __init__(self):
        self._skills: dict[str, SkillDef] = {}

    @classmethod
    def get_instance(cls) -> SkillEaterRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_from_yaml(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Skill definition file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "skills" not in data:
            return

        for skill_data in data["skills"]:
            skill = SkillDef.from_dict(skill_data)
            self._skills[skill.id] = skill

    def get_skill(self, skill_id: str) -> SkillDef | None:
        return self._skills.get(skill_id)

    def get_all_skills(self) -> list[SkillDef]:
        return list(self._skills.values())

    def get_skills_by_tier(self, tier: SkillTier) -> list[SkillDef]:
        return [s for s in self._skills.values() if s.tier == tier]

    def get_skills_by_tag(self, tag: str) -> list[SkillDef]:
        return [s for s in self._skills.values() if tag in s.tags]


@dataclass
class CharacterSkillSlot:
    skill_id: str
    level: int = 1
    current_cooldown: int = 0


@dataclass
class CharacterState:
    id: str
    name: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    atk: int
    defense: int
    intelligence: int
    speed: int
    analysis_level: int = 1
    skills: dict[str, CharacterSkillSlot] = field(default_factory=dict)
    status_effects: list[str] = field(default_factory=list)
    is_husk: bool = False  # スキルを全て失って空っぽになった状態
    last_devoured_element: str | None = None  # 前回喰らったスキルの代表属性
    max_memory_capacity: int = 10  # 記憶容量（メモリ）上限
    addiction_buildup: int = 0  # スキル精神侵食度 (0 - 100)
    encryption_broken: bool = False  # ハッキングによる偽装解除フラグ

    @property
    def current_memory_usage(self) -> int:
        registry = SkillEaterRegistry.get_instance()
        total = 0
        for s_id in self.skills:
            s_def = registry.get_skill(s_id)
            if s_def:
                total += s_def.memory_usage
            else:
                total += 1
        return total

    def add_skill(self, skill_id: str, level: int = 1) -> bool:
        if skill_id in self.skills:
            return True
        registry = SkillEaterRegistry.get_instance()
        s_def = registry.get_skill(skill_id)
        cost = s_def.memory_usage if s_def else 1
        if self.current_memory_usage + cost > self.max_memory_capacity:
            return False  # メモリ超過で習得不可
        self.skills[skill_id] = CharacterSkillSlot(skill_id=skill_id, level=level)
        return True

    def remove_skill(self, skill_id: str) -> CharacterSkillSlot | None:
        slot = self.skills.pop(skill_id, None)
        if len(self.skills) == 0:
            self.is_husk = True
        return slot

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.skills

    def get_skill_ids(self) -> list[str]:
        return list(self.skills.keys())
