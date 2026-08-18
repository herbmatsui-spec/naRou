"""
Elona Masterpiece Edition - DataManager System (Data-Driven Architecture)
Centralized loading, caching, schema validation, and factory generation for items, monsters, skills, and dungeons.
"""

from __future__ import annotations
import os
import yaml
import json
import random
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from core_framework import BaseSystem
from constants import (
    QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD
)
from item_system import (
    Item, MATERIALS,
    CAT_TOOL
)
from entity import Entity, Attributes

if TYPE_CHECKING:
    from game import Engine


class DataManager(BaseSystem):
    """データ駆動型マネージャー (アイテム・モンスター・スキルの統合ファクトリ)"""
    def __init__(self, data_dir: str = "data"):
        super().__init__()
        self.data_dir = data_dir
        self._cache: Dict[str, Any] = {}
        self.items_data: Dict[str, Any] = {}
        self.monsters_data: Dict[str, Any] = {}
        self.skills_data: Dict[str, Any] = {}
        self.spells_data: Dict[str, Any] = {}
        self.dungeon_themes_data: Dict[str, Any] = {}
        self.materials_data: Dict[str, Any] = dict(MATERIALS)
        self.load_all()

    def initialize(self, engine: "Engine") -> None:
        self.load_all()

    def load_all(self) -> None:
        """全YAML/JSONマスターデータのロード"""
        self.items_data = self._load_file("items.yaml") or {}
        self.monsters_data = self._load_file("monsters.yaml") or {}
        self.skills_data = self._load_file("skill_trees.yaml") or {}
        self.spells_data = self._load_file("spells.yaml") or {}
        self.dungeon_themes_data = self._load_file("dungeon_themes.yaml") or {}

    def _load_file(self, filename: str) -> Any:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    data = yaml.safe_load(f)
                elif filename.endswith(".json"):
                    data = json.load(f)
                else:
                    data = None
                self._cache[filename] = data
                return data
        except Exception as e:
            print(f"[DataManager] Failed to load {filename}: {e}")
            return None

    def get_raw_data(self, filename: str) -> Any:
        if filename in self._cache:
            return self._cache[filename]
        return self._load_file(filename)

    # ==================== ITEM GENERATION ====================

    def create_item(
        self,
        item_id: str,
        x: int = 0,
        y: int = 0,
        material: Optional[str] = None,
        quality: str = QUALITY_NORMAL,
        cursed: bool = False,
        count: int = 1,
        identified: bool = True
    ) -> Item:
        """YAMLデータ定義からItemインスタンスを生成"""
        d = self.items_data.get(item_id)
        if not d:
            # Fallback
            from item_system import create_sample_item
            return create_sample_item(item_id, x, y)

        mat_choice = material or d.get("material", "iron")
        
        # 品質によるボーナス計算
        hit_bonus = int(d.get("hit_bonus", 0))
        dmg_bonus = int(d.get("dmg_bonus", 0))
        pv = int(d.get("pv", 0))
        dv = int(d.get("dv", 0))

        if quality == QUALITY_GOOD:
            hit_bonus += random.randint(1, 3)
            dmg_bonus += random.randint(1, 2)
            pv += 1
        elif quality == QUALITY_MIRACLE:
            hit_bonus += random.randint(3, 7)
            dmg_bonus += random.randint(2, 5)
            pv += random.randint(2, 4)
            dv += random.randint(1, 3)
        elif quality == QUALITY_GOD:
            hit_bonus += random.randint(8, 15)
            dmg_bonus += random.randint(6, 12)
            pv += random.randint(5, 10)
            dv += random.randint(4, 8)
        elif quality == QUALITY_BAD:
            hit_bonus = max(0, hit_bonus - 2)
            dmg_bonus = max(0, dmg_bonus - 1)

        item = Item(
            name=d.get("name", item_id),
            category=d.get("category", CAT_TOOL),
            char=d.get("char", "📦"),
            color=tuple(d.get("color", [200, 200, 200])),
            x=x,
            y=y,
            base_weight=float(d.get("base_weight", 1.0)),
            base_value=int(d.get("base_value", 10)),
            count=count,
            material=mat_choice,
            quality=quality,
            identified=identified,
            dice_num=int(d.get("dice_num", 1)),
            dice_side=int(d.get("dice_side", 6)),
            hit_bonus=hit_bonus,
            dmg_bonus=dmg_bonus,
            pv=pv,
            dv=dv,
            heal_amount=int(d.get("heal_amount", 0)),
            nutrition=int(d.get("nutrition", 0)),
            spell_id=d.get("spell_id", ""),
            sp_stock=int(d.get("sp_stock", 0)),
            cursed=cursed,
        )
        return item

    def get_random_item_for_floor(self, floor_level: int, x: int = 0, y: int = 0) -> Item:
        """フロア深度に応じたアイテムの動的ランダム生成"""
        if not self.items_data:
            from item_system import create_sample_item
            return create_sample_item("potion_heal", x, y)

        candidates = list(self.items_data.keys())
        item_id = random.choice(candidates)

        # 品質抽選 (深い階層ほど奇跡・神器の確率アップ)
        r = random.random()
        god_prob = min(0.05, 0.005 * floor_level)
        miracle_prob = min(0.18, 0.02 * floor_level)
        good_prob = min(0.35, 0.08 * floor_level)

        if r < god_prob:
            quality = QUALITY_GOD
        elif r < god_prob + miracle_prob:
            quality = QUALITY_MIRACLE
        elif r < god_prob + miracle_prob + good_prob:
            quality = QUALITY_GOOD
        elif r > 0.92:
            quality = QUALITY_BAD
        else:
            quality = QUALITY_NORMAL

        # 素材抽選
        materials = list(self.materials_data.keys())
        mat = random.choice(materials) if quality in (QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD) else None

        cursed = (quality == QUALITY_BAD) or (random.random() < 0.05)
        return self.create_item(item_id, x, y, material=mat, quality=quality, cursed=cursed)

    # ==================== MONSTER GENERATION ====================

    def create_monster(
        self,
        monster_id: str,
        x: int = 0,
        y: int = 0,
        level_scale: int = 1,
        faction: str = "monster"
    ) -> Entity:
        """YAMLデータ定義からMonster Entityインスタンスを生成"""
        d = self.monsters_data.get(monster_id)
        if not d:
            # Fallback
            from systems import MonsterPreset
            return MonsterPreset.create(monster_id, x, y)

        attrs_data = d.get("attributes", {})
        scale_mult = 1.0 + (level_scale - 1) * 0.15

        scaled_attrs = Attributes(
            strength=int(attrs_data.get("strength", 10) * scale_mult),
            endurance=int(attrs_data.get("endurance", 10) * scale_mult),
            dexterity=int(attrs_data.get("dexterity", 10) * scale_mult),
            perception=int(attrs_data.get("perception", 10) * scale_mult),
            learning=int(attrs_data.get("learning", 8) * scale_mult),
            will=int(attrs_data.get("will", 8) * scale_mult),
            magic=int(attrs_data.get("magic", 8) * scale_mult),
            charisma=int(attrs_data.get("charisma", 8) * scale_mult),
        )

        base_hp = int(d.get("max_hp", 20) * scale_mult)
        base_speed = int(d.get("speed", 70))

        mob = Entity(
            x=x,
            y=y,
            char=d.get("char", "👾"),
            color=tuple(d.get("color", [200, 200, 200])),
            name=d.get("name", monster_id),
            speed=base_speed,
            attributes=scaled_attrs,
            is_player=False,
            is_pet=False
        )
        mob.max_hp = base_hp
        mob.hp = base_hp
        mob.faction = faction
        mob.ai_type = d.get("ai_type", "aggressive")
        mob.skills = list(d.get("skills", []))
        mob.status_effects = []
        return mob

    def get_random_monster_for_floor(self, floor_level: int, x: int = 0, y: int = 0) -> Entity:
        """フロア深度に応じたモンスターの動的ランダム生成"""
        if not self.monsters_data:
            from systems import MonsterPreset
            return MonsterPreset.create("slime", x, y)

        # 階層に応じたモンスター候補のフィルタ
        tier_pool = []
        for m_id, m_val in self.monsters_data.items():
            min_floor = int(m_val.get("min_floor", 1))
            max_floor = int(m_val.get("max_floor", 999))
            if min_floor <= floor_level <= max_floor + 3:
                tier_pool.append(m_id)

        if not tier_pool:
            tier_pool = list(self.monsters_data.keys())

        chosen_id = random.choice(tier_pool)
        return self.create_monster(chosen_id, x, y, level_scale=floor_level)

    def validate_all_data(self) -> List[str]:
        """全データの整合性バリデーション (スキーマチェック)"""
        errors = []
        # アイテムチェック
        for i_id, i_val in self.items_data.items():
            if "name" not in i_val:
                errors.append(f"Item '{i_id}' missing 'name'")
            if "category" not in i_val:
                errors.append(f"Item '{i_id}' missing 'category'")

        # モンスターチェック
        for m_id, m_val in self.monsters_data.items():
            if "name" not in m_val:
                errors.append(f"Monster '{m_id}' missing 'name'")
            if "max_hp" not in m_val:
                errors.append(f"Monster '{m_id}' missing 'max_hp'")

        return errors


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager
    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
