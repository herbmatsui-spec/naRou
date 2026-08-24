"""
Elona Roguelike - フェーズ4: 高度なアイテム・インベントリシステム
Steps 28-36: UUID, 呪いアイテム, 食料腐敗, 厳密スタック判定, 装備スロットクラス
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

from naRou.constants import (
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_LABELS,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
    QUALITY_VALUE_MULTIPLIERS,
)

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
        category: str,
        char: str,
        color: tuple[int, int, int],
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
        locked: bool = False,  # お気に入り保護・ロックフラグ (ステップ37)
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
        self.locked = locked

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
            and self.category in (CAT_POTION, CAT_SCROLL, CAT_FOOD)
        )

    @property
    def weight(self) -> float:
        mat = MATERIALS.get(self.material, {})
        return round(self.base_weight * mat.get("weight_mult", 1.0) * self.count, 2)

    @property
    def value(self) -> int:
        mat = MATERIALS.get(self.material, {})
        qual_mult = QUALITY_VALUE_MULTIPLIERS.get(self.quality, 1.0)
        return int(self.base_value * mat.get("value_mult", 1.0) * qual_mult * self.count)

    @property
    def enchantments(self) -> list[Any]:
        return list(self.enchants)

    @enchantments.setter
    def enchantments(self, value: Any) -> None:
        self.enchants = tuple(value) if isinstance(value, (list, set)) else tuple(value)

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
        quality_tag = f"({QUALITY_LABELS.get(self.quality, '')})" if self.identified and self.quality != QUALITY_NORMAL else ""
        count_str = f" x{self.count}" if self.count > 1 else ""
        return f"{curse_tag}{prefix}{self.name}{quality_tag}{id_tag}{count_str} [{self.weight}s]"

    def to_dict(self) -> dict[str, Any]:
        """辞書形式シリアライズ (Step 22 & Step 16)"""
        ench_list = []
        for e in self.enchants:
            if hasattr(e, "model_dump"):
                ench_list.append(e.model_dump())
            elif isinstance(e, dict):
                ench_list.append(e)
            else:
                ench_list.append(str(e))

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
            "locked": self.locked,
            "enchants": ench_list,
            "rot_progress": self.rot_progress,
            "is_cooling": self.is_cooling,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Item:
        """辞書形式デシリアライズ (Step 22 & Step 16 & Step 37)"""
        ench_raw = data.get("enchants", ())
        ench_instances = []
        for e in ench_raw:
            if isinstance(e, dict) and "id" in e and "type" in e:
                try:
                    from data.generated.item.enchantment import ItemEnchantmentInstance
                    ench_instances.append(ItemEnchantmentInstance.model_validate(e))
                except Exception:
                    ench_instances.append(e)
            else:
                ench_instances.append(e)

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
            enchants=tuple(ench_instances),
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

    def get_equipped_items(self) -> list[Item]:
        """装備中の全アイテムを取得"""
        return [s.item for s in self.slots if s.item is not None]

    def get_total_pv(self) -> int:
        """装備品による合計PV (Step 14)"""
        return sum(item.pv for item in self.get_equipped_items())

    def get_total_dv(self) -> int:
        """装備品による合計DV (Step 14)"""
        return sum(item.dv for item in self.get_equipped_items())

    def get_total_hit_bonus(self) -> int:
        """装備品による合計命中補正 (Step 15)"""
        return sum(item.hit_bonus for item in self.get_equipped_items())

    def get_total_dmg_bonus(self) -> int:
        """装備品による合計ダメージ補正 (Step 13)"""
        return sum(item.dmg_bonus for item in self.get_equipped_items())

    def get_stat_bonuses(self) -> dict[str, int]:
        """エンチャントによる能力値ボーナス (Step 13, 14)"""
        bonuses: dict[str, int] = {}
        for item in self.get_equipped_items():
            for ench in item.enchantments:
                if getattr(ench, "type", "") == "stat_bonus" and getattr(ench, "target_stat", None):
                    t_stat = ench.target_stat
                    bonuses[t_stat] = bonuses.get(t_stat, 0) + getattr(ench, "power", 0)
                elif isinstance(ench, dict) and ench.get("type") == "stat_bonus" and ench.get("target_stat"):
                    t_stat = ench["target_stat"]
                    bonuses[t_stat] = bonuses.get(t_stat, 0) + ench.get("power", 0)
        return bonuses

    def get_elemental_resistances(self) -> dict[str, int]:
        """エンチャントによる属性耐性ボーナス (Step 14, 56)"""
        res: dict[str, int] = {}
        for item in self.get_equipped_items():
            for ench in item.enchantments:
                if getattr(ench, "type", "") == "resistance" and getattr(ench, "element", None):
                    elem = ench.element
                    res[elem] = res.get(elem, 0) + getattr(ench, "power", 0)
                elif isinstance(ench, dict) and ench.get("type") == "resistance" and ench.get("element"):
                    elem = ench["element"]
                    res[elem] = res.get(elem, 0) + ench.get("power", 0)
        return res

    def get_weapon_element_damages(self) -> list[tuple[str, int]]:
        """利き手武器の属性追加ダメージ一覧 (Step 13, 55)"""
        main_hand = self.get_slot("main_hand")
        if not main_hand or not main_hand.item:
            return []
        damages = []
        for ench in main_hand.item.enchantments:
            if getattr(ench, "type", "") == "element_damage" and getattr(ench, "element", None):
                damages.append((ench.element, getattr(ench, "power", 0)))
            elif isinstance(ench, dict) and ench.get("type") == "element_damage" and ench.get("element"):
                damages.append((ench["element"], ench.get("power", 0)))
        return damages

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

    def toggle_lock(self, item: Item) -> bool:
        """アイテムのお気に入り保護（ロック）トグル (Step 37)"""
        item.locked = not item.locked
        return item.locked

    def can_sell(self, item: Item) -> tuple[bool, str]:
        """売却可能かどうかの判定 (Step 40)"""
        if item.locked:
            return False, f"{item.display_name} はお気に入り保護されているため売却できません。"
        return True, ""

    def can_destroy(self, item: Item) -> tuple[bool, str]:
        """破棄可能かどうかの判定 (Step 40)"""
        if item.locked:
            return False, f"{item.display_name} はお気に入り保護されているため破棄できません。"
        return True, ""

    def filter_items(self, category: str | None = None) -> list[Item]:
        """カテゴリ別アイテム抽出 (Step 30)"""
        if not category or category == "all":
            return list(self.items)
        if category == "equipment":
            return [i for i in self.items if i.category in (CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_HELM, CAT_RING)]
        elif category == "consumable":
            return [i for i in self.items if i.category in (CAT_POTION, CAT_SCROLL, CAT_FOOD, CAT_SPELLBOOK)]
        elif category == "valuable":
            return [i for i in self.items if i.category in (CAT_ORE, CAT_GOLD) or getattr(i, "quality", "") in (QUALITY_MIRACLE, QUALITY_GOD)]
        return [i for i in self.items if i.category == category]

    def sort_items(self, items: list[Item] | None = None, key: str = "default", reverse: bool = False) -> list[Item]:
        """各種キーによるソート (Step 31-34, 39: ロック品最優先固定)"""
        target_list = list(items if items is not None else self.items)

        quality_order = {
            QUALITY_BAD: 0,
            QUALITY_NORMAL: 1,
            QUALITY_GOOD: 2,
            QUALITY_MIRACLE: 3,
            QUALITY_GOD: 4,
        }

        if key == "name":
            target_list.sort(key=lambda i: i.name, reverse=reverse)
        elif key == "weight":
            target_list.sort(key=lambda i: i.weight, reverse=reverse)
        elif key == "value":
            target_list.sort(key=lambda i: i.value, reverse=reverse)
        elif key == "quality":
            target_list.sort(key=lambda i: quality_order.get(i.quality, 1), reverse=reverse)
        elif key == "category":
            target_list.sort(key=lambda i: i.category, reverse=reverse)

        # ステップ39: ロックされているアイテムを常に最上位に配置
        target_list.sort(key=lambda i: 0 if i.locked else 1)

        return target_list

    def tick_food_rot(self, ticks: int = 1) -> list[str]:
        """所持食料の腐敗進行 (ステップ35)"""
        logs = []
        for item in self.items:
            msg = item.tick_rot(ticks)
            if msg:
                logs.append(msg)
        return logs


def create_sample_item(name: str, x: int = 0, y: int = 0) -> Item:
    """デバッグ・生成用アイテムプリセット (外部YAMLデータ連携 & 絵文字対応)"""
    from naRou.config_manager import DataCache

    items_data = DataCache.get_data("data/items.yaml")

    if items_data and name in items_data:
        d = items_data[name]
        return Item(
            name=d.get("name", name),
            category=d.get("category", CAT_WEAPON),
            char=d.get("char", "🗡️"),
            color=tuple(d.get("color", [200, 200, 200])),
            x=x,
            y=y,
            base_weight=float(d.get("base_weight", 1.0)),
            base_value=int(d.get("base_value", 10)),
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
    return presets.get(name, presets["longsword"])


def calculate_reincarnation_drop_rate(base_rate: float, player_reinc_count: int) -> float:
    """転生ドロップスケーリング適用 (Steps 55, 56)"""
    bonus_mult = min(3.0, 1.0 + player_reinc_count * 0.10)
    return base_rate * bonus_mult


def use_item(user: Any, item: Item) -> tuple[bool, str]:
    """アイテム使用処理 (ポーション、巻物、食料等) (Step 64)"""
    if item.category == CAT_POTION:
        if item.heal_amount > 0:
            user.hp = min(getattr(user, "max_hp", 9999), user.hp + item.heal_amount)
            return True, f"{user.name}は{item.name}を飲み、HPが{item.heal_amount}回復した！"
        elif "毒消し" in item.name or "cure_poison" in getattr(item, "item_id", "") or item.name == "毒消しのポーション":
            cured = False
            if hasattr(user, "remove_status"):
                c1 = user.remove_status("poison")
                c2 = user.remove_status("burn")
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

