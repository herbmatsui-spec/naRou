"""
Event Scheduler Module
Handles scheduling of seasonal events based on game time and quarter.
"""

from __future__ import annotations

# ワールドイベントシステムからレジストリをインポートしないことで循環インポートを避ける
# レジストリオブジェクトは外部から渡されるものとする
from typing import Any


class EventScheduler:
    def __init__(self, registry=None):
        self.registry = registry

    def get_current_seasonal_event(
        self, current_turn: int, current_quarter: int | None = None
    ) -> Any | None:
        """
        現在のターンと四半期に基づいてアクティブなシーズンイベントを取得する。
        :param current_turn: 現在のターン数
        :param current_quarter: 現在の四半期 (1-4)。Noneの場合はターンから計算。
        :return: アクティブなワールドイベントデータまたはNone
        """
        if self.registry is None:
            return None
        if current_quarter is None:
            # 仮定: 1年を4つの季節に分け、それぞれ90ターン（調整必要）
            current_quarter = ((current_turn // 90) % 4) + 1

        # 指定された四半期のイベントを探す
        for event_data in self.registry.all_events().values():
            # スケジュールターンが設定されている場合はそれを優先（クォーターより優先）
            if (
                hasattr(event_data, "start_turn")
                and hasattr(event_data, "end_turn")
                and event_data.start_turn is not None
                and event_data.end_turn is not None
            ):
                if event_data.start_turn <= current_turn <= event_data.end_turn:
                    return event_data
            # スケジュールターンが設定されていないが、quarterが一致する場合は四半期中ずっとアクティブとみなす
            elif (
                hasattr(event_data, "quarter")
                and event_data.quarter is not None
                and event_data.quarter == current_quarter
            ):
                return event_data
        return None

    def get_announcement_event(
        self, current_turn: int, current_quarter: int | None = None
    ) -> Any | None:
        """
        アナウンス期間中のイベントを取得する。
        :param current_turn: 現在のターン数
        :param current_quarter: 現在の四半期 (1-4)。Noneの場合はターンから計算。
        :return: アナウンス中のイベントまたはNone
        """
        if self.registry is None:
            return None
        if current_quarter is None:
            current_quarter = ((current_turn // 90) % 4) + 1

        for event_data in self.registry.all_events().values():
            in_quarter = False
            if hasattr(event_data, "quarter") and event_data.quarter is not None:
                if event_data.quarter == current_quarter:
                    in_quarter = True
            if (
                hasattr(event_data, "start_turn")
                and hasattr(event_data, "end_turn")
                and event_data.start_turn is not None
                and event_data.end_turn is not None
            ):
                in_quarter = True
                event_start = event_data.start_turn
                event_end = event_data.end_turn
            else:
                if not in_quarter:
                    continue
                quarter_start = (current_quarter - 1) * 90
                quarter_end = quarter_start + 90
                event_start = quarter_start
                event_end = quarter_end

            announcement_period = getattr(event_data, "announcement_period", 0)
            if announcement_period > 0:
                announcement_start = event_start - announcement_period
                announcement_end = event_start
                if announcement_start <= current_turn < announcement_end:
                    return event_data
        return None

    async def async_get_current_seasonal_event(
        self, current_turn: int, current_quarter: int | None = None
    ) -> Any | None:
        """Async wrapper for get_current_seasonal_event."""
        return self.get_current_seasonal_event(current_turn, current_quarter)

    async def async_get_announcement_event(
        self, current_turn: int, current_quarter: int | None = None
    ) -> Any | None:
        """Async wrapper for get_announcement_event."""
        return self.get_announcement_event(current_turn, current_quarter)
        """
        アナウンス期間中のイベントを取得する。
        :param current_turn: 現在のターン数
        :param current_quarter: 現在の四半期 (1-4)。Noneの場合はターンから計算。
        :return: アナウンス中のイベントまたはNone
        """
        if self.registry is None:
            return None
        if current_quarter is None:
            # 仮定: 1年を4つの季節に分け、それぞれ90ターン（調整必要）
            current_quarter = ((current_turn // 90) % 4) + 1

        # 指定された四半期のイベントを探す
        for event_data in self.registry.all_events().values():
            # イベントがこのクォーターに属するか、またはスケジュールされているかを判定
            in_quarter = False
            if hasattr(event_data, "quarter") and event_data.quarter is not None:
                if event_data.quarter == current_quarter:
                    in_quarter = True
            # スケジュールターンが設定されている場合はそれを優先
            if (
                hasattr(event_data, "start_turn")
                and hasattr(event_data, "end_turn")
                and event_data.start_turn is not None
                and event_data.end_turn is not None
            ):
                # スケジュールされているイベント
                in_quarter = (
                    True  # スケジュールされている場合はクォーターに関係なく考慮
                )
                event_start = event_data.start_turn
                event_end = event_data.end_turn
            else:
                # スケジュールターンが設定されていないが、quarterが一致する場合は四半期中ずっとアクティブとみなす
                if not in_quarter:
                    continue
                # 四半期の概算開始ターンと終了ターンを計算
                quarter_start = (current_quarter - 1) * 90
                quarter_end = quarter_start + 90
                event_start = quarter_start
                event_end = quarter_end

            # アナウンス期間を計算: イベント開始ターン - announcement_period
            announcement_period = getattr(event_data, "announcement_period", 0)
            if announcement_period > 0:
                announcement_start = event_start - announcement_period
                announcement_end = event_start  # アナウンス期間はイベント開始まで
                if announcement_start <= current_turn < announcement_end:
                    return event_data
        return None
