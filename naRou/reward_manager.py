"""
Reward Manager Module
Handles granting of rewards for world events.
"""

from __future__ import annotations

import random
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from naRou.systems.item_system import Item, Inventory
    from naRou.systems.item_system import create_sample_item

from naRou.ecs.entity import Entity  # Assuming Entity is defined elsewhere

# Reward key constants
KEY_GOLD = "gold"
KEY_PLATINUM = "platinum"
KEY_EXP = "exp"
KEY_PIETY = "piety"
KEY_FAME = "fame"
KEY_ITEMS = "items"
KEY_ITEM_DROPS = "item_drops"
KEY_ARTIFACT = "artifact"
KEY_SPECIAL_CURRENCY = "special_currency"
KEY_CURRENCY_AMOUNT = "currency_amount"


_CURRENCY_MAP = {
    "gold": KEY_GOLD,
    "g": KEY_GOLD,
    "platinum": KEY_PLATINUM,
    "p": KEY_PLATINUM,
}


class RewardManager:
    """Reward manager that grants rewards to players based on event data.
    
    Supported reward dict keys:
    - "gold": int amount of gold
    - "platinum": int amount of platinum
    - "exp": int experience points
    - "piety": int piety points
    - "fame": int fame points (stored in faction_reputation)
    - "items": dict{item_id: quantity} for guaranteed item drops
    - "item_drops": dict{item_id: drop_chance} for probabilistic drops
    - "artifact": str item_id for a single artifact item
    - "special_currency": str currency_id (legacy)
    - "currency_amount": int amount for legacy special_currency
    Unknown keys are ignored (logged if engine provided).
    """
    def __init__(self):
        pass

    def _normalize_rewards(self, rewards) -> dict[str, Any]:
        if not isinstance(rewards, dict):
            return {}
        return rewards

    def _get_amount(self, rewards, key, default=0) -> int:
        try:
            return int(rewards.get(key, default))
        except (ValueError, TypeError):
            return default

    def _resolve_item_id(self, raw_id) -> str:
        return str(raw_id)

    def _log(self, engine: Any, message: str, color: tuple[int, int, int] = (255, 255, 255)) -> None:
        """Log a message via engine if available."""
        if engine is not None and hasattr(engine, "log"):
            engine.log(message, color)

    def _grant_gold(self, player: Entity, amount: int, engine: Any = None) -> None:
        """Grant gold to player."""
        if amount <= 0:
            return
        player.gold = getattr(player, "gold", 0) + amount
        self._log(engine, f"金が{amount}G増加した。", (255, 215, 0))

    def _grant_platinum(self, player: Entity, amount: int, engine: Any = None) -> None:
        """Grant platinum to player."""
        if amount <= 0:
            return
        player.platinum = getattr(player, "platinum", 0) + amount
        self._log(engine, f"プラチナが{amount}P増加した。", (229, 228, 226))

    def _grant_exp(self, player: Entity, amount: int, engine: Any = None) -> list[str]:
        """Grant experience points to player, returning log strings."""
        if amount <= 0:
            return []
        logs = player.gain_exp(amount)
        if engine is not None:
            for log in logs:
                self._log(engine, log, (255, 255, 100))
        return logs

    def _grant_piety(self, player: Entity, amount: int, engine: Any = None) -> None:
        """Grant piety points to player."""
        if amount <= 0:
            return
        player.piety = getattr(player, "piety", 0) + amount
        self._log(engine, f"信仰が{amount}増加した。", (255, 180, 100))

    def _grant_fame(self, player: Entity, amount: int, engine: Any = None) -> None:
        """Grant fame points to player (stored in faction_reputation)."""
        if amount <= 0:
            return
        # Ensure faction_reputation exists as a dict
        rep = getattr(player, "faction_reputation", None)
        if rep is None:
            rep = {}
            player.faction_reputation = rep
        rep["world"] = rep.get("world", 0) + amount
        self._log(engine, f"名声が{amount}増加した。", (200, 200, 200))

    def _grant_currency(self, player: Entity, currency_id: str, amount: int, engine: Any = None) -> None:
        """Grant currency based on currency_id."""
        mapped = self._CURRENCY_MAP.get(str(currency_id).lower(), KEY_GOLD)
        if mapped == KEY_GOLD:
            self._grant_gold(player, amount, engine)
        elif mapped == KEY_PLATINUM:
            self._grant_platinum(player, amount, engine)
        else:
            # Fallback to gold (should not happen)
            self._grant_gold(player, amount, engine)

    def _create_item(self, item_id: str, quantity: int = 1) -> Item:
        """Create an Item from item_id, using create_sample_item with fallback."""
        try:
            from naRou.systems.item_system import create_sample_item, Item, CAT_TOOL
            item = create_sample_item(item_id)
            if not isinstance(item, Item):
                raise ValueError("create_sample_item did not return an Item")
            item.count = int(quantity)
            return item
        except Exception:
            # Fallback: create a minimal item
            from naRou.systems.item_system import Item, CAT_TOOL
            item = Item(
                name=f"不明なアイテム ({item_id})",
                category=CAT_TOOL,
                char="?",
                color=(200, 200, 200),
                base_weight=0.1,
                base_value=10,
                count=int(quantity),
            )
            return item

    def _grant_item(self, player: Entity, item_id: str, quantity: int = 1, engine: Any = None) -> None:
        """Grant a specific item to player's inventory."""
        if quantity <= 0:
            return
        inv = getattr(player, "inventory", None)
        if inv is None:
            self._log(engine, "インベントリがないためアイテムを付与できません。", (255, 100, 100))
            return
        try:
            item = self._create_item(item_id, quantity)
            ok, msg = inv.add_item(item)
            self._log(engine, msg, (120, 255, 120) if ok else (255, 100, 100))
        except Exception as e:
            self._log(engine, f"アイテム付与中にエラー: {e}", (255, 100, 100))

    def _grant_items(self, player: Entity, items_dict: dict[str, Any], engine: Any = None) -> None:
        """Grant multiple items from a dict of item_id to quantity."""
        if not isinstance(items_dict, dict):
            return
        for item_id, qty in items_dict.items():
            self._grant_item(player, item_id, qty, engine)

    def grant_event_rewards(self, player: Entity, event_data: Any, engine: Any = None) -> list[str]:
        """
        イベントに関連する報酬をプレイヤーに付与する。
        :param player: 報酬を受け取るプレイヤー
        :param event_data: WorldEventDataオブジェクト
        :param engine: ログ出力用エンジン（任意）
        :return: 付与されたログメッセージのリスト
        """
        rewards = self._normalize_rewards(getattr(event_data, "rewards", {}))
        logs: list[str] = []

        # 金
        if KEY_GOLD in rewards:
            amount = self._get_amount(rewards, KEY_GOLD)
            if amount != 0:
                logs.extend(self._grant_gold(player, amount, engine))

        # プラチナ
        if KEY_PLATINUM in rewards:
            amount = self._get_amount(rewards, KEY_PLATINUM)
            if amount != 0:
                logs.extend(self._grant_platinum(player, amount, engine))

        # 経験値
        if KEY_EXP in rewards:
            amount = self._get_amount(rewards, KEY_EXP)
            if amount != 0:
                logs.extend(self._grant_exp(player, amount, engine))

        # 信仰
        if KEY_PIETY in rewards:
            amount = self._get_amount(rewards, KEY_PIETY)
            if amount != 0:
                logs.extend(self._grant_piety(player, amount, engine))

        # 名声
        if KEY_FAME in rewards:
            amount = self._get_amount(rewards, KEY_FAME)
            if amount != 0:
                logs.extend(self._grant_fame(player, amount, engine))

        # アイテム（確定ドロップ）
        if KEY_ITEMS in rewards:
            items_dict = rewards[KEY_ITEMS]
            if isinstance(items_dict, dict):
                logs.extend(self._grant_items(player, items_dict, engine))

        # アイテムドロップ（確率ドロップ）
        if KEY_ITEM_DROPS in rewards:
            drops_dict = rewards[KEY_ITEM_DROPS]
            if isinstance(drops_dict, dict):
                for item_id, drop_chance in drops_dict.items():
                    try:
                        chance = float(drop_chance)
                    except (ValueError, TypeError):
                        continue
                    if chance > 0 and random.random() < chance:
                        logs.extend(self._grant_item(player, item_id, 1, engine))

        # アーティファクト（特別アイテム）
        if KEY_ARTIFACT in rewards:
            artifact_id = rewards[KEY_ARTIFACT]
            if artifact_id:
                logs.extend(self._grant_item(player, artifact_id, 1, engine))

        # レガシー特別通貨
        if KEY_SPECIAL_CURRENCY in rewards:
            currency_id = rewards[KEY_SPECIAL_CURRENCY]
            amount = self._get_amount(rewards, KEY_CURRENCY_AMOUNT, 100)
            if amount != 0:
                logs.extend(self._grant_currency(player, currency_id, amount, engine))

        # エンジンがあればログ出力
        if engine is not None:
            for log in logs:
                self._log(engine, log, (255, 255, 255))

        return logs


REWARD_MANAGER = RewardManager()