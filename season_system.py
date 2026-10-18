"""季節システム (T44 案B: 季節イベントシステム完成度)

春夏秋冬の季節サイクル進行と季節ごとの実効効果 (敵攻撃 / ハングリー消費 /
回復 / ドロップゴールド / 店価格) を管理する。

既存定義との整合:

- ターン → 季節: event_scheduler.EventScheduler と同一の規則
  (1季節 = 90ターン, quarter = ((turn // 90) % 4) + 1)。
- quarter 1-4 は world_event_system.WorldEventData.quarter の既存定義
  (1:春, 2:夏, 3:秋, 4:冬) に対応する。
- season_id (spring|summer|autumn|winter) は
  quest_scheduler.ScheduleCondition.season の想定値に対応する。
- 月 (1-12) → 季節は time_system.WorldClock の暦 (30日/月, 12ヶ月) に対応。

季節転換時には SeasonSystem.update() がイベント (ログ + FloatingText +
EventBus 通知) を発火し、shop_system へは店価格倍率が後段乗算で反映される。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# 1季節あたりのターン数 (event_scheduler.py の既存計算式と同一の値)
TURNS_PER_SEASON = 90

# 季節転換ログ / FloatingText の色 (若葉色)
SEASON_COLOR: tuple[int, int, int] = (144, 238, 144)


class Season(Enum):
    """季節 (quarter は WorldEventData.quarter の既存定義: 1:春, 2:夏, 3:秋, 4:冬)"""

    SPRING = (1, "spring", "春")
    SUMMER = (2, "summer", "夏")
    AUTUMN = (3, "autumn", "秋")
    WINTER = (4, "winter", "冬")

    def __init__(self, quarter: int, season_id: str, display_name: str) -> None:
        self.quarter = quarter
        self.season_id = season_id
        self.display_name = display_name

    @classmethod
    def from_quarter(cls, quarter: int) -> "Season":
        """四半期番号 (1-4) から季節を判定する (範囲外は mod 4 で正規化)"""
        normalized = ((int(quarter) - 1) % 4) + 1
        for season in cls:
            if season.quarter == normalized:
                return season
        raise ValueError(f"不正な quarter: {quarter}")  # 到達しない

    @classmethod
    def from_turn(cls, turn: int) -> "Season":
        """ターン数から季節を判定する (EventScheduler と同一の既存規則)"""
        turn = max(0, int(turn))
        return cls.from_quarter(((turn // TURNS_PER_SEASON) % 4) + 1)

    @classmethod
    def from_month(cls, month: int) -> "Season":
        """月 (1-12) から季節を判定する (WorldClock の暦に対応)

        3-5月: 春 / 6-8月: 夏 / 9-11月: 秋 / 12,1,2月: 冬
        """
        m = int(month) % 12
        if m == 0:
            m = 12
        if 3 <= m <= 5:
            return cls.SPRING
        if 6 <= m <= 8:
            return cls.SUMMER
        if 9 <= m <= 11:
            return cls.AUTUMN
        return cls.WINTER

    def next(self) -> "Season":
        """翌季節を返す (冬の翌は春)"""
        return self.from_quarter(self.quarter + 1)


@dataclass(frozen=True)
class SeasonEffects:
    """季節ごとの実効効果倍率 (1.0 = 影響なし)"""

    enemy_attack_multiplier: float = 1.0  # 敵攻撃倍率
    hunger_consumption_multiplier: float = 1.0  # ハングリー消費倍率
    heal_multiplier: float = 1.0  # 回復量倍率
    gold_drop_multiplier: float = 1.0  # ドロップゴールド倍率
    shop_price_multiplier: float = 1.0  # 店価格倍率 (小さいほど割引)


# 季節別効果テーブル
# 春: 生命の息吹 (回復+10%) / 夏: 酷暑 (敵攻撃+10%)
# 秋: 収穫祭 (ドロップ金+20%, 店価格10%引) / 冬: 厳寒 (ハングリー消費+20%)
SEASON_EFFECTS: dict[Season, SeasonEffects] = {
    Season.SPRING: SeasonEffects(heal_multiplier=1.10),
    Season.SUMMER: SeasonEffects(enemy_attack_multiplier=1.10),
    Season.AUTUMN: SeasonEffects(gold_drop_multiplier=1.20, shop_price_multiplier=0.90),
    Season.WINTER: SeasonEffects(hunger_consumption_multiplier=1.20),
}


@dataclass
class SeasonTransition:
    """季節転換情報 (SeasonSystem.update の戻り値)"""

    old_season: Season
    new_season: Season
    turn: int
    message: str


class SeasonSystem:
    """季節サイクルの進行管理と季節転換イベント発火

    ターン進行に合わせて update() を呼び出すと季節を追跡し、季節が
    転換した瞬間にログ / FloatingText / EventBus 通知を発火する。
    """

    def __init__(self, start_turn: int = 0, event_bus: Any | None = None) -> None:
        self._current_season = Season.from_turn(start_turn)
        self.event_bus = event_bus

    @property
    def current_season(self) -> Season:
        """追跡中の現在季節"""
        return self._current_season

    def get_season(self, turn: int | None = None) -> Season:
        """現在 (または指定ターン) の季節を取得する"""
        if turn is None:
            return self._current_season
        return Season.from_turn(turn)

    def update(
        self,
        turn: int,
        engine: Any | None = None,
        player: Any | None = None,
    ) -> SeasonTransition | None:
        """ターン進行に追従して季節を更新し、転換時にイベントを発火する。

        Args:
            turn: 現在のターン数
            engine: log() / fx_manager.add_floating_text() を持つオブジェクト (省略可)
            player: FloatingText の表示座標の参照先 (x / y 属性, 省略可)

        Returns:
            季節が転換した場合は SeasonTransition、同一季節内なら None。
        """
        new_season = Season.from_turn(turn)
        if new_season == self._current_season:
            return None
        transition = self._fire_season_changed(
            self._current_season, new_season, int(turn), engine, player
        )
        self._current_season = new_season
        return transition

    def _fire_season_changed(
        self,
        old_season: Season,
        new_season: Season,
        turn: int,
        engine: Any | None,
        player: Any | None,
    ) -> SeasonTransition:
        """季節転換イベントを発火する (ログ + FloatingText + EventBus)"""
        message = f"季節は{new_season.display_name}へ"
        if engine is not None:
            log = getattr(engine, "log", None)
            if callable(log):
                log(f"【季節】{message}", SEASON_COLOR, level="INFO")
            fx = getattr(engine, "fx_manager", None)
            if fx is not None and hasattr(fx, "add_floating_text"):
                x = float(getattr(player, "x", 0) or 0)
                y = float(getattr(player, "y", 0) or 0)
                fx.add_floating_text(message, x, y, SEASON_COLOR)
        if self.event_bus is not None:
            self.event_bus.publish(
                "SEASON_CHANGED",
                {"old": old_season, "new": new_season, "turn": turn},
            )
        logger.info("季節が転換: %s → %s (ターン %s)", old_season.display_name, new_season.display_name, turn)
        return SeasonTransition(
            old_season=old_season,
            new_season=new_season,
            turn=turn,
            message=message,
        )

    # --- 季節効果アクセサ ---

    def get_effects(self, season: Season | None = None) -> SeasonEffects:
        """指定季節 (未指定なら現在季節) の効果倍率を取得する"""
        key = season if season is not None else self._current_season
        return SEASON_EFFECTS[key]

    def get_enemy_attack_multiplier(self, season: Season | None = None) -> float:
        """敵攻撃倍率を取得する"""
        return self.get_effects(season).enemy_attack_multiplier

    def get_hunger_consumption_multiplier(self, season: Season | None = None) -> float:
        """ハングリー消費倍率を取得する"""
        return self.get_effects(season).hunger_consumption_multiplier

    def get_heal_multiplier(self, season: Season | None = None) -> float:
        """回復量倍率を取得する"""
        return self.get_effects(season).heal_multiplier

    def get_gold_drop_multiplier(self, season: Season | None = None) -> float:
        """ドロップゴールド倍率を取得する"""
        return self.get_effects(season).gold_drop_multiplier

    def get_shop_price_multiplier(self, season: Season | None = None) -> float:
        """店価格倍率を取得する (shop_system の後段乗算で使用)"""
        return self.get_effects(season).shop_price_multiplier

    # --- セーブ/ロード ---

    def to_dict(self) -> dict:
        return {"current_quarter": self._current_season.quarter}

    def from_dict(self, data: dict) -> None:
        quarter = int((data or {}).get("current_quarter", 1))
        self._current_season = Season.from_quarter(quarter)


# モジュールシングルトン (shop_system 等から現在季節を参照する)
SEASON_SYSTEM = SeasonSystem()
