"""
称号・二つ名システム
データ駆動型で称号の判定・付与・効果適用を行う
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entity import Entity

import yaml


@dataclass
class TitleEffect:
    """称号によるステータス効果"""

    attr: str  # 対象属性名 (strength, damage_vs_goblin 等)
    value: float  # 加算値 or 乗算値
    is_multiplier: bool = False  # Trueなら乗算、Falseなら加算


@dataclass
class TitleCondition:
    """称号獲得条件"""

    type: str  # kill_count, skill_level, dungeon_depth 等
    target: str = ""  # 対象 (モンスターID, スキル名 等)
    count: int = 0  # 必要数
    value: int = 0  # 閾値
    level: int = 0  # スキルレベル等
    category: str = ""  # クラフトカテゴリ等
    min_depth: int = 0  # ダンジョン深度
    max_turns: int = 0  # ターン数制限


@dataclass
class TitleData:
    """称号マスターデータ"""

    id: str
    name: str  # 表示名「ゴブリンスレイヤー」
    epithet: str  # 二つ名「緑皮の悪夢」
    category: str  # kill, explore, skill, survival, faith, wealth, pet, craft, special, milestone
    condition: TitleCondition
    effects: list[TitleEffect]
    message: str  # 獲得時メッセージ
    is_hidden: bool = False  # 獲得前は隠すか


class TitleRegistry:
    """称号レジストリ（シングルトン的）"""

    _instance: TitleRegistry | None = None
    _titles: dict[str, TitleData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path: str = "data/titles.yaml") -> None:
        """YAMLから称号定義を読み込み"""
        if self._loaded:
            return
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for t in data.get("titles", {}).values():
            cond = t["condition"]
            condition = TitleCondition(
                type=cond["type"],
                target=cond.get("target", ""),
                count=cond.get("count", 0),
                value=cond.get("value", 0),
                level=cond.get("level", 0),
                category=cond.get("category", ""),
                min_depth=cond.get("min_depth", 0),
                max_turns=cond.get("max_turns", 0),
            )
            effects = [
                TitleEffect(
                    attr=e["attr"],
                    value=e["value"],
                    is_multiplier=e.get("is_multiplier", False),
                )
                for e in t.get("effects", [])
            ]
            title = TitleData(
                id=t["id"],
                name=t["name"],
                epithet=t["epithet"],
                category=t["category"],
                condition=condition,
                effects=effects,
                message=t["message"],
                is_hidden=t.get("is_hidden", False),
            )
            self._titles[title.id] = title
        self._loaded = True

    def get(self, title_id: str) -> TitleData | None:
        return self._titles.get(title_id)

    def all(self) -> list[TitleData]:
        return list(self._titles.values())

    def by_category(self, category: str) -> list[TitleData]:
        return [t for t in self._titles.values() if t.category == category]


# グローバルアクセス用
REGISTRY = TitleRegistry()


class TitleManager:
    """称号の判定・付与・効果管理"""

    def __init__(self, registry: TitleRegistry = None):
        self.registry = registry or REGISTRY

    # === 条件判定 ===
    def check_kill_count(self, player: Entity, target: str, required: int) -> bool:
        return getattr(player, "kill_counts", {}).get(target, 0) >= required

    def check_skill_level(self, player: Entity, skill: str, level: int) -> bool:
        from entity import Skill

        return player.skills.get(skill, Skill("")).level >= level

    def check_dungeon_depth(self, player: Entity, min_depth: int) -> bool:
        return getattr(player, "max_dungeon_depth", 0) >= min_depth

    def check_near_death(self, player: Entity, count: int) -> bool:
        return getattr(player, "near_death_count", 0) >= count

    def check_piety(self, player: Entity, value: int) -> bool:
        return player.piety >= value

    def check_gold(self, player: Entity, value: int) -> bool:
        return getattr(player, "gold", 0) >= value

    def check_pet_count(self, player: Entity, count: int) -> bool:
        return len(getattr(player, "pets", [])) >= count

    def check_craft_count(self, player: Entity, category: str, count: int) -> bool:
        return getattr(player, "craft_counts", {}).get(category, 0) >= count

    def check_level(self, player: Entity, level: int) -> bool:
        return player.level >= level

    def check_game_clear_time(self, player: Entity, max_turns: int) -> bool:
        return getattr(player, "total_turns", 0) <= max_turns

    # === 汎用判定ディスパッチャ ===
    def check_condition(self, player: Entity, condition: TitleCondition) -> bool:
        check_map = {
            "kill_count": lambda c: self.check_kill_count(player, c.target, c.count),
            "skill_level": lambda c: self.check_skill_level(player, c.target, c.level),
            "dungeon_depth": lambda c: self.check_dungeon_depth(player, c.min_depth),
            "near_death_count": lambda c: self.check_near_death(player, c.count),
            "piety": lambda c: self.check_piety(player, c.value),
            "gold_owned": lambda c: self.check_gold(player, c.value),
            "pet_count": lambda c: self.check_pet_count(player, c.count),
            "craft_count": lambda c: self.check_craft_count(player, c.category, c.count),
            "level": lambda c: self.check_level(player, c.value),
            "game_clear_time": lambda c: self.check_game_clear_time(player, c.max_turns),
        }
        checker = check_map.get(condition.type)
        if checker:
            return checker(condition)
        return False

    # === 称号付与 ===
    def grant_title(self, player: Entity, title_id: str) -> bool:
        """称号を付与（重複チェック込み）"""
        if title_id in player.titles:
            return False  # 既に所持
        title = self.registry.get(title_id)
        if not title:
            return False
        player.titles.append(title_id)
        # 通知キューに追加
        player.title_notifications.append(title.message)
        # 効果即時適用
        self.apply_title_effects(player, title)
        return True

    def apply_title_effects(self, player: Entity, title: TitleData) -> None:
        """称号効果をステータスに適用"""
        for eff in title.effects:
            if eff.attr == "all_attributes":
                for attr in [
                    "strength",
                    "endurance",
                    "dexterity",
                    "perception",
                    "learning",
                    "will",
                    "magic",
                    "charisma",
                ]:
                    current = getattr(player.attributes, attr)
                    setattr(player.attributes, attr, current + int(eff.value))
            elif hasattr(player.attributes, eff.attr):
                current = getattr(player.attributes, eff.attr)
                if eff.is_multiplier:
                    # 乗算は再計算時に適用するためフラグ管理推奨
                    # ここでは簡易加算
                    setattr(player.attributes, eff.attr, current + int(eff.value))
                else:
                    setattr(player.attributes, eff.attr, current + int(eff.value))
            # 特殊効果 (damage_vs_goblin, fear_resist 等) は別途管理
        player.recalculate_stats()

    def remove_title_effects(self, player: Entity, title: TitleData) -> None:
        """称号効果を除去（装備解除時）"""
        for eff in title.effects:
            if eff.attr == "all_attributes":
                for attr in [
                    "strength",
                    "endurance",
                    "dexterity",
                    "perception",
                    "learning",
                    "will",
                    "magic",
                    "charisma",
                ]:
                    current = getattr(player.attributes, attr)
                    setattr(player.attributes, attr, current - int(eff.value))
            elif hasattr(player.attributes, eff.attr):
                current = getattr(player.attributes, eff.attr)
                setattr(player.attributes, eff.attr, current - int(eff.value))
        player.recalculate_stats()

    # === 全称号チェック（ターン終了時等に呼ぶ） ===
    def check_all_titles(self, player: Entity) -> list[str]:
        """未獲得称号を全チェック、新規獲得分を返す"""
        granted = []
        for title in self.registry.all():
            if title.id in player.titles:
                continue
            if self.check_condition(player, title.condition):
                if self.grant_title(player, title.id):
                    granted.append(title.id)
        return granted

    # === 装備/解除 ===
    def equip_title(self, player: Entity, title_id: str) -> bool:
        """称号を装備（二つ名表示・効果発動）"""
        if title_id not in player.titles:
            return False
        # 既存装備を解除
        if player.equipped_title:
            self.unequip_title(player)
        # 新規装備
        player.equipped_title = title_id
        title = self.registry.get(title_id)
        if title:
            self.apply_title_effects(player, title)
        return True

    def unequip_title(self, player: Entity) -> bool:
        """称号を解除（効果消失）"""
        if not player.equipped_title:
            return False
        title = self.registry.get(player.equipped_title)
        if title:
            self.remove_title_effects(player, title)
        player.equipped_title = ""
        return True

    def get_display_name(self, player: Entity) -> str:
        """表示用名前（二つ名込み）取得"""
        base = player.name
        if player.equipped_title:
            title = self.registry.get(player.equipped_title)
            if title:
                return f"{base}《{title.epithet}》"
        return base

    def get_title_list_for_ui(self, player: Entity) -> list[dict[str, Any]]:
        """UI表示用リスト（獲得済み/未獲得・装備中フラグ付き）"""
        result = []
        for title in self.registry.all():
            owned = title.id in player.titles
            equipped = title.id == player.equipped_title
            result.append(
                {
                    "id": title.id,
                    "name": title.name,
                    "epithet": title.epithet,
                    "category": title.category,
                    "owned": owned,
                    "equipped": equipped,
                    "hidden": title.is_hidden and not owned,
                    "message": title.message if owned else "???",
                }
            )
        return result


# グローバルマネージャー
MANAGER = TitleManager()
