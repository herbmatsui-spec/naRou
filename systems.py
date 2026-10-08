"""
Elona Roguelike - フェーズ5: 高度な戦闘・属性・フレンドリーファイア・出血システム
Steps 37-45: 属性耐性, 詠唱失敗率, AoEパターン, Faction/Aggro, 出血と自然回復の相殺

Note: CombatSystem is now a thin wrapper delegating to engine.systems.combat_system.CombatSystem.
The actual implementation has been consolidated there.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from constants import Element
from naRou import combat

if TYPE_CHECKING:
    from ecs.entity import Entity
    from item_system import Item

# 状態異常
STATUS_POISON = "毒"
STATUS_PARALYSIS = "麻痺"
STATUS_CONFUSION = "混乱"
STATUS_BLIND = "盲目"
STATUS_BLEEDING = "出血"  # ステップ45
STATUS_HASTE = "加速"
STATUS_SLOW = "鈍足"
STATUS_RETURN = "帰還待機"  # ステップ63 遅延ワープ

# ファクション (ステップ42)
FACTION_PLAYER = "player"
FACTION_MONSTER = "monster"
FACTION_TOWNSFOLK = "townsfolk"
FACTION_GUARD = "guard"


@dataclass
class StatusEffect:
    """状態異常 - Tick連動(ステップ16)"""

    name: str
    remaining_ticks: int  # 残り持続Tick
    power: int = 1  # 効果の強さ
    source: str | None = None


class ResistanceSet:
    """属性耐性セット (ステップ37)"""

    def __init__(self):
        self.fire = 0  # -100〜100, 0=通常, 100=無効, -50=弱点(1.5倍)
        self.cold = 0
        self.lightning = 0
        self.darkness = 0
        self.chaos = 0
        self.magic = 0

    def get(self, element: Element) -> int:
        mapping = {
            Element.FIRE: self.fire,
            Element.COLD: self.cold,
            Element.LIGHTNING: self.lightning,
            Element.DARKNESS: self.darkness,
            Element.CHAOS: self.chaos,
            Element.MAGIC: self.magic,
        }
        return mapping.get(element, 0)


class AggroList:
    """ヘイトリスト (ステップ42)"""

    def __init__(self):
        self._table: dict[str, int] = {}  # entity name -> hate_value

    def add_hate(self, target_name: str, amount: int) -> None:
        self._table[target_name] = self._table.get(target_name, 0) + amount

    def top_target(self) -> str | None:
        if not self._table:
            return None
        return max(self._table, key=lambda k: self._table[k])


# ==================== DELEGATED COMBAT SYSTEM (thin wrapper for backward compat) ====================
class CombatSystem:
    """Legacy CombatSystem - delegates to engine.systems.combat_system.CombatSystem.

    This is a backward-compatibility wrapper. New code should use
    engine.systems.combat_system.CombatSystem directly.
    """

    @staticmethod
    def _get_new_combat():
        """Get the new CombatSystem class."""
        from engine.systems.combat_system import CombatSystem as NewCombatSystem
        return NewCombatSystem

    # Delegate all static methods to new implementation
    @staticmethod
    def aoe_radius(cx: int, cy: int, radius: int = 1):
        return CombatSystem._get_new_combat().aoe_radius(cx, cy, radius)

    @staticmethod
    def aoe_beam(sx: int, sy: int, direction: tuple[int, int], length: int = 5):
        return CombatSystem._get_new_combat().aoe_beam(sx, sy, direction, length)

    @staticmethod
    def aoe_nova(cx: int, cy: int):
        return CombatSystem._get_new_combat().aoe_nova(cx, cy)

    @staticmethod
    def publish_damage_event(event_bus, damage: int, x: int, y: int, is_crit: bool = False, is_kill: bool = False):
        return CombatSystem._get_new_combat().publish_damage_event(event_bus, damage, x, y, is_crit, is_kill)

    @staticmethod
    def publish_kill_event(event_bus, x: int, y: int):
        return CombatSystem._get_new_combat().publish_kill_event(event_bus, x, y)

    @staticmethod
    def publish_trap_event(event_bus, damage: int, x: int, y: int):
        return CombatSystem._get_new_combat().publish_trap_event(event_bus, damage, x, y)

    @staticmethod
    def calc_element_damage(base_dmg: int, element: Element, resistance: int):
        return CombatSystem._get_new_combat().calc_element_damage(base_dmg, element, resistance)

    @staticmethod
    def calc_spell_success(caster: Entity, spell_id: str):
        return CombatSystem._get_new_combat().calc_spell_success(caster, spell_id)

    @staticmethod
    def calculate_melee_attack(attacker: Entity, defender: Entity, weapon=None, element: Element = Element.PHYSICAL):
        return CombatSystem._get_new_combat().calculate_melee_attack(attacker, defender, weapon, element)

    @staticmethod
    def apply_aoe(caster: Entity, coords: list[tuple[int, int]], base_dmg_range: tuple[int, int], element: Element, entities: list[Entity], karma_ref: Any = None):
        return CombatSystem._get_new_combat().apply_aoe(caster, coords, base_dmg_range, element, entities, karma_ref)

    @staticmethod
    def process_status_effects(entity: Entity):
        return CombatSystem._get_new_combat().process_status_effects(entity)

    @staticmethod
    def cast_spell(caster: Entity, spell_name: str, target: Entity):
        return CombatSystem._get_new_combat().cast_spell(caster, spell_name, target)

    @staticmethod
    def is_exclusive_skill(skill_id: str):
        return CombatSystem._get_new_combat().is_exclusive_skill(skill_id)

    @staticmethod
    def get_exclusive_skill_data(skill_id: str):
        return CombatSystem._get_new_combat().get_exclusive_skill_data(skill_id)

    @staticmethod
    def execute_exclusive_skill(caster: Entity, skill_id: str, target: Entity):
        return CombatSystem._get_new_combat().execute_exclusive_skill(caster, skill_id, target)

    # TODO: Reincarnation scaling


class SurvivalSystem:
    """生存システム (ステップ33)"""

    def __init__(self):
        self.hunger = 0
        self.thirst = 0
        self.fatigue = 0
        self.karma = 0
        self.gold = 0
        self.fame = 0
        self.turns = 0

    def tick(self, entity: Entity) -> list[str]:
        logs = []
        # ... existing implementation
        return logs

    def eat(self, entity: Entity, food_value: int) -> str:
        # ... existing implementation
        return ""

    def drink(self, entity: Entity, water_value: int) -> str:
        # ... existing implementation
        return ""


@dataclass
class Quest:
    """クエストクラス (ステップ34)"""

    title: str
    target_monster: str
    target_count: int
    current_count: int = 0
    reward_gold: int = 200
    reward_platinum: int = 2
    completed: bool = False


# ==================== MonsterPreset (restored from original) ====================

class MonsterPreset:
    # Map monster names to Tiny Rogue tile IDs
    MONSTER_TILE_MAP = {
        "slime": "TR_MONSTER_01",
        "red_slime": "TR_MONSTER_01",
        "snail": "TR_MONSTER_02",
        "goblin": "TR_MONSTER_01",
        "kobold": "TR_MONSTER_02",
        "orc": "TR_MONSTER_03",
        "hound_fire": "TR_MONSTER_VAR_01",
        "rogue_thief": "TR_MONSTER_VAR_02",
        "novice_wizard": "TR_MONSTER_VAR_03",
        "minotaur": "TR_MONSTER_VAR_01",
        "lich": "TR_MONSTER_VAR_02",
        "dragon_red": "TR_MONSTER_VAR_03",
    }

    # Map pet types to Tiny Rogue tile IDs so pets render with real art
    # instead of the generic placeholder. Falls back to "PET" when unknown.
    PET_TILE_MAP = {
        "puppy": "TR_MONSTER_VAR_01",
        "hound": "TR_MONSTER_VAR_01",
        "hound_fire": "TR_MONSTER_VAR_01",
        "guard_dog": "TR_MONSTER_VAR_01",
        "magic_hound": "TR_MONSTER_VAR_01",
        "wolf": "TR_MONSTER_VAR_01",
        "panther": "TR_MONSTER_VAR_02",
        "cat": "TR_MONSTER_VAR_02",
        "tiger": "TR_MONSTER_VAR_02",
        "slime": "TR_MONSTER_01",
        "dragon": "TR_MONSTER_VAR_03",
        "dragon_red": "TR_MONSTER_VAR_03",
    }

    @staticmethod
    def create(name: str, x: int, y: int) -> Entity:
        from config_manager import DataCache
        from ecs.entity import Attributes, Entity

        m_data = DataCache.get_data("data/monsters.yaml")
        if m_data and name in m_data:
            entry = m_data[name]
            attr_dict = entry.get("attributes", {})
            attr = Attributes(
                strength=attr_dict.get("strength", 10),
                endurance=attr_dict.get("endurance", 10),
                dexterity=attr_dict.get("dexterity", 10),
                perception=attr_dict.get("perception", 10),
                learning=attr_dict.get("learning", 10),
                will=attr_dict.get("will", 10),
                magic=attr_dict.get("magic", 10),
                charisma=attr_dict.get("charisma", 10),
            )
            e = Entity(
                x=x,
                y=y,
                char=entry.get("char", "👾"),
                color=tuple(entry.get("color", [255, 255, 255])),
                name=entry.get("name", name),
                speed=entry.get("speed", 70),
                attributes=attr,
            )
            e.max_hp = entry.get("max_hp", 20)
            e.hp = e.max_hp
            e.faction = FACTION_MONSTER
            e.aggro = AggroList()
            e.resistances = ResistanceSet()
            e.status_effects = []
            # Store monster type for tile rendering
            e.monster_type = name
            return e

        # フォールバック
        presets = {
            "slime": (
                "ぷち",
                "🍮",
                (100, 255, 100),
                50,
                Attributes(strength=5, endurance=6, dexterity=6),
            ),
            "goblin": (
                "ゴブリン",
                "👺",
                (200, 100, 50),
                70,
                Attributes(strength=8, endurance=8, dexterity=8),
            ),
            "orc": (
                "オーク",
                "👹",
                (150, 150, 50),
                65,
                Attributes(strength=14, endurance=12, dexterity=6),
            ),
        }
        if name not in presets:
            return Entity(x, y, "👾", (255, 255, 255), "モンスター")
        n, c, col, spd, attr = presets[name]
        e = Entity(x, y, c, col, n, speed=spd, attributes=attr)
        hp_map = {"slime": 14, "goblin": 24, "orc": 42}
        e.max_hp = hp_map.get(name, 20)
        e.hp = e.max_hp
        e.faction = FACTION_MONSTER
        e.aggro = AggroList()
        e.resistances = ResistanceSet()
        e.status_effects = []
        e.monster_type = name
        return e


# --- LocalizationManager integration (i18n, Step 3.x) ---
from localization_manager import localize  # noqa: E402,F401

logger = logging.getLogger(__name__)
