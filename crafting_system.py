"""
Crafting and Resource Harvesting System Module
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from item_system import Inventory, Item


@dataclass
class ResourceNode:
    """採取ポイント - マップ上の隠れた採取オブジェクト"""

    x: int
    y: int
    node_type: str  # "herb", "ore_vein", "mushroom"
    depleted: bool = False
    replenish_ticks: int = 2000  # 再生までのTick

    NODE_DROPS: dict[str, list[tuple[str, float]]] = field(
        default_factory=lambda: {
            "herb": [("ハーブ", 0.7), ("高級ハーブ", 0.25), ("幻のハーブ", 0.05)],
            "ore_vein": [("鉄鉱石", 0.6), ("銀鉱石", 0.3), ("金鉱石", 0.1)],
            "mushroom": [
                ("毒キノコ", 0.5),
                ("旨いキノコ", 0.35),
                ("カオスマッシュルーム", 0.15),
            ],
        }
    )

    def harvest(self, player: Entity) -> tuple[Item | None, str]:
        """採取実行"""
        from item_system import CAT_FOOD, CAT_ORE, Item

        if self.depleted:
            return None, "もう何もない。"
        self.depleted = True

        drops = self.NODE_DROPS.get(self.node_type, [])
        roll = random.random()
        cumulative = 0.0
        chosen_name = drops[0][0] if drops else "ハーブ"
        for name, prob in drops:
            cumulative += prob
            if roll < cumulative:
                chosen_name = name
                break

        cat = CAT_FOOD if self.node_type != "ore_vein" else CAT_ORE
        itm = Item(
            chosen_name,
            cat,
            "%",
            (150, 220, 120),
            self.x,
            self.y,
            base_weight=0.3,
            base_value=30,
            nutrition=500,
        )
        player.gain_skill_exp("farming", 20)
        return itm, f"採取した！ 【{chosen_name}】を手に入れた。"


@dataclass
class Recipe:
    """素材合成レシピ"""

    result_name: str
    result_category: str
    required_materials: dict[str, int]  # 素材名 -> 個数
    required_skill: str
    required_skill_level: int
    base_value: int = 100
    base_weight: float = 1.0


CRAFTING_RECIPES: dict[str, Recipe] = {
    "basic_potion": Recipe(
        result_name="自家製回復薬",
        result_category="potion",
        required_materials={"高級ハーブ": 2},
        required_skill="cooking",
        required_skill_level=3,
        base_value=80,
        base_weight=0.3,
    ),
    "herb_food": Recipe(
        result_name="ハーブ料理",
        result_category="food",
        required_materials={"ハーブ": 3, "旅糧": 1},
        required_skill="cooking",
        required_skill_level=1,
        base_value=50,
        base_weight=0.8,
    ),
}


def try_craft(
    recipe: Recipe, player: Entity, inventory: Inventory
) -> tuple[bool, str, Item | None]:
    """クラフト実行 + 品質決定"""
    from item_system import QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_NORMAL, Item

    # 素材チェック
    for mat_name, need in recipe.required_materials.items():
        count = sum(i.count for i in inventory.items if i.name == mat_name)
        if count < need:
            return False, f"素材が足りない！ [{mat_name} x{need}]", None

    # スキルチェック
    skill_lv = player.skills.get(recipe.required_skill)
    actual_lv = skill_lv.level if skill_lv else 0
    if actual_lv < recipe.required_skill_level:
        return (
            False,
            f"スキル【{recipe.required_skill}】Lv{recipe.required_skill_level}以上が必要。",
            None,
        )

    # 素材消費
    for mat_name, need in recipe.required_materials.items():
        consumed = 0
        for itm in list(inventory.items):
            if itm.name == mat_name and consumed < need:
                take = min(itm.count, need - consumed)
                inventory.remove_item(itm, count=take)
                consumed += take

    # 品質決定: スキル余裕 + 乱数
    surplus = actual_lv - recipe.required_skill_level
    roll = random.randint(0, 10) + surplus
    if roll >= 15:
        quality = QUALITY_MIRACLE
        color = (255, 220, 100)
    elif roll >= 8:
        quality = QUALITY_GOOD
        color = (180, 255, 180)
    else:
        quality = QUALITY_NORMAL
        color = (200, 200, 200)

    result = Item(
        recipe.result_name,
        recipe.result_category,
        "!",
        color,
        base_weight=recipe.base_weight,
        base_value=recipe.base_value,
        quality=quality,
        heal_amount=35,
        nutrition=2000,
    )

    player.gain_skill_exp(recipe.required_skill, 30)
    return True, f"【{recipe.result_name}】(品質:{quality})を作成した！", result
