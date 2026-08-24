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
    memory_cost_mb: int = 20
    is_encrypted: bool = False
    unlock_conditions: list[dict[str, Any]] = field(
        default_factory=list
    )  # 例: [{'type': 'element', 'element': 'Ice'}]
    is_trap: bool = False  # トラップスキルか
    trap_penalty: str = "Virus"  # トラップ発動時のペナルティ

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillDef:
        tier_val = SkillTier(data.get("tier", "Common"))
        type_val = SkillType(data.get("type", "Passive"))
        effects_data = data.get("effects", [])
        effects = [SkillEffect.from_dict(e) for e in effects_data]

        tier_mem_mb = (
            15
            if tier_val == SkillTier.COMMON
            else (
                25 if tier_val == SkillTier.RARE else (45 if tier_val == SkillTier.UNIQUE else 60)
            )
        )

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
            memory_cost_mb=data.get("memory_cost_mb", tier_mem_mb),
            is_encrypted=data.get(
                "is_encrypted", tier_val in [SkillTier.UNIQUE, SkillTier.CONCEPT]
            ),
            unlock_conditions=data.get("unlock_conditions", []),
            is_trap=data.get("is_trap", False),
            trap_penalty=data.get("trap_penalty", "Virus"),
        )


DEFAULT_SKILL_MEMORY_USAGE = 1
DEFAULT_SKILL_MEMORY_COST_MB = 20


class SkillEaterRegistry:
    _instance: SkillEaterRegistry | None = None

    def __init__(self):
        self._skills: dict[str, SkillDef] = {}

    @classmethod
    def get_instance(cls) -> SkillEaterRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        if cls._instance is not None:
            cls._instance._skills.clear()
        cls._instance = None

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
    is_encrypted: bool = False
    unlock_conditions: list[dict[str, Any]] = field(default_factory=list)
    is_trap: bool = False
    trap_penalty: str = "Virus"
    is_disguised: bool = False  # 弱いスキルに偽装されているか
    real_skill_id: str | None = None


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
    archived_skills: dict[str, CharacterSkillSlot] = field(default_factory=dict)
    max_memory_capacity: int = 10  # 記憶容量（メモリ）上限
    base_memory_capacity_mb: int = 100  # 脳メモリ容量 (MB)
    current_used_memory_mb: int = 0  # 現在使用中の合計MB
    overclock_level: int = 0  # オーバークロック率 (%)
    max_active_slots: int = 4  # アクティブスキル上限
    max_passive_slots: int = 4  # パッシブスキル上限
    has_cyberpunk_eye: bool = False  # Lv40義眼インプラント所持フラグ
    active_skills: list[str] = field(default_factory=list)
    passive_skills: list[str] = field(default_factory=list)
    addiction_buildup: int = 0  # スキル精神侵食度 (0 - 100)
    encryption_broken: bool = False  # ハッキングによる偽装解除フラグ
    junk: int = 0  # スクラップ/ジャンク資源
    facility_action_cooldowns: dict[str, int] = field(
        default_factory=dict
    )  # 施設アクションクールダウン
    unidentified_crystals: list[str] = field(default_factory=list)  # 未鑑定スキル結晶
    perception: int = 10  # 知覚/観察力 (SkillEaterSecretAccess)

    # SkillEaterSecretAccess - 隠しエリア・鍵システム
    discovered_secrets: set[str] = field(default_factory=set)  # 発見済みシークレットID
    unlocked_secrets: set[str] = field(default_factory=set)  # 解放済みシークレットID
    owned_keys: dict[str, int] = field(default_factory=dict)  # key_id -> count
    discovered_lore: list[dict] = field(default_factory=list)  # 発見したロア
    last_search_turn: int = 0  # 最後のサーチ実行ターン
    failed_search_count: int = 0  # 連続検知失敗回数

    def calculate_memory_usage(self) -> int:
        """装備中スキルの合計MBおよびオーバークロック率(%)を計算して更新する"""
        registry = SkillEaterRegistry.get_instance()
        total_mb = 0
        for s_id in self.skills:
            s_def = registry.get_skill(s_id)
            if s_def:
                total_mb += s_def.memory_cost_mb
            else:
                total_mb += DEFAULT_SKILL_MEMORY_COST_MB
        self.current_used_memory_mb = total_mb
        if self.base_memory_capacity_mb > 0 and total_mb > self.base_memory_capacity_mb:
            excess = total_mb - self.base_memory_capacity_mb
            self.overclock_level = int((excess / self.base_memory_capacity_mb) * 100)
        else:
            self.overclock_level = 0
        return total_mb

    @property
    def current_memory_usage(self) -> int:
        registry = SkillEaterRegistry.get_instance()
        total = 0
        for s_id in self.skills:
            s_def = registry.get_skill(s_id)
            if s_def:
                total += s_def.memory_usage
            else:
                total += DEFAULT_SKILL_MEMORY_USAGE
        return total

    def add_skill(self, skill_id: str, level: int = 1, ignore_capacity: bool = False) -> bool:
        if skill_id in self.skills:
            return True
        registry = SkillEaterRegistry.get_instance()
        s_def = registry.get_skill(skill_id)
        cost = s_def.memory_usage if s_def else DEFAULT_SKILL_MEMORY_USAGE
        if not ignore_capacity and self.current_memory_usage + cost > self.max_memory_capacity:
            return False
        self.skills[skill_id] = CharacterSkillSlot(skill_id=skill_id, level=level)
        self.calculate_memory_usage()
        return True

    def remove_skill(self, skill_id: str) -> CharacterSkillSlot | None:
        slot = self.skills.pop(skill_id, None)
        if slot is not None:
            self.calculate_memory_usage()
        if len(self.skills) == 0:
            self.is_husk = True
        return slot

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.skills

    def get_skill_ids(self) -> list[str]:
        return list(self.skills.keys())

    def archive_skill(self, skill_id: str) -> bool:
        """通常所持スキルをアジトの保管庫（アーカイブ）に預け、メモリ使用量と侵食影響を解除する"""
        if skill_id not in self.skills:
            return False
        slot = self.skills.pop(skill_id)
        self.calculate_memory_usage()
        if len(self.skills) == 0:
            self.is_husk = True
        self.archived_skills[skill_id] = slot
        return True

    def retrieve_skill(self, skill_id: str) -> bool:
        """保管庫からスキルを通常メモリにロード（装備）する"""
        if skill_id not in self.archived_skills:
            return False
        registry = SkillEaterRegistry.get_instance()
        s_def = registry.get_skill(skill_id)
        cost = s_def.memory_usage if s_def else DEFAULT_SKILL_MEMORY_USAGE
        if self.current_memory_usage + cost > self.max_memory_capacity:
            return False  # メモリ容量不足
        slot = self.archived_skills.pop(skill_id)
        self.skills[skill_id] = slot
        self.is_husk = False
        self.calculate_memory_usage()
        return True

    def get_archived_skill_ids(self) -> list[str]:
        return list(self.archived_skills.keys())

    # SkillEaterSecretAccess - 鍵管理メソッド
    def add_key(self, key_id: str, count: int = 1) -> None:
        """鍵アイテムを追加"""
        self.owned_keys[key_id] = self.owned_keys.get(key_id, 0) + count

    def remove_key(self, key_id: str, count: int = 1) -> bool:
        """鍵アイテムを消費・削除"""
        current = self.owned_keys.get(key_id, 0)
        if current < count:
            return False
        if current == count:
            del self.owned_keys[key_id]
        else:
            self.owned_keys[key_id] = current - count
        return True

    def has_key(self, key_id: str) -> bool:
        """鍵アイテムを所持しているか"""
        return self.owned_keys.get(key_id, 0) > 0

    def get_key_count(self, key_id: str) -> int:
        """鍵アイテムの所持数を取得"""
        return self.owned_keys.get(key_id, 0)


# SkillEaterState は CharacterState のエイリアス
SkillEaterState = CharacterState
