"""
Elona Masterpiece Edition - Random Item & Enchantment Generator
Steps 8-12: Quality rolling, enchantment selection, power scaling, and random item factory.
"""

from __future__ import annotations

import random
from typing import Any

from naRou.constants import (
    ALL_QUALITIES,
    CAT_ARMOR,
    CAT_HELM,
    CAT_RING,
    CAT_SHIELD,
    CAT_WEAPON,
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from naRou.data_manager import DataManager

from data.generated.item.enchantment import EnchantmentDefinition, ItemEnchantmentInstance
from data.generated.item.item import ItemDefinition
from item_system import Item


class ItemGenerator:
    """ランダムアイテム・エンチャント生成エンジン"""

    def __init__(self, data_manager: DataManager | None = None):
        self.data_manager = data_manager or DataManager()

    def roll_quality(self, dungeon_level: int = 1, luck_bonus: float = 0.0) -> str:
        """ダンジョン深度と幸運補正に基づく品質抽選 (Step 9)"""
        # 深度による重み補正
        w_bad = max(2.0, 10.0 - dungeon_level * 0.2)
        w_normal = max(30.0, 60.0 - dungeon_level * 0.5)
        w_good = 22.0 + dungeon_level * 0.4 + luck_bonus * 2.0
        w_miracle = 7.0 + dungeon_level * 0.25 + luck_bonus * 1.5
        w_god = 1.0 + dungeon_level * 0.1 + luck_bonus * 0.8

        qualities = [QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD]
        weights = [w_bad, w_normal, w_good, w_miracle, w_god]

        return random.choices(qualities, weights=weights, k=1)[0]

    def get_enchant_count(self, quality: str) -> int:
        """品質に応じたエンチャント付与数決定 (Step 10)"""
        if quality == QUALITY_BAD:
            return 0
        elif quality == QUALITY_NORMAL:
            return 1 if random.random() < 0.10 else 0
        elif quality == QUALITY_GOOD:
            return random.randint(1, 2)
        elif quality == QUALITY_MIRACLE:
            return random.randint(2, 4)
        elif quality == QUALITY_GOD:
            return random.randint(4, 6)
        return 0

    def generate_enchantments_for_item(
        self,
        category: str,
        quality: str,
        count: int | None = None,
    ) -> list[ItemEnchantmentInstance]:
        """アイテムカテゴリと品質に応じたエンチャント選定と威力計算 (Step 11)"""
        if count is None:
            count = self.get_enchant_count(quality)
        if count <= 0:
            return []

        # カテゴリに適用可能なエンチャントを抽出
        available_enchants = self.data_manager.enchantments.get_for_category(category)
        if not available_enchants:
            return []

        # 品質制限フィルタ
        quality_rank = {
            QUALITY_BAD: 0,
            QUALITY_NORMAL: 1,
            QUALITY_GOOD: 2,
            QUALITY_MIRACLE: 3,
            QUALITY_GOD: 4,
        }
        item_rank = quality_rank.get(quality, 1)

        candidate_enchants = [
            e for e in available_enchants
            if quality_rank.get(getattr(e, "min_quality", "good"), 2) <= item_rank
        ]

        if not candidate_enchants:
            candidate_enchants = available_enchants

        # 重複なしで選択 (プール数より多ければ許容)
        k = min(count, len(candidate_enchants))
        selected_defs = random.sample(candidate_enchants, k=k)

        instances: list[ItemEnchantmentInstance] = []
        for ench_def in selected_defs:
            p_range = getattr(ench_def, "power_range", [1, 5])
            min_p = p_range[0] if len(p_range) > 0 else 1
            max_p = p_range[1] if len(p_range) > 1 else min_p

            base_power = random.randint(min_p, max_p)

            # 高品質ボーナス
            if quality == QUALITY_MIRACLE:
                base_power = max(min_p, int(base_power * 1.25) + 1)
            elif quality == QUALITY_GOD:
                base_power = max(min_p, int(base_power * 1.6) + 2)

            inst = ItemEnchantmentInstance(
                id=ench_def.id,
                name=ench_def.name,
                type=ench_def.type,
                power=base_power,
                target_stat=getattr(ench_def, "target_stat", None),
                element=getattr(ench_def, "element", None),
            )
            instances.append(inst)

        return instances

    def create_item(
        self,
        template_id: str,
        quality: str | None = None,
        dungeon_level: int = 1,
        identified: bool = True,
        material: str | None = None,
    ) -> Item:
        """指定テンプレートからのアイテム生成 (Step 12)"""
        item_def = self.data_manager.items.get(template_id)
        if not item_def:
            raise KeyError(f"Item template '{template_id}' not found.")

        final_quality = quality if quality is not None else self.roll_quality(dungeon_level)
        final_material = material or item_def.material or "iron"

        cat_str = item_def.category.value if hasattr(item_def.category, "value") else str(item_def.category)

        # 装備品カテゴリであればエンチャント抽選
        is_equip = cat_str in (CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_HELM, CAT_RING)
        enchants: list[ItemEnchantmentInstance] = []
        if is_equip:
            enchants = self.generate_enchantments_for_item(cat_str, final_quality)

        # 品質による基礎ステータス補正
        hit_bonus = item_def.hit_bonus or 0
        dmg_bonus = item_def.dmg_bonus or 0
        pv = item_def.pv or 0
        dv = item_def.dv or 0

        if final_quality == QUALITY_BAD:
            hit_bonus -= 1
            dmg_bonus = max(0, dmg_bonus - 1)
            pv = max(0, pv - 1)
        elif final_quality == QUALITY_GOOD:
            hit_bonus += 1
            dmg_bonus += 1
            pv += 1
        elif final_quality == QUALITY_MIRACLE:
            hit_bonus += 2
            dmg_bonus += 2
            pv += 2
            dv += 1
        elif final_quality == QUALITY_GOD:
            hit_bonus += 4
            dmg_bonus += 4
            pv += 5
            dv += 2

        # エンチャントからの直接補正加算
        for ench in enchants:
            if ench.type == "combat_bonus" and ench.target_stat:
                if ench.target_stat == "pv":
                    pv += ench.power
                elif ench.target_stat == "dv":
                    dv += ench.power
                elif ench.target_stat == "hit_bonus":
                    hit_bonus += ench.power
                elif ench.target_stat == "dmg_bonus":
                    dmg_bonus += ench.power

        # Item インスタンス生成
        item = Item(
            name=item_def.name,
            category=cat_str,
            char=item_def.char or "?",
            color=tuple(item_def.color or [255, 255, 255]),
            base_weight=item_def.base_weight or 1.0,
            base_value=item_def.base_value or 10,
            count=1,
            material=final_material,
            quality=final_quality,
            identified=identified,
            dice_num=item_def.dice_num or 1,
            dice_side=item_def.dice_side or 6,
            hit_bonus=hit_bonus,
            dmg_bonus=dmg_bonus,
            pv=pv,
            dv=dv,
            heal_amount=item_def.heal_amount or 0,
            nutrition=item_def.nutrition or 0,
            spell_id=item_def.spell_id or "",
            sp_stock=item_def.sp_stock or 0,
            cursed=(final_quality == QUALITY_BAD and random.random() < 0.4),
            enchants=tuple(enchants),
        )
        item.item_id = template_id
        return item

    def generate_item_from_definition(
        self,
        item_def: ItemDefinition,
        quality: str | None = None,
        dungeon_level: int = 1,
        identified: bool = True,
        material: str | None = None,
    ) -> Item:
        """ItemDefinitionインスタンスからの直接アイテム生成"""
        template_id = getattr(item_def, "id", None)
        if not template_id or template_id not in self.data_manager.items._data:
            for k, v in self.data_manager.items._data.items():
                if v == item_def or v.name == item_def.name:
                    template_id = k
                    break
        if not template_id:
            template_id = "longsword"
        return self.create_item(
            template_id=template_id,
            quality=quality,
            dungeon_level=dungeon_level,
            identified=identified,
            material=material,
        )

    def generate_random_item(
        self,
        dungeon_level: int = 1,
        category: str | None = None,
        luck_bonus: float = 0.0,
        identified: bool = True,
    ) -> Item:
        """ランダムアイテム生成 (Step 12)"""
        if category:
            candidates = self.data_manager.items.get_by_category(category)
        else:
            candidates = list(self.data_manager.items._data.values())

        if not candidates:
            # フォールバック
            candidates = list(self.data_manager.items._data.values())

        chosen_def = random.choice(candidates)
        # ID特定 (items._data のキーから探す)
        template_id = "longsword"
        for k, v in self.data_manager.items._data.items():
            if v == chosen_def:
                template_id = k
                break

        quality = self.roll_quality(dungeon_level, luck_bonus)
        return self.create_item(
            template_id=template_id,
            quality=quality,
            dungeon_level=dungeon_level,
            identified=identified,
        )


# グローバルファクトリ関数
_global_item_generator: ItemGenerator | None = None

# item_enchantments.yaml の軽量リポジトリキャッシュ (起動一括ロードを避ける)
_lightweight_enchant_repo: "EnchantmentRepository | None" = None


def _get_lightweight_enchant_repository() -> "EnchantmentRepository":
    """item_enchantments.yaml を DataCache 経由で読んだ EnchantmentRepository を返す。

    DataManager() の全データ一括ロードを避けるための軽量経路。初回呼び出し時に
    構築してキャッシュする。
    """
    global _lightweight_enchant_repo
    if _lightweight_enchant_repo is None:
        from data.repositories.enchantment import EnchantmentRepository

        from config_manager import DataCache

        raw = DataCache.get_data("data/item_enchantments.yaml") or {}
        _lightweight_enchant_repo = EnchantmentRepository(
            {k: EnchantmentDefinition.model_validate(v) for k, v in raw.items()}
        )
    return _lightweight_enchant_repo


class _EnchantOnlyDataManager:
    """エンチャント供給だけを持つ最小アダプタ (ItemGenerator からの参照用)"""

    def __init__(self) -> None:
        self.enchantments = _get_lightweight_enchant_repository()


def roll_enchantments(category: str, quality: str) -> tuple[ItemEnchantmentInstance, ...]:
    """軽量ファクトリ (create_sample_item 等) 向けのエンチャント抽選。

    ItemGenerator と同じ選定ロジック・品質カーブ・威力計算を共有し、
    DataManager の全体ロードを行わない。
    """
    gen = ItemGenerator.__new__(ItemGenerator)
    gen.data_manager = _EnchantOnlyDataManager()  # type: ignore[assignment]
    count = gen.get_enchant_count(quality)
    if count <= 0:
        return ()
    return tuple(gen.generate_enchantments_for_item(category, quality, count=count))


def get_item_generator() -> ItemGenerator:
    global _global_item_generator
    if _global_item_generator is None:
        _global_item_generator = ItemGenerator()
    return _global_item_generator


def generate_random_item(
    dungeon_level: int = 1,
    category: str | None = None,
    luck_bonus: float = 0.0,
    identified: bool = True,
) -> Item:
    """ステップ12: ランダムアイテム生成ショートカット"""
    return get_item_generator().generate_random_item(
        dungeon_level=dungeon_level,
        category=category,
        luck_bonus=luck_bonus,
        identified=identified,
    )
