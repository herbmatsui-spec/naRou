"""
Elona Roguelike Masterpiece - Time, Energy Tick, & Speed System
Steps 10 to 18 (Resolving speed & action timing contradictions)
"""

from __future__ import annotations

from typing import Any

from constants import ENERGY_THRESHOLD
from core_framework import EventBus


class TimeSystem:
    """Tickベースの絶対時間とElona風エネルギーチャージシステム (ステップ9, 10, 11, 12, 17)"""

    def __init__(
        self,
        year: int = 517,
        month: int = 8,
        day: int = 15,
        hour: int = 8,
        minute: int = 0,
        event_bus: EventBus | None = None,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.ticks = 0
        self.event_bus = event_bus

    def pass_ticks(self, ticks: int = 10) -> None:
        """絶対Tickの経過と日付計算"""
        self.ticks += ticks
        # 100 Ticks = 1分として計算
        mins_passed = ticks // 100
        if mins_passed > 0 or (self.ticks % 100 < ticks):
            self.minute += max(1, mins_passed)
            while self.minute >= 60:
                self.minute -= 60
                self.hour += 1
                while self.hour >= 24:
                    self.hour -= 24
                    self.day += 1
                    if self.event_bus:
                        self.event_bus.publish(
                            "NEW_DAY", {"day": self.day, "month": self.month}
                        )
                    if self.day > 30:
                        self.day = 1
                        self.month += 1
                        if self.event_bus:
                            self.event_bus.publish("NEW_MONTH", {"month": self.month})
                        if self.month > 12:
                            self.month = 1
                            self.year += 1

    def to_string(self) -> str:
        return f"{self.year}年{self.month:02d}月{self.day:02d}日 {self.hour:02d}:{self.minute:02d}"


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
            ready_entities = [
                e for e in entities if e.energy >= ENERGY_THRESHOLD and e.hp > 0
            ]
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
