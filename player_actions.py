"""
Player Action Time Cost System
Steps 41-48: ActionType, ActionCost, PlayerActionManager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

try:
    from naRou.time_system import TimePhase, get_world_clock
except ImportError:
    from time_system import TimePhase, get_world_clock


class ActionType(Enum):
    """プレイヤー行動タイプ"""
    EXPLORE = "explore"       # 探索 (2h)
    CRAFT = "craft"           # クラフト (3h)
    SLEEP = "sleep"           # 睡眠 (6h, 全回復)
    WAIT = "wait"             # 待機 (1h)
    TRAVEL = "travel"         # 移動 (距離依存)
    TRAIN = "train"           # 訓練 (2h)
    SHOP = "shop"             # 買い物 (1h)
    TALK = "talk"             # 会話 (0.5h)


@dataclass
class ActionCost:
    """行動コスト定義"""
    action_type: ActionType
    base_hours: float
    stamina_cost: int = 0
    mp_cost: int = 0
    hp_cost: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """行動実行結果"""
    success: bool
    message: str
    hours_consumed: float = 0.0
    stamina_cost: int = 0
    mp_cost: int = 0


class PlayerActionManager:
    """プレイヤー行動管理"""

    def __init__(self):
        self._costs: dict[ActionType, ActionCost] = {}
        self._load_default_costs()

    def _load_default_costs(self) -> None:
        """デフォルトコスト設定"""
        self._costs = {
            ActionType.EXPLORE: ActionCost(ActionType.EXPLORE, 2.0, stamina_cost=10),
            ActionType.CRAFT: ActionCost(ActionType.CRAFT, 3.0, stamina_cost=15, mp_cost=5),
            ActionType.SLEEP: ActionCost(ActionType.SLEEP, 6.0),
            ActionType.WAIT: ActionCost(ActionType.WAIT, 1.0),
            ActionType.TRAVEL: ActionCost(ActionType.TRAVEL, 1.0, stamina_cost=5),  # 基本1h/区画
            ActionType.TRAIN: ActionCost(ActionType.TRAIN, 2.0, stamina_cost=20, mp_cost=10),
            ActionType.SHOP: ActionCost(ActionType.SHOP, 1.0),
            ActionType.TALK: ActionCost(ActionType.TALK, 0.5),
        }

    def load_from_yaml(self, path: str) -> None:
        """YAMLからコスト読み込み"""
        p = Path(path)
        if not p.exists():
            return

        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for cost_data in data.get("action_costs", []):
            try:
                action_type = ActionType(cost_data["action_type"])
            except ValueError:
                continue

            self._costs[action_type] = ActionCost(
                action_type=action_type,
                base_hours=cost_data.get("base_hours", 1.0),
                stamina_cost=cost_data.get("stamina_cost", 0),
                mp_cost=cost_data.get("mp_cost", 0),
                hp_cost=cost_data.get("hp_cost", 0),
                conditions=cost_data.get("conditions", {}),
            )

    def get_cost(self, action_type: ActionType) -> ActionCost | None:
        """コスト取得"""
        return self._costs.get(action_type)

    def can_perform(self, action_type: ActionType, player: Any, **kwargs) -> tuple[bool, str]:
        """実行可能判定"""
        cost = self._costs.get(action_type)
        if not cost:
            return False, f"不明な行動: {action_type.value}"

        # スタミナチェック
        if cost.stamina_cost > 0:
            if player.stamina < cost.stamina_cost:
                return False, f"スタミナ不足 (必要: {cost.stamina_cost}, 現在: {player.stamina})"

        # MPチェック
        if cost.mp_cost > 0:
            if player.mp < cost.mp_cost:
                return False, f"MP不足 (必要: {cost.mp_cost}, 現在: {player.mp})"

        # 施設稼働チェック (クラフト等)
        if action_type == ActionType.CRAFT:
            clock = get_world_clock()
            if not clock.is_facility_active("workshop"):
                return False, "工房が稼働していません (昼間のみ利用可能)"

        # 時間帯制限チェック
        if action_type == ActionType.EXPLORE:
            clock = get_world_clock()
            if clock.current_phase == TimePhase.NIGHT:
                # 夜間探索は警告のみ (実行は可能)
                pass

        # 追加条件チェック
        for key, value in cost.conditions.items():
            if key == "min_level" and player.level < value:
                return False, f"レベル不足 (必要: {value})"

        return True, "実行可能"

    def perform(self, action_type: ActionType, player: Any, **kwargs) -> ActionResult:
        """行動実行"""
        can, msg = self.can_perform(action_type, player, **kwargs)
        if not can:
            return ActionResult(False, msg)

        cost = self._costs[action_type]
        clock = get_world_clock()

        # 実際の消費時間計算 (施設効率適用)
        actual_hours = cost.base_hours
        if action_type == ActionType.CRAFT:
            efficiency = clock.get_facility_efficiency("workshop")
            if efficiency > 0:
                actual_hours = cost.base_hours / efficiency

        # コスト消費
        if cost.stamina_cost > 0:
            player.stamina = max(0, player.stamina - cost.stamina_cost)
        if cost.mp_cost > 0:
            player.mp = max(0, player.mp - cost.mp_cost)

        # 時間経過
        clock.advance(int(actual_hours))

        # 行動別効果
        if action_type == ActionType.EXPLORE:
            return self._perform_explore(player, actual_hours)
        elif action_type == ActionType.CRAFT:
            return self._perform_craft(player, actual_hours, **kwargs)
        elif action_type == ActionType.SLEEP:
            return self._perform_sleep(player, actual_hours)
        elif action_type == ActionType.WAIT:
            return self._perform_wait(player, actual_hours)
        elif action_type == ActionType.TRAVEL:
            return self._perform_travel(player, actual_hours, **kwargs)
        elif action_type == ActionType.TRAIN:
            return self._perform_train(player, actual_hours)
        elif action_type == ActionType.SHOP:
            return self._perform_shop(player, actual_hours)
        elif action_type == ActionType.TALK:
            return self._perform_talk(player, actual_hours)

        return ActionResult(True, f"{action_type.value}を実行した", actual_hours, cost.stamina_cost, cost.mp_cost)

    def _perform_explore(self, player: Any, hours: float) -> ActionResult:
        """探索実行"""
        clock = get_world_clock()
        phase = clock.current_phase

        # 時間帯による効果
        if phase == TimePhase.NIGHT:
            msg = f"夜間探索を実施 ({hours:.1f}h経過)。遭遇率上昇、レアドロップ率上昇。"
        elif phase == TimePhase.DAY:
            msg = f"昼間探索を実施 ({hours:.1f}h経過)。安全、経験値ボーナス。"
        else:
            msg = f"探索を実施 ({hours:.1f}h経過)。"

        return ActionResult(True, msg, hours, 10, 0)

    def _perform_craft(self, player: Any, hours: float, recipe_id: str = "", **kwargs) -> ActionResult:
        """クラフト実行"""
        # 実際のクラフト処理は別システムに委譲
        msg = f"クラフトを実行 ({hours:.1f}h経過)。レシピ: {recipe_id or '不明'}"
        return ActionResult(True, msg, hours, 15, 5)

    def _perform_sleep(self, player: Any, hours: float) -> ActionResult:
        """睡眠実行"""
        # 次の夜明けまで調整
        clock = get_world_clock()
        hours_until_dawn = TimePhase.DAWN.hours_until_next(clock.hour)
        if hours_until_dawn < hours:
            hours = float(hours_until_dawn)

        # 全回復
        player.hp = player.max_hp
        player.mp = player.max_mp
        player.stamina = player.max_stamina

        # SurvivalSystem連携
        try:
            from naRou.systems import SurvivalSystem
            survival = SurvivalSystem()
            survival.sleep(player)
        except ImportError:
            pass

        msg = f"ぐっすり眠った ({hours:.1f}h経過)。HP・MP・スタミナ全快！"
        return ActionResult(True, msg, hours, 0, 0)

    def _perform_wait(self, player: Any, hours: float) -> ActionResult:
        """待機実行"""
        # スタミナ微回復
        recover = min(10, player.max_stamina - player.stamina)
        player.stamina += recover

        msg = f"待機した ({hours:.1f}h経過)。スタミナ+{recover}回復。"
        return ActionResult(True, msg, hours, 0, 0)

    def _perform_travel(self, player: Any, hours: float, distance: int = 1, **kwargs) -> ActionResult:
        """移動実行"""
        actual_hours = hours * distance
        msg = f"移動した ({actual_hours:.1f}h経過)。距離: {distance}"
        return ActionResult(True, msg, actual_hours, 5 * distance, 0)

    def _perform_train(self, player: Any, hours: float) -> ActionResult:
        """訓練実行"""
        # スキル経験値付与は別システムに委譲
        msg = f"訓練した ({hours:.1f}h経過)。スキル経験値獲得。"
        return ActionResult(True, msg, hours, 20, 10)

    def _perform_shop(self, player: Any, hours: float) -> ActionResult:
        """買い物実行"""
        msg = f"買い物をした ({hours:.1f}h経過)。"
        return ActionResult(True, msg, hours, 0, 0)

    def _perform_talk(self, player: Any, hours: float) -> ActionResult:
        """会話実行"""
        msg = f"会話した ({hours:.1f}h経過)。"
        return ActionResult(True, msg, hours, 0, 0)

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return {
            "costs": {
                at.value: {
                    "action_type": at.value,
                    "base_hours": c.base_hours,
                    "stamina_cost": c.stamina_cost,
                    "mp_cost": c.mp_cost,
                    "hp_cost": c.hp_cost,
                    "conditions": c.conditions,
                }
                for at, c in self._costs.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerActionManager":
        manager = cls()
        for at_str, c_data in data.get("costs", {}).items():
            try:
                action_type = ActionType(at_str)
            except ValueError:
                continue
            manager._costs[action_type] = ActionCost(
                action_type=action_type,
                base_hours=c_data.get("base_hours", 1.0),
                stamina_cost=c_data.get("stamina_cost", 0),
                mp_cost=c_data.get("mp_cost", 0),
                hp_cost=c_data.get("hp_cost", 0),
                conditions=c_data.get("conditions", {}),
            )
        return manager
