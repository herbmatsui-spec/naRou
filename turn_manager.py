"""
Elona Roguelike Masterpiece - Time, Energy Tick, & Speed System
Steps 10 to 18 (Resolving speed & action timing contradictions)
"""

from __future__ import annotations

from typing import Any

from constants import ENERGY_THRESHOLD
from core_framework import EventBus
from time_system import TimeConfig, TimePhase, WorldClock


class TimeSystem:
    """Tickベースの絶対時間とElona風エネルギーチャージシステム (ステップ9, 10, 11, 12, 17)
    内部的にWorldClockを使用し、後方互換性を維持
    """

    def __init__(
        self,
        year: int = 517,
        month: int = 8,
        day: int = 15,
        hour: int = 8,
        minute: int = 0,
        event_bus: EventBus | None = None,
    ):
        # WorldClockに委譲
        config = TimeConfig(
            start_year=year,
            start_month=month,
            start_day=day,
            start_hour=hour,
            start_minute=minute,
        )
        self._world_clock = WorldClock(config, event_bus)
        self.event_bus = event_bus

    # --- 後方互換プロパティ ---
    @property
    def year(self) -> int:
        return self._world_clock.year

    @year.setter
    def year(self, value: int) -> None:
        self._world_clock.year = value

    @property
    def month(self) -> int:
        return self._world_clock.month

    @month.setter
    def month(self, value: int) -> None:
        self._world_clock.month = value

    @property
    def day(self) -> int:
        return self._world_clock.day

    @day.setter
    def day(self, value: int) -> None:
        self._world_clock.day = value

    @property
    def hour(self) -> int:
        return self._world_clock.hour

    @hour.setter
    def hour(self, value: int) -> None:
        self._world_clock.hour = value % 24

    @property
    def minute(self) -> int:
        return self._world_clock.minute

    @minute.setter
    def minute(self, value: int) -> None:
        self._world_clock.minute = value % 60

    @property
    def ticks(self) -> int:
        return self._world_clock.total_ticks

    @ticks.setter
    def ticks(self, value: int) -> None:
        self._world_clock.total_ticks = value

    @property
    def world_clock(self) -> WorldClock:
        """WorldClockインスタンスへのアクセス"""
        return self._world_clock

    @property
    def current_phase(self) -> TimePhase:
        return self._world_clock.current_phase

    # --- メソッド ---
    def pass_ticks(self, ticks: int = 10) -> None:
        """絶対Tickの経過と日付計算 (WorldClockに委譲)"""
        self._world_clock.advance_ticks(ticks)

    def to_string(self) -> str:
        return self._world_clock.to_string()

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return self._world_clock.to_dict()

    @classmethod
    def from_dict(cls, data: dict, event_bus: EventBus | None = None) -> "TimeSystem":
        ts = cls(event_bus=event_bus)
        ts._world_clock = WorldClock.from_dict(data, event_bus)
        return ts


class TurnQueue:
    """速度(Speed)に基づく厳密な行動順管理 (ステップ12, 13, 14, 15)"""

    def __init__(self, time_system: TimeSystem):
        self.time_system = time_system

    def step_next_actor(self, entities: list[Any]) -> tuple[Any | None, int]:
        """
        全キャラクターのenergyにspeedを加算し、最初に1000を超えたEntityを返す。
        戻り値: (行動可能になったEntity, 経過したTick数)
        """
        ticks_elapsed = 0
        while ticks_elapsed < 500:  # 無限ループ防止ガード
            # 閾値に達しているEntityがいるか探す
            ready_entities = [e for e in entities if e.energy >= ENERGY_THRESHOLD and e.hp > 0]
            if ready_entities:
                # 速度が最も速い、または余剰エネルギーが多い順
                ready_entities.sort(key=lambda e: (e.energy, e.speed), reverse=True)
                return ready_entities[0], ticks_elapsed

            # 誰も行動できない場合、全員にエネルギーをチャージ
            ticks_elapsed += 1
            for e in entities:
                if e.hp > 0:
                    e.energy += e.speed

            self.time_system.pass_ticks(10)

        return None, ticks_elapsed

    def process(self, engine: Any, delta_time: float = 1.0) -> None:
        """Process turn queue update in continuous game loop."""
