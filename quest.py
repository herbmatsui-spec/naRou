"""Quest data class."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Quest:
    title: str
    target_monster: str
    target_count: int
    current_count: int = 0
    reward_gold: int = 200
    reward_platinum: int = 2
    completed: bool = False


# ============================================================
# クエスト報酬テーブル (T35 R3案A: 報酬定義の一元化)
# ============================================================

# data/main_quests.yaml rewards: の正キー一覧 (この表以外の報酬キーは認めない)。
# world_phase は報酬ではなく進行制御のため、演出対象外として resolver 外で処理する。
QUEST_REWARD_KEYS: tuple[str, ...] = (
    "gold",  # ゴールド
    "exp",  # 経験値
    "items",  # アイテム {item_id: 個数}
    "skill_points",  # スキルポイント
    "world_phase",  # 進行制御 (resolver 外で処理)
)

# 報酬種別 (解決済み報酬の kind に使う)。items は要素単位で "item" に正規化される。
REWARD_KIND_GOLD = "gold"
REWARD_KIND_EXP = "exp"
REWARD_KIND_ITEM = "item"
REWARD_KIND_SKILL_POINTS = "skill_points"

# FloatingText / ログ共通の表示色 (R, G, B)
REWARD_COLORS: dict[str, tuple[int, int, int]] = {
    REWARD_KIND_GOLD: (255, 215, 0),
    REWARD_KIND_EXP: (100, 255, 100),
    REWARD_KIND_ITEM: (170, 150, 255),
    REWARD_KIND_SKILL_POINTS: (80, 200, 255),
}


@dataclass(frozen=True)
class ResolvedReward:
    """解決済み報酬1件分 (付与量と表示ラベルを保持)"""

    kind: str  # REWARD_KIND_* のいずれか
    amount: int  # 付与量 (item は個数)
    item_name: str = ""  # kind が "item" の場合のみ使うアイテムID

    @property
    def label(self) -> str:
        """FloatingText / ログ共通の表示文字列 (例: "+500 G", "EXP+300")"""
        if self.kind == REWARD_KIND_GOLD:
            return f"+{self.amount} G"
        if self.kind == REWARD_KIND_EXP:
            return f"EXP+{self.amount}"
        if self.kind == REWARD_KIND_SKILL_POINTS:
            return f"SP+{self.amount}"
        return f"{self.item_name} ×{self.amount}"


class QuestRewardResolver:
    """クエスト報酬テーブルの解決・付与を一箇所に集約する薄いリゾルバ (T35 R3案A)

    報酬の定義源は data/main_quests.yaml の rewards: キーのみとし、
    gold/exp/items/skill_points の正規化と付与先 (engine.survival / player /
    インベントリ) への反映をここで行う。演出 (FloatingText/ログ) は
    呼び出し側が grant の戻り値を渡して一箇所で発行する。
    """

    def resolve(self, rewards: dict[str, Any] | None) -> list[ResolvedReward]:
        """rewards テーブル辞書を報酬リストへ正規化する

        未知キー (world_phase など進行制御) と非正値は報酬として無視する。
        """
        resolved: list[ResolvedReward] = []
        if not rewards:
            return resolved

        gold = rewards.get(REWARD_KIND_GOLD)
        if self._is_positive_number(gold):
            resolved.append(ResolvedReward(REWARD_KIND_GOLD, int(gold)))

        exp = rewards.get(REWARD_KIND_EXP)
        if self._is_positive_number(exp):
            resolved.append(ResolvedReward(REWARD_KIND_EXP, int(exp)))

        skill_points = rewards.get(REWARD_KIND_SKILL_POINTS)
        if self._is_positive_number(skill_points):
            resolved.append(ResolvedReward(REWARD_KIND_SKILL_POINTS, int(skill_points)))

        items = rewards.get("items")
        if isinstance(items, dict):
            for item_id, count in items.items():
                if self._is_positive_number(count):
                    resolved.append(ResolvedReward(REWARD_KIND_ITEM, int(count), str(item_id)))

        return resolved

    def grant(
        self, player: Any, engine: Any, rewards: dict[str, Any] | None
    ) -> list[ResolvedReward]:
        """報酬を付与し、実際に付与できた報酬のリストを返す

        付与先 (survival / player 属性 / インベントリ) が存在しない報酬は
        黙ってスキップし、戻り値に含めない (演出側は戻り値のみを表示する)。
        """
        granted: list[ResolvedReward] = []
        for reward in self.resolve(rewards):
            if self._grant_one(player, engine, reward):
                granted.append(reward)
        return granted

    def _grant_one(self, player: Any, engine: Any, reward: ResolvedReward) -> bool:
        """単一報酬を付与する (付与先が無い場合は False)"""
        if reward.kind == REWARD_KIND_GOLD:
            # engine.survival が正本 (kernel 登録オブジェクト)。
            # engine.survival_system とは別オブジェクトのため直接は使わない。
            survival = getattr(engine, "survival", None) if engine is not None else None
            if survival is not None:
                survival.gold = getattr(survival, "gold", 0) + reward.amount
                return True
            if player is not None and hasattr(player, "gold"):
                player.gold = getattr(player, "gold", 0) + reward.amount
                return True
            return False

        if player is None:
            return False

        if reward.kind == REWARD_KIND_EXP:
            gain_exp = getattr(player, "gain_exp", None)
            if callable(gain_exp):
                gain_exp(reward.amount)
                return True
            if hasattr(player, "exp"):
                player.exp = getattr(player, "exp", 0) + reward.amount
                return True
            return False

        if reward.kind == REWARD_KIND_SKILL_POINTS:
            if not hasattr(player, "skill_points"):
                return False
            player.skill_points = getattr(player, "skill_points", 0) + reward.amount
            if hasattr(player, "total_skill_points_earned"):
                player.total_skill_points_earned = (
                    getattr(player, "total_skill_points_earned", 0) + reward.amount
                )
            return True

        if reward.kind == REWARD_KIND_ITEM:
            inventory = self._find_inventory(player, engine)
            if inventory is None:
                return False
            return self._add_item(inventory, reward.item_name, reward.amount)

        return False

    def _find_inventory(self, player: Any, engine: Any) -> Any:
        """報酬アイテムの受け先インベントリを探す (player コンポーネント → engine)"""
        components = getattr(player, "components", None)
        if components is not None:
            from item_system import Inventory

            inventory = components.get(Inventory)
            if inventory is not None:
                return inventory
        return getattr(engine, "inventory", None) if engine is not None else None

    def _add_item(self, inventory: Any, item_id: str, count: int) -> bool:
        """インベントリへ count 個のアイテムを追加する (1個でも追加できたら True)"""
        from item_system import create_sample_item

        added = 0
        for _ in range(count):
            item = create_sample_item(item_id)
            if item is None:
                break
            ok, _message = inventory.add_item(item)
            if not ok:
                break
            added += 1
        return added > 0

    @staticmethod
    def _is_positive_number(value: Any) -> bool:
        """正の数かどうか (bool は数とみなさない)"""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return value > 0
