"""
Elona Masterpiece Edition - Crafting and Salvage System
Steps 7-10: Item breakdown, recipe management, material consumption, and crafting execution.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from constants import (
    CRAFT_CRIT_CHANCE,
    CRAFT_SUCCESS_BASE,
    CRAFT_SUCCESS_SKILL_BONUS,
    MATERIAL_NAMES,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_LABELS,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from data.generated.item.recipe import RecipeDefinition
from data_manager import DataManager
from item_generator import ItemGenerator
from item_system import Item

if TYPE_CHECKING:
    from ecs.entity import Entity


class CraftingSystem:
    """クラフト・アイテム分解システム"""

    def __init__(self, data_manager: DataManager | None = None, item_generator: ItemGenerator | None = None):
        self.data_manager = data_manager or DataManager()
        self.item_generator = item_generator or ItemGenerator(self.data_manager)

    def get_inventory_material_counts(self, entity: Entity) -> dict[str, int]:
        """プレイヤーのインベントリ内の素材・アイテム数を集計"""
        counts: dict[str, int] = {}
        if not hasattr(entity, "inventory") or not entity.inventory:
            return counts

        for item in entity.inventory.items:
            # item.item_id をキーとして集計 (例: "item_iron_ingot", "longsword" など)
            item_key = getattr(item, "item_id", "") or item.name
            counts[item_key] = counts.get(item_key, 0) + getattr(item, "count", 1)

            # item.name でも引けるようにエイリアス保持
            if item.name != item_key:
                counts[item.name] = counts.get(item.name, 0) + getattr(item, "count", 1)

        return counts

    def can_craft(self, entity: Entity, recipe_id: str) -> tuple[bool, str, dict[str, int]]:
        """指定レシピがクラフト可能か判定 (Step 9)"""
        recipe: RecipeDefinition | None = self.data_manager.recipes.get(recipe_id)
        if not recipe:
            return False, f"レシピ '{recipe_id}' が見つかりません。", {}

        mat_counts = self.get_inventory_material_counts(entity)
        missing: dict[str, int] = {}

        for mat_id, req_count in recipe.required_materials.items():
            current_count = mat_counts.get(mat_id, 0)
            if current_count < req_count:
                missing[mat_id] = req_count - current_count

        if missing:
            missing_names = []
            for mat_id, diff in missing.items():
                item_def = self.data_manager.items.get(mat_id)
                mat_name = item_def.name if item_def else MATERIAL_NAMES.get(mat_id, mat_id)
                missing_names.append(f"{mat_name} x{diff}")
            return False, f"素材が不足しています: {', '.join(missing_names)}", missing

        return True, "製作可能です。", {}

    def craft_item(self, entity: Entity, recipe_id: str) -> tuple[bool, Item | None, str]:
        """素材を消費してアイテムをクラフト (Step 10)"""
        can, reason, _ = self.can_craft(entity, recipe_id)
        if not can:
            return False, None, reason

        recipe: RecipeDefinition = self.data_manager.recipes.get(recipe_id)

        # 素材をインベントリから消費
        for mat_id, req_count in recipe.required_materials.items():
            self._consume_material(entity, mat_id, req_count)

        # クラフト品質の判定 (器用さや幸運、会心判定)
        roll = random.random()
        if roll < CRAFT_CRIT_CHANCE:
            crafted_quality = QUALITY_MIRACLE
        elif roll < CRAFT_CRIT_CHANCE * 3:
            crafted_quality = QUALITY_GOOD
        else:
            crafted_quality = QUALITY_NORMAL

        # アイテム生成
        item_def = self.data_manager.items.get(recipe.result_item_id)
        if not item_def:
            return False, None, f"完成品アイテム '{recipe.result_item_id}' のデータが存在しません。"

        crafted_item = self.item_generator.generate_item_from_definition(
            item_def=item_def,
            quality=crafted_quality,
            identified=True,
            dungeon_level=max(1, recipe.difficulty // 2),
        )
        crafted_item.count = recipe.result_count

        # インベントリに追加
        added = entity.inventory.add_item(crafted_item)
        if not added:
            # インベントリがいっぱいの場合は足元にドロップ
            crafted_item.x = entity.x
            crafted_item.y = entity.y
            msg = f"{crafted_item.name} を製作しましたが、荷物が満杯のため足元に置きました。"
        else:
            q_label = QUALITY_LABELS.get(getattr(crafted_item, "quality", QUALITY_NORMAL), "通常")
            msg = f"{crafted_item.name} を製作しました！（品質: {q_label}）"


        return True, crafted_item, msg

    def _consume_material(self, entity: Entity, mat_id: str, amount_to_consume: int) -> None:
        """インベントリから指定素材を指定個数消費"""
        remaining = amount_to_consume
        items_to_remove = []

        for item in entity.inventory.items:
            item_key = getattr(item, "item_id", "") or item.name
            if item_key == mat_id or item.name == mat_id:
                if item.count <= remaining:
                    remaining -= item.count
                    items_to_remove.append(item)
                else:
                    item.count -= remaining
                    remaining = 0
                    break
                if remaining <= 0:
                    break

        for item in items_to_remove:
            entity.inventory.remove_item(item)

    def salvage_item(self, entity: Entity, item: Item) -> tuple[bool, list[dict[str, Any]], str]:
        """アイテムを分解して素材を獲得 (Step 8)"""
        if not item:
            return False, [], "アイテムが指定されていません。"

        if getattr(item, "locked", False):
            return False, [], f"{item.name} はロック保護されているため分解できません。"

        # 装備中か確認
        if hasattr(entity.inventory, "is_equipped") and entity.inventory.is_equipped(item):
            return False, [], f"{item.name} は装備中のため分解できません。"

        # 分解素材の決定
        salvage_mats: dict[str, int] = {}
        item_def = self.data_manager.items.get(getattr(item, "item_id", ""))
        if item_def and item_def.salvage_materials:
            salvage_mats = dict(item_def.salvage_materials)
        elif hasattr(item, "salvage_materials") and item.salvage_materials:
            salvage_mats = dict(item.salvage_materials)
        else:
            # デフォルトの分解ルール（素材に応じたインゴット/木材など）
            mat_type = getattr(item, "material", "iron")
            if mat_type == "wood":
                salvage_mats = {"item_wood_log": 1}
            elif mat_type == "steel":
                salvage_mats = {"item_steel_ingot": 2}
            elif mat_type == "mythril" or mat_type == "mithril":
                salvage_mats = {"mythril_ore": 1}
            elif mat_type == "rubynus" or mat_type == "rubinus":
                salvage_mats = {"item_rubinus_ore": 1}
            elif mat_type == "leather":
                salvage_mats = {"item_leather": 1}
            elif mat_type == "cloth":
                salvage_mats = {"item_cloth": 1}
            else:
                salvage_mats = {"item_iron_ingot": 1}

        # アイテムを1個消費
        item_name = item.name
        if item.count > 1:
            item.count -= 1
        else:
            entity.inventory.remove_item(item)

        # 素材をインベントリに付与
        gained_mats_info = []
        for mat_id, count in salvage_mats.items():
            mat_def = self.data_manager.items.get(mat_id)
            if mat_def:
                mat_item = self.item_generator.generate_item_from_definition(
                    item_def=mat_def,
                    quality=QUALITY_NORMAL,
                    identified=True,
                )
                mat_item.count = count
            else:
                # 定義がなければ汎用素材アイテムを生成
                mat_item = Item(
                    name=MATERIAL_NAMES.get(mat_id, mat_id),
                    category="ore",
                    char="🧱",
                    color=(180, 180, 180),
                    base_weight=1.0,
                    base_value=20,
                    count=count,
                    material=mat_id,
                )
                mat_item.item_id = mat_id

            entity.inventory.add_item(mat_item)
            gained_mats_info.append({
                "mat_id": mat_id,
                "name": mat_item.name,
                "count": count,
            })

        summary = ", ".join([f"{m['name']} x{m['count']}" for m in gained_mats_info])
        msg = f"{item_name} を分解し、[{summary}] を獲得しました。"
        return True, gained_mats_info, msg

    def get_recipes_status(self, entity: Entity) -> list[dict[str, Any]]:
        """クライアントUI表示用のレシピ一覧および作成可否情報を取得"""
        recipes_data = []
        mat_counts = self.get_inventory_material_counts(entity)

        for recipe in self.data_manager.recipes.get_all():
            can_craft_flag, reason, _ = self.can_craft(entity, recipe.id)
            mats_detail = []
            for mat_id, req in recipe.required_materials.items():
                item_def = self.data_manager.items.get(mat_id)
                mat_name = item_def.name if item_def else MATERIAL_NAMES.get(mat_id, mat_id)
                current = mat_counts.get(mat_id, 0)
                mats_detail.append({
                    "mat_id": mat_id,
                    "name": mat_name,
                    "required": req,
                    "current": current,
                    "satisfied": current >= req,
                })

            result_def = self.data_manager.items.get(recipe.result_item_id)
            recipes_data.append({
                "id": recipe.id,
                "name": recipe.name,
                "result_item_id": recipe.result_item_id,
                "result_name": result_def.name if result_def else recipe.result_item_id,
                "result_count": recipe.result_count,
                "category": recipe.category,
                "difficulty": recipe.difficulty,
                "description": recipe.description or "",
                "can_craft": can_craft_flag,
                "materials": mats_detail,
            })

        return recipes_data


# --- 後方互換性定義 (Backward Compatibility) ---
from dataclasses import dataclass, field


@dataclass
class ResourceNode:
    """採掘・採取可能なリソースノード"""
    x: int
    y: int
    node_type: str = "herb"  # "herb", "mushroom", "ore_vein"
    remaining_resources: int = 3
    char: str = "🌲"
    color: tuple[int, int, int] = (100, 200, 100)

    def harvest(self) -> str | None:
        if self.remaining_resources > 0:
            self.remaining_resources -= 1
            if self.node_type == "herb":
                return "item_herb"
            elif self.node_type == "ore_vein":
                return "item_iron_ingot"
            return "item_wood_log"
        return None


@dataclass
class Recipe:
    """旧レシピクラス"""
    id: str
    name: str
    result_item_id: str
    materials: dict[str, int]
    difficulty: int = 10


CRAFTING_RECIPES: dict[str, Recipe] = {
    "recipe_shortsword": Recipe("recipe_shortsword", "短剣の製作", "shortsword", {"item_iron_ingot": 1}),
    "recipe_longsword": Recipe("recipe_longsword", "長剣の製作", "longsword", {"item_iron_ingot": 2, "item_wood_log": 1}),
}


def try_craft(entity: Any, recipe_id: str) -> tuple[bool, Any, str]:
    """旧クラフト互換関数"""
    cs = CraftingSystem()
    return cs.craft_item(entity, recipe_id)
