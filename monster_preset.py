"""Monster presets and tile mapping."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .combat_core import FACTION_MONSTER, AggroList, ResistanceSet

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity


class MonsterPreset:
    # Map monster names to Tiny Rogue tile IDs.
    # FF6風スプライト (案2/案3) を優先し、未生成種はTiny Rogueへフォールバックする。
    # FF6_* TileDef は assets/tiles/tileset_def_ff6_actors.json 断片由来で、
    # メイン側マージ後のみアトラスに存在する。
    MONSTER_TILE_MAP = {
        "slime": "TR_MONSTER_01",
        "red_slime": "TR_MONSTER_01",
        "snail": "TR_MONSTER_02",
        "goblin": "FF6_GOBLIN",
        "kobold": "FF6_GOBLIN",
        "orc": "TR_MONSTER_03",
        "wolf": "FF6_WOLF",
        "hound_fire": "FF6_WOLF",
        "skeleton": "FF6_SKELETON",
        "bat": "FF6_BAT",
        "giant_bat": "FF6_BAT",
        "rogue_thief": "TR_MONSTER_VAR_02",
        "novice_wizard": "TR_MONSTER_VAR_03",
        "minotaur": "TR_MONSTER_VAR_01",
        "lich": "TR_MONSTER_VAR_02",
        "dragon_red": "TR_MONSTER_VAR_03",
        # 案3: 大型ボス (64x64)
        "void_boss": "FF6_BOSS",
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
        from naRou.config_manager import DataCache
        from naRou.ecs.entity import Attributes, Entity

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
