"""
Elona Roguelike - フェーズ4: 高度なアイテム・インベントリシステム
Steps 28-36: UUID, 呪いアイテム, 食料腐敗, 厳密スタック判定, 装備スロットクラス
"""

from __future__ import annotations

import copy
import random
import uuid
from dataclasses import dataclass
from typing import Any

import yaml

from constants import QUALITY_BAD, QUALITY_GOD, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_NORMAL

# 素材定義
MATERIALS: dict[str, dict[str, Any]] = {
    "wood": {
        "name": "木",
        "weight_mult": 0.8,
        "value_mult": 0.8,
        "hit": 0,
        "dmg": 0,
        "pv": 0,
        "dv": 0,
    },
    "iron": {
        "name": "鉄",
        "weight_mult": 1.0,
        "value_mult": 1.0,
        "hit": 0,
        "dmg": 1,
        "pv": 1,
        "dv": 0,
    },
    "steel": {
        "name": "鋼鉄",
        "weight_mult": 1.1,
        "value_mult": 1.4,
        "hit": 1,
        "dmg": 2,
        "pv": 3,
        "dv": 1,
    },
    "mithril": {
        "name": "ミスリル",
        "weight_mult": 0.7,
        "value_mult": 2.2,
        "hit": 2,
        "dmg": 3,
        "pv": 4,
        "dv": 3,
    },
    "rubynus": {
        "name": "ルビナス",
        "weight_mult": 1.2,
        "value_mult": 3.0,
        "hit": 3,
        "dmg": 5,
        "pv": 6,
        "dv": 0,
    },
    "emerald": {
        "name": "エメラルド",
        "weight_mult": 0.9,
        "value_mult": 2.8,
        "hit": 2,
        "dmg": 2,
        "pv": 3,
        "dv": 5,
    },
}

# アイテムカテゴリ文字列
CAT_WEAPON = "weapon"
CAT_SHIELD = "shield"
CAT_HELM = "helm"
CAT_ARMOR = "armor"
CAT_RING = "ring"
CAT_POTION = "potion"
CAT_SCROLL = "scroll"
CAT_FOOD = "food"
CAT_SPELLBOOK = "spellbook"
CAT_TOOL = "tool"
CAT_ROD = "rod"
CAT_ORE = "ore"
CAT_GOLD = "gold"


class Item:
    """UUID付き厳密なアイテムクラス (ステップ28, 29, 32, 35, 36)"""

    def __init__(
        self,
        name: str,
        category: str = CAT_TOOL,
        char: str = '?',
        color: tuple[int, int, int] = (255, 255, 255),
        x: int = 0,
        y: int = 0,
        base_weight: float = 1.0,
        base_value: int = 10,
        count: int = 1,
        material: str = "iron",
        quality: str = QUALITY_NORMAL,
        identified: bool = True,
        dice_num: int = 1,
        dice_side: int = 6,
        hit_bonus: int = 0,
        dmg_bonus: int = 0,
        pv: int = 0,
        dv: int = 0,
        heal_amount: int = 0,
        nutrition: int = 0,
        spell_id: str = "",
        sp_stock: int = 0,
        cursed: bool = False,  # 呪いフラグ (ステップ32)
        enchants: tuple[str, ...] = (),  # エンチャント (スタック判定用: ステップ29)
        sell_price: int | None = None,  # 売却価格 (ステップ26)
        locked: bool = False,  # お気に入りロック (フェーズ2 Step 37)
        description: str = "",  # 説明文 (テスト用追加)
    ):
        self.item_id: str = str(uuid.uuid4())  # 固有ID (ステップ28)
        self.name = name
        self.category = category
        self.char = char
        self.color = color
        self.x = x
        self.y = y
        self.base_weight = base_weight
        self.base_value = base_value
        self.count = count
        self.material = material
        self.quality = quality
        self.identified = identified
        self.dice_num = dice_num
        self.dice_side = dice_side
        self.hit_bonus = hit_bonus
        self.dmg_bonus = dmg_bonus
        self.pv = pv
        self.dv = dv
        self.heal_amount = heal_amount
        self.nutrition = nutrition
        self.spell_id = spell_id
        self.sp_stock = sp_stock
        self.cursed = cursed
        self.enchants = enchants
        self.sell_price = sell_price if sell_price is not None else int(base_value * 0.3)
        self.locked = locked  # お気に入りロック
        self.description = description  # 説明文

        # 食料腐敗システム (ステップ35, 36)
        self.rot_progress: int = 0
        self.is_cooling: bool = False  # クーラーボックス内フラグ

    def tick_rot(self, ticks: int = 1) -> str | None:
        """腐敗の進行 (ステップ35) - cooling中は進まない"""
        if self.category != CAT_FOOD or self.is_cooling:
            return None
        self.rot_progress += ticks
        if self.rot_progress >= 5000 and "腐った" not in self.name:
            self.name = "腐った" + self.name
            self.color = (120, 80, 40)
            self.nutrition = max(0, self.nutrition - 500)
            return f"{self.name} が腐り始めた！"
        return None

    def can_stack_with(self, other: Item) -> bool:
        """厳密なスタック判定 (ステップ29)"""
        return (
            self.name == other.name
            and self.category == other.category
            and self.material == other.material
            and self.quality == other.quality
            and self.cursed == other.cursed
            and self.enchants == other.enchants
            and self.identified == other.identified
            and self.locked == other.locked
            and self.category in (CAT_POTION, CAT_SCROLL, CAT_FOOD)
        )

    @property
    def weight(self) -> float:
        mat = MATERIALS.get(self.material, {})
        return round(self.base_weight * mat.get("weight_mult", 1.0) * self.count, 2)

    @property
    def value(self) -> int:
        mat = MATERIALS.get(self.material, {})
        base = int(self.base_value * mat.get("value_mult", 1.0) * self.count)
        # Quality multiplier
        quality_mult = {
            QUALITY_BAD: 0.5,
            QUALITY_NORMAL: 1.0,
            QUALITY_GOOD: 1.5,
            QUALITY_MIRACLE: 2.5,
            QUALITY_GOD: 4.0,
        }.get(self.quality, 1.0)
        return int(base * quality_mult)

    @property
    def enchantments(self):
        """互換性のためのエイリアス (enchants -> enchantments)"""
        return list(self.enchants)

    @enchantments.setter
    def enchantments(self, value):
        """互換性のためのセッター"""
        self.enchants = tuple(value)

    @property
    def display_name(self) -> str:
        mat = MATERIALS.get(self.material, {})
        mat_name = mat.get("name", "")
        prefix = (
            f"{mat_name}の"
            if mat_name and self.category in (CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_HELM)
            else ""
        )
        curse_tag = "【呪】" if self.cursed else ""
        id_tag = "" if self.identified else "(未鑑定)"
        count_str = f" x{self.count}" if self.count > 1 else ""
        return f"{curse_tag}{prefix}{self.name}{id_tag}{count_str} [{self.weight}s]"

    def to_dict(self) -> dict[str, Any]:
        """辞書形式シリアライズ (Step 22)"""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "char": self.char,
            "color": list(self.color),
            "x": self.x,
            "y": self.y,
            "base_weight": self.base_weight,
            "base_value": self.base_value,
            "sell_price": self.sell_price,
            "count": self.count,
            "material": self.material,
            "quality": self.quality,
            "identified": self.identified,
            "dice_num": self.dice_num,
            "dice_side": self.dice_side,
            "hit_bonus": self.hit_bonus,
            "dmg_bonus": self.dmg_bonus,
            "pv": self.pv,
            "dv": self.dv,
            "heal_amount": self.heal_amount,
            "nutrition": self.nutrition,
            "spell_id": self.spell_id,
            "sp_stock": self.sp_stock,
            "cursed": self.cursed,
            "enchants": list(self.enchants),
            "rot_progress": self.rot_progress,
            "is_cooling": self.is_cooling,
            "locked": self.locked,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Item:
        """辞書形式デシリアライズ (Step 22)"""
        item = cls(
            name=data.get("name", "Unknown Item"),
            category=data.get("category", CAT_TOOL),
            char=data.get("char", "?"),
            color=tuple(data.get("color", [255, 255, 255])),
            x=data.get("x", 0),
            y=data.get("y", 0),
            base_weight=data.get("base_weight", 1.0),
            base_value=data.get("base_value", 10),
            count=data.get("count", 1),
            material=data.get("material", "iron"),
            quality=data.get("quality", QUALITY_NORMAL),
            identified=data.get("identified", True),
            dice_num=data.get("dice_num", 1),
            dice_side=data.get("dice_side", 6),
            hit_bonus=data.get("hit_bonus", 0),
            dmg_bonus=data.get("dmg_bonus", 0),
            pv=data.get("pv", 0),
            dv=data.get("dv", 0),
            heal_amount=data.get("heal_amount", 0),
            nutrition=data.get("nutrition", 0),
            spell_id=data.get("spell_id", ""),
            sp_stock=data.get("sp_stock", 0),
            cursed=data.get("cursed", False),
            enchants=tuple(data.get("enchants", ())),
            sell_price=data.get("sell_price"),
            locked=data.get("locked", False),
        )
        item.item_id = data.get("item_id", item.item_id)
        item.rot_progress = data.get("rot_progress", 0)
        item.is_cooling = data.get("is_cooling", False)
        return item


@dataclass
class EquipmentSlot:
    """装備部位クラス (ステップ30)"""

    slot_name: str  # "main_hand", "off_hand", "head", "body", "ring1", "ring2"
    display_name: str  # 表示名
    item: Item | None = None
    disabled: bool = False  # 変異でスロットが使用不可になる場合

    def can_equip(self, item: Item) -> bool:
        return not self.disabled


class Inventory:
    """厳密なインベントリ管理 (ステップ29, 30, 31, 32, 33)"""

    def __init__(self, max_items: int = 24, max_weight: float = 50.0):
        self.items: list[Item] = []
        self.max_items = max_items
        self.max_weight = max_weight

        # 装備スロットをリストで管理 (ステップ30)
        self.slots: list[EquipmentSlot] = [
            EquipmentSlot("main_hand", "利き手"),
            EquipmentSlot("off_hand", "逆の手"),
            EquipmentSlot("head", "頭"),
            EquipmentSlot("body", "胴体"),
            EquipmentSlot("ring1", "指(右)"),
            EquipmentSlot("ring2", "指(左)"),
        ]

    def get_slot(self, slot_name: str) -> EquipmentSlot | None:
        for s in self.slots:
            if s.slot_name == slot_name:
                return s
        return None

    @property
    def equipment(self) -> dict[str, Item | None]:
        """後方互換: dict形式でアクセス可能"""
        return {s.slot_name: s.item for s in self.slots}

    @property
    def total_weight(self) -> float:
        return round(sum(i.weight for i in self.items), 2)

    def is_overburdened(self) -> bool:
        return self.total_weight > self.max_weight

    def add_item(self, item: Item) -> tuple[bool, str]:
        """スタック判定付きアイテム追加"""
        for existing in self.items:
            if existing.can_stack_with(item):
                existing.count += item.count
                return True, f"{item.display_name} をスタックした。(x{existing.count})"

        if len(self.items) >= self.max_items:
            return False, "荷物がいっぱいで持てない！"

        self.items.append(item)
        return True, f"{item.display_name} を手に入れた。"

    def remove_item(self, item: Item, count: int = 1) -> Item | None:
        if item not in self.items:
            return None
        for slot in self.slots:
            if slot.item is item:
                ok, _ = self.unequip(item)
                if not ok:
                    return None
                break
        if item.count <= count:
            self.items.remove(item)
            return item
        else:
            item.count -= count
            dropped = copy.copy(item)
            dropped.item_id = str(uuid.uuid4())
            dropped.count = count
            return dropped

    def equip(self, item: Item, slot_name: str) -> tuple[bool, str]:
        """装備処理 (呪い・スロット無効チェック含む)"""
        slot = self.get_slot(slot_name)
        if not slot:
            return False, "無効なスロット。"
        if slot.disabled:
            return False, f"{slot.display_name}スロットは変異で使えない！"
        if slot.item:
            ok, msg = self.unequip(slot.item)
            if not ok:
                return False, msg
        slot.item = item
        return True, f"{item.display_name} を装備した。"

    def unequip(self, item: Item) -> tuple[bool, str]:
        """装備解除 (呪いアイテムは解除不可: ステップ32)"""
        if item.cursed:
            return False, f"{item.display_name} は呪われており外せない！"
        for slot in self.slots:
            if slot.item is item:
                slot.item = None
                return True, f"{item.display_name} を外した。"
        return False, "装備されていない。"

    def tick_food_rot(self, ticks: int = 1) -> list[str]:
        """所持食料の腐敗進行 (ステップ35)"""
        logs = []
        for item in self.items:
            msg = item.tick_rot(ticks)
            if msg:
                logs.append(msg)
        return logs

    # ==================== Filter / Sort / Lock (Phase 2 Steps 37-40) ====================

    def filter_items(self, category_filter: str) -> list[Item]:
        """カテゴリ別フィルタリング

        Args:
            category_filter: "weapon", "armor", "shield", "equipment" (weapon+armor+shield+ring+helm),
                           "consumable" (potion+scroll+food+spellbook), "tool", "rod", "ore", "gold"
        """
        # Equipment categories
        equipment_cats = {CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_HELM, CAT_RING}
        consumable_cats = {CAT_POTION, CAT_SCROLL, CAT_FOOD, CAT_SPELLBOOK}

        if category_filter == "equipment":
            return [item for item in self.items if item.category in equipment_cats]
        elif category_filter == "consumable":
            return [item for item in self.items if item.category in consumable_cats]
        else:
            # Single category match
            return [item for item in self.items if item.category == category_filter]

    def sort_items(self, key: str = "name", reverse: bool = False) -> list[Item]:
        """各種キーによるソート

        Args:
            key: "name", "value", "weight", "quality"
            reverse: True for descending, False for ascending
        """
        quality_order = {
            QUALITY_GOD: 5,
            QUALITY_MIRACLE: 4,
            QUALITY_GOOD: 3,
            QUALITY_NORMAL: 2,
            QUALITY_BAD: 1,
        }

        def sort_key(item: Item):
            if key == "name":
                return item.name
            elif key == "value":
                return item.value
            elif key == "weight":
                return item.weight
            elif key == "quality":
                return quality_order.get(item.quality, 0)
            else:
                return item.name

        # Locked items always come first
        locked_items = [item for item in self.items if item.locked]
        unlocked_items = [item for item in self.items if not item.locked]

        locked_sorted = sorted(locked_items, key=sort_key, reverse=reverse)
        unlocked_sorted = sorted(unlocked_items, key=sort_key, reverse=reverse)

        return locked_sorted + unlocked_sorted

    def can_sell(self, item: Item) -> tuple[bool, str]:
        """売却可能かチェック（ロック・呪い・装備中は不可）"""
        if item.locked:
            return False, "ロックされているため売却できません（保護中）。"
        if item.cursed:
            return False, "呪われているため売却できません。"
        # Check if equipped
        for slot in self.slots:
            if slot.item is item:
                return False, "装備中のため売却できません。"
        return True, ""

    def can_destroy(self, item: Item) -> tuple[bool, str]:
        """破棄可能かチェック（ロックは不可、呪いは可能）"""
        if item.locked:
            return False, "ロックされているため破棄できません（保護中）。"
        # Check if equipped
        for slot in self.slots:
            if slot.item is item:
                return False, "装備中のため破棄できません。"
        return True, ""

    def toggle_lock(self, item: Item) -> bool:
        """ロック切り替え - 戻り値はロック後の状態"""
        if item in self.items:
            item.locked = not item.locked
            return item.locked
        return False

    def get_stat_bonuses(self) -> dict[str, int]:
        """装備中のアイテムからステータスボーナスを集計（エンチャント含む）"""
        bonuses: dict[str, int] = {}
        for slot in self.slots:
            item = slot.item
            if item:
                # エンチャントからステータスボーナスを集計 (enchants と enchantments の両方に対応)
                # 旧セーブの文字列エンチャントは type を持たないためスキップする
                for ench in getattr(item, "enchants", ()) or getattr(item, "enchantments", ()):
                    ench_type = getattr(ench, "type", None)
                    if ench_type == "stat_bonus" and ench.target_stat:
                        bonuses[ench.target_stat] = bonuses.get(ench.target_stat, 0) + ench.power
                    elif ench_type == "combat_bonus" and ench.target_stat:
                        # combat_bonusもステータスとして扱う
                        bonuses[ench.target_stat] = bonuses.get(ench.target_stat, 0) + ench.power
        return bonuses

    def get_weapon_element_damages(self) -> list[tuple[str, int]]:
        """メインハンド武器の属性ダメージを取得"""
        result: list[tuple[str, int]] = []
        main_hand_slot = self.get_slot("main_hand")
        if main_hand_slot and main_hand_slot.item:
            weapon = main_hand_slot.item
            # 旧セーブの文字列エンチャントは type を持たないためスキップする
            for ench in getattr(weapon, "enchants", ()) or getattr(weapon, "enchantments", ()):
                if getattr(ench, "type", None) == "element_damage" and ench.element:
                    result.append((ench.element, ench.power))
        return result


def _roll_sample_enchants(category: str) -> tuple:
    """create_sample_item 用の控えめなエンチャント抽選。

    ItemGenerator と同じ品質カーブを共有する (遅延 import: item_generator は
    本モジュールに依存するため循環を避ける)。NORMAL 品質の曲線では
    10% の確率で 1 件付くだけの控えめな初期値。
    """
    if category not in (CAT_WEAPON, CAT_SHIELD, CAT_HELM, CAT_ARMOR, CAT_RING):
        return ()
    try:
        from item_generator import roll_enchantments

        return roll_enchantments(category, QUALITY_NORMAL)
    except Exception:
        return ()


def create_sample_item(name: str, x: int = 0, y: int = 0) -> Item:
    """デバッグ・生成用アイテムプリセット (外部YAMLデータ連携 & 絵文字対応)"""
    from config_manager import DataCache

    items_data = DataCache.get_data("data/items.yaml")

    if items_data and name in items_data:
        d = items_data[name]
        category = d.get("category", CAT_WEAPON)
        return Item(
            name=d.get("name", name),
            category=category,
            char=d.get("char", "🗡️"),
            color=tuple(d.get("color", [200, 200, 200])),
            x=x,
            y=y,
            base_weight=float(d.get("base_weight", 1.0)),
            base_value=int(d.get("base_value", 10)),
            sell_price=d.get("sell_price"),
            material=d.get("material", "iron"),
            dice_num=int(d.get("dice_num", 1)),
            dice_side=int(d.get("dice_side", 6)),
            hit_bonus=int(d.get("hit_bonus", 0)),
            dmg_bonus=int(d.get("dmg_bonus", 0)),
            pv=int(d.get("pv", 0)),
            dv=int(d.get("dv", 0)),
            heal_amount=int(d.get("heal_amount", 0)),
            nutrition=int(d.get("nutrition", 0)),
            spell_id=d.get("spell_id", ""),
            sp_stock=int(d.get("sp_stock", 0)),
            identified=d.get("identified", True),
            enchants=_roll_sample_enchants(category),
        )

    # フォールバック
    presets: dict[str, Item] = {
        "longsword": Item(
            "長剣",
            CAT_WEAPON,
            "🗡️",
            (200, 200, 200),
            x,
            y,
            base_weight=3.5,
            base_value=120,
            dice_num=2,
            dice_side=6,
            hit_bonus=2,
            material="iron",
        ),
        "shortsword": Item(
            "短剣",
            CAT_WEAPON,
            "🗡️",
            (200, 200, 255),
            x,
            y,
            base_weight=1.2,
            base_value=80,
            dice_num=1,
            dice_side=8,
            hit_bonus=4,
            material="iron",
        ),
        "shield": Item(
            "バックラー",
            CAT_SHIELD,
            "🛡️",
            (180, 180, 180),
            x,
            y,
            base_weight=2.0,
            base_value=90,
            pv=2,
            dv=4,
            material="steel",
        ),
        "leather_armor": Item(
            "皮の鎧",
            CAT_ARMOR,
            "🥋",
            (160, 110, 60),
            x,
            y,
            base_weight=4.5,
            base_value=150,
            pv=4,
            dv=2,
            material="wood",
        ),
        "potion_heal": Item(
            "軽傷治療のポーション",
            CAT_POTION,
            "🧪",
            (255, 100, 100),
            x,
            y,
            base_weight=0.3,
            base_value=40,
            heal_amount=35,
            identified=True,
        ),
        "bread": Item(
            "パン",
            CAT_FOOD,
            "🍞",
            (210, 180, 100),
            x,
            y,
            base_weight=0.5,
            base_value=15,
            nutrition=1500,
        ),
        "ration": Item(
            "旅糧",
            CAT_FOOD,
            "🍖",
            (180, 150, 80),
            x,
            y,
            base_weight=1.0,
            base_value=25,
            nutrition=3200,
        ),
        "book_fire": Item(
            "魔矢の魔法書",
            CAT_SPELLBOOK,
            "📘",
            (200, 100, 255),
            x,
            y,
            base_weight=1.5,
            base_value=300,
            spell_id="magic_dart",
            sp_stock=50,
        ),
    }
    item = presets.get(name, presets["longsword"])
    item.enchants = _roll_sample_enchants(item.category)
    return item


def sell(item: Item, gold_holder: Any) -> int:
    """アイテムを売却し、ゴールドを受け取り手に加算する。

    Args:
        item: 売却するアイテム
        gold_holder: gold属性を持つオブジェクト (player, survival_system等)

    Returns:
        獲得したゴールド額
    """
    # YAMLデータからsell_priceを取得、なければbase_valueの30%を使用
    sell_price = getattr(item, 'sell_price', None)
    if sell_price is None:
        sell_price = int(item.base_value * 0.3)

    # スタック数を考慮
    total_gold = sell_price * item.count

    # ゴールドホルダーに加算
    if hasattr(gold_holder, 'gold'):
        gold_holder.gold += total_gold
    elif hasattr(gold_holder, 'add_gold'):
        gold_holder.add_gold(total_gold)
    else:
        raise ValueError("gold_holder must have 'gold' attribute or 'add_gold' method")

    return total_gold


def calculate_reincarnation_drop_rate(base_rate: float, player_reinc_count: int) -> float:
    """転生ドロップスケーリング適用 (Steps 55, 56)"""
    # TODO: Reincarnation drop scaling
    bonus_mult = min(3.0, 1.0 + player_reinc_count * 0.10)
    return base_rate * bonus_mult


# ============================================================
# 接尾辞 (Affix) システム (Phase 3 Step 57-58)
# ============================================================

AFFIXES_YAML_PATH = "data/item_affixes.yaml"


@dataclass(frozen=True)
class Affix:
    """接尾辞定義 (Step 57)

    すべての戦闘系接尾辞は利得と代償の両方を持つ (test_affixes_trade_off_two_ways が強制)。
    呪い系 (cursed=true) は例外で純代償。
    """

    id: str
    name: str
    slot: str  # weapon / armor / any
    weight: int  # 0 = ロール対象外 (呪い)
    tier: int  # 0=呪い, 1=通常, 2=良品, 3=奇跡
    mods: dict[str, int]
    cursed: bool = False

    @property
    def is_curse(self) -> bool:
        return self.cursed


_AFFIX_CACHE: dict[str, Affix] | None = None


def load_affixes(path: str = AFFIXES_YAML_PATH) -> dict[str, Affix]:
    """data/item_affixes.yaml から接尾辞定義を読み込む (キャッシュ付き)"""
    global _AFFIX_CACHE
    if _AFFIX_CACHE is not None:
        return _AFFIX_CACHE
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except OSError:
        raw = {}
    cache: dict[str, Affix] = {}
    for affix_id, body in raw.items():
        if not isinstance(body, dict):
            continue
        cache[affix_id] = Affix(
            id=affix_id,
            name=body.get("name", affix_id),
            slot=body.get("slot", "any"),
            weight=int(body.get("weight", 0)),
            tier=int(body.get("tier", 1)),
            mods=dict(body.get("mods") or {}),
            cursed=bool(body.get("cursed", False)),
        )
    _AFFIX_CACHE = cache
    return cache


def clear_affix_cache() -> None:
    """テスト用: 接尾辞キャッシュをクリア"""
    global _AFFIX_CACHE
    _AFFIX_CACHE = None


def _affix_roll_count(quality: str, rand: Any = None) -> int:
    """品質に応じた接尾辞ロール数 (Step 58.2)

    QUALITY_GOD は必ず2個、QUALITY_NORMAL は確率0.3、QUALITY_BAD は禁止。
    """
    r = rand if rand is not None else random
    if quality == QUALITY_GOD:
        return 2
    if quality in (QUALITY_MIRACLE, QUALITY_GOOD):
        return 1
    if quality == QUALITY_NORMAL:
        return 1 if r.random() < 0.3 else 0
    return 0  # QUALITY_BAD は接尾辞禁止


def roll_affixes(item: Item, rng: Any = None, quality: str | None = None) -> Item:
    """アイテムに接尾辞をロールして付与する (Step 57.3, 58.1)

    Args:
        item: 対象アイテム (破壊的に修正され、返り値でもある)
        rng: 乱数生成器 (None なら random モジュール)
        quality: アイテム品質 (None なら item.quality)

    Returns:
        接尾辞が付与されたアイテム
    """
    r = rng if rng is not None else random
    q = quality if quality is not None else getattr(item, "quality", QUALITY_NORMAL)

    affixes = load_affixes()
    # 呪いはロール対象外 (weight=0)。呪い品は既存 cursed フラグ経路で扱う
    pool = [a for a in affixes.values() if a.weight > 0 and not a.is_curse]
    if not pool:
        return item

    count = _affix_roll_count(q, r)
    applied: list[str] = []
    for _ in range(count):
        candidates = [a for a in pool if a.id not in applied]
        if not candidates:
            break
        total = sum(a.weight for a in candidates)
        pick = r.uniform(0, total)
        acc = 0.0
        chosen = candidates[-1]
        for a in candidates:
            acc += a.weight
            if pick <= acc:
                chosen = a
                break
        applied.append(chosen.id)
        _apply_affix(item, chosen)

    if applied:
        item.affix_ids = tuple(applied)
        suffix_names = "/".join(affixes[a].name for a in applied)
        item.name = f"{item.name} [{suffix_names}]"
    else:
        item.affix_ids = ()
    return item


def _apply_affix(item: Item, affix: Affix) -> None:
    """接尾辞の mods を Item のフィールドへ適用する"""
    mods = affix.mods
    # 数値フィールドへの直接適用 (Item に存在するものだけ)
    field_map = {
        "dmg_bonus": "dmg_bonus",
        "hit_bonus": "hit_bonus",
        "pv": "pv",
        "dv": "dv",
    }
    for key, field in field_map.items():
        if key in mods:
            setattr(item, field, getattr(item, field, 0) + int(mods[key]))

    # 属性系は動的属性として保持 (戦闘解決が参照する)
    dynamic_keys = (
        "str", "endurance", "dexterity", "perception", "learning",
        "will", "magic", "charisma", "speed",
        "hp_regen", "mp_regen", "life_steal", "thorns", "stealth",
        "fire_resist", "cold_resist", "fire_damage", "ice_damage",
        "equip_hp_penalty", "max_hp",
    )
    if getattr(item, "affix_mods", None) is None:
        item.affix_mods = {}
    for key in dynamic_keys:
        if key in mods:
            item.affix_mods[key] = item.affix_mods.get(key, 0) + int(mods[key])


def can_identify(item: Item) -> bool:
    """アイテムが鑑定可能か (Step 60.3)"""
    return not getattr(item, "identified", True)


def identify(item: Item, cost: int, gold_holder: Any = None) -> Item:
    """アイテムを鑑定する (Step 60.2)

    Args:
        item: 鑑定対象
        cost: 鑑定費用 (ゴールド)
        gold_holder: 費用を支払う者 (None なら費用チェック省略)

    Returns:
        鑑定済みアイテム
    """
    if not can_identify(item):
        return item
    if gold_holder is not None:
        if gold_holder.gold < cost:
            return item  # 費用不足: 鑑定されない
        gold_holder.gold -= cost
    item.identified = True
    return item


def use_item(user: Any, item: Item) -> tuple[bool, str]:
    """アイテム使用処理 (ポーション、巻物、食料等) (Step 64)"""
    if item.category == CAT_POTION:
        if item.heal_amount > 0:
            user.hp = min(getattr(user, "max_hp", 9999), user.hp + item.heal_amount)
            return True, f"{user.name}は{item.name}を飲み、HPが{item.heal_amount}回復した！"
        elif "毒消し" in item.name or "cure_poison" in getattr(item, "item_id", "") or item.name == "毒消しのポーション":
            cured = False
            if hasattr(user, "remove_status"):
                # Handle both English (ECS) and Japanese (legacy) status keys
                c1 = user.remove_status("poison") or user.remove_status("毒")
                c2 = user.remove_status("burn") or user.remove_status("炎上")
                cured = c1 or c2
            return True, f"{user.name}は毒消しのポーションを飲み、毒と炎上が治まった！" if cured else f"{user.name}は毒消しのポーションを飲んだ。"
        elif "魔力回復" in item.name or "mana" in getattr(item, "item_id", ""):
            user.mp = min(getattr(user, "max_mp", 9999), getattr(user, "mp", 0) + 40)
            return True, f"{user.name}は魔力回復のポーションを飲み、MPが回復した！"
    elif item.category == CAT_FOOD:
        if hasattr(user, "hunger"):
            user.hunger = min(10000, user.hunger + item.nutrition)
        return True, f"{user.name}は{item.name}を食べた。"
    return False, "使用できないアイテムです。"
