"""
World Clock System - Time Phase Definitions
Step 1: TimePhase Enum
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TimePhase(Enum):
    """時間帯フェーズ (DAWN: 0-6, DAY: 6-18, DUSK: 18-22, NIGHT: 22-24)"""
    DAWN = auto()   # 0-6時
    DAY = auto()    # 6-18時
    DUSK = auto()   # 18-22時
    NIGHT = auto()  # 22-24時

    @property
    def start_hour(self) -> int:
        """フェーズ開始時刻"""
        return {
            TimePhase.DAWN: 0,
            TimePhase.DAY: 6,
            TimePhase.DUSK: 18,
            TimePhase.NIGHT: 22,
        }[self]

    @property
    def end_hour(self) -> int:
        """フェーズ終了時刻 (次のフェーズの開始時刻)"""
        return {
            TimePhase.DAWN: 6,
            TimePhase.DAY: 18,
            TimePhase.DUSK: 22,
            TimePhase.NIGHT: 24,
        }[self]

    @property
    def display_name(self) -> str:
        """日本語表示名"""
        return {
            TimePhase.DAWN: "夜明け",
            TimePhase.DAY: "昼",
            TimePhase.DUSK: "夕暮れ",
            TimePhase.NIGHT: "夜",
        }[self]

    @property
    def short_name(self) -> str:
        """短縮表示名"""
        return {
            TimePhase.DAWN: "明",
            TimePhase.DAY: "昼",
            TimePhase.DUSK: "暮",
            TimePhase.NIGHT: "夜",
        }[self]

    @classmethod
    def from_hour(cls, hour: int) -> TimePhase:
        """時刻からフェーズを判定 (0-23)"""
        hour = hour % 24
        if 0 <= hour < 6:
            return cls.DAWN
        elif 6 <= hour < 18:
            return cls.DAY
        elif 18 <= hour < 22:
            return cls.DUSK
        else:
            return cls.NIGHT

    def hours_until_next(self, current_hour: int) -> int:
        """現在時刻から次のフェーズまでの時間"""
        current_hour = current_hour % 24
        end = self.end_hour
        if current_hour >= end:
            return (24 - current_hour) + end
        return end - current_hour


@dataclass
class TimeConfig:
    """時計設定データクラス"""
    ticks_per_hour: int = 100
    ticks_per_minute: int = 10
    start_year: int = 517
    start_month: int = 8
    start_day: int = 15
    start_hour: int = 8
    start_minute: int = 0


class WorldClock:
    """世界時計 - 絶対時間管理とフェーズ遷移"""

    def __init__(self, config: TimeConfig | None = None, event_bus=None):
        self.config = config or TimeConfig()
        self.event_bus = event_bus

        # 絶対時間
        self.year = self.config.start_year
        self.month = self.config.start_month
        self.day = self.config.start_day
        self.hour = self.config.start_hour
        self.minute = self.config.start_minute

        # ティックカウンタ
        self.total_ticks = 0
        self.ticks_in_current_hour = 0

        # 現在フェーズ
        self._current_phase = TimePhase.from_hour(self.hour)

        # NPCスケジュールレジストリ (遅延初期化)
        self._npc_registry = None

        # 音響マネージャー (遅延初期化)
        self._audio_manager = None

        # コールバック
        self._on_phase_changed_callbacks: list[callable] = []
        self._on_hour_changed_callbacks: list[callable] = []
        self._on_day_changed_callbacks: list[callable] = []

        # 音響コールバック登録
        self.on_phase_changed(self._on_phase_changed_audio)
        self.on_hour_changed(self._on_hour_changed_audio)
        self.on_day_changed(self._on_day_changed_audio)

    # --- 音響コールバック ---
    def _on_phase_changed_audio(self, old_phase: TimePhase, new_phase: TimePhase) -> None:
        if self._audio_manager is None:
            try:
                from naRou.audio.world_clock_audio import get_world_clock_audio_manager
            except ImportError:
                from audio.world_clock_audio import get_world_clock_audio_manager
            self._audio_manager = get_world_clock_audio_manager()
        self._audio_manager.on_phase_changed(old_phase, new_phase)

    def _on_hour_changed_audio(self, hour: int) -> None:
        if self._audio_manager is None:
            try:
                from naRou.audio.world_clock_audio import get_world_clock_audio_manager
            except ImportError:
                from audio.world_clock_audio import get_world_clock_audio_manager
            self._audio_manager = get_world_clock_audio_manager()
        self._audio_manager.on_hour_changed(hour)

    def _on_day_changed_audio(self, day: int) -> None:
        if self._audio_manager is None:
            try:
                from naRou.audio.world_clock_audio import get_world_clock_audio_manager
            except ImportError:
                from audio.world_clock_audio import get_world_clock_audio_manager
            self._audio_manager = get_world_clock_audio_manager()
        self._audio_manager.on_day_changed(day)

    # --- プロパティ ---
    @property
    def current_phase(self) -> TimePhase:
        return self._current_phase

    @property
    def npc_registry(self):
        """NPCスケジュールレジストリ取得 (遅延初期化)"""
        if self._npc_registry is None:
            from naRou.skill_eater.ai.npc_schedule import NPCScheduleRegistry
            self._npc_registry = NPCScheduleRegistry()
            self._npc_registry.load_from_yaml("data/npc_schedules.yaml")
        return self._npc_registry

    # --- NPCスケジュール連携 ---
    def get_active_npcs(self, player=None) -> list[str]:
        """現在フェーズでアクティブなNPC ID一覧取得 (条件チェック付き)"""
        registry = self.npc_registry
        active = registry.get_active_npcs(self._current_phase)
        if player:
            return [s.npc_id for s in active if registry.check_conditions(s, player)]
        return [s.npc_id for s in active]

    def get_active_npc_details(self, player=None) -> list[dict]:
        """現在フェーズでアクティブなNPC詳細取得"""
        registry = self.npc_registry
        active = registry.get_active_npcs(self._current_phase)
        result = []
        for s in active:
            if player and not registry.check_conditions(s, player):
                continue
            result.append({
                "npc_id": s.npc_id,
                "name": s.name,
                "location": s.location,
                "raid_chance": s.raid_chance,
            })
        return result

    def get_merchant_location(self, npc_id: str) -> str:
        """移動商人の現在地取得"""
        return self.npc_registry.get_merchant_location(npc_id, self._current_phase)

    # --- 施設稼働連携 ---
    @property
    def facility_registry(self):
        """施設レジストリ取得 (遅延初期化)"""
        if not hasattr(self, '_facility_registry') or self._facility_registry is None:
            try:
                from naRou.facility_system import FacilityRegistry
            except ImportError:
                from facility_system import FacilityRegistry
            self._facility_registry = FacilityRegistry()
            self._facility_registry.load_from_yaml("data/facility_schedules.yaml")
        return self._facility_registry

    def get_facility_efficiency(self, facility_id: str) -> float:
        """現在フェーズでの施設効率取得"""
        return self.facility_registry.get_efficiency(facility_id, self._current_phase)

    def is_facility_active(self, facility_id: str) -> bool:
        """施設が稼働中か判定"""
        return self.facility_registry.is_active(facility_id, self._current_phase)

    def get_active_facilities(self) -> list[str]:
        """現在稼働中の施設ID一覧"""
        return [
            f.facility_id for f in self.facility_registry.get_all_facilities()
            if self.facility_registry.is_active(f.facility_id, self._current_phase)
        ]

    # --- プレイヤー行動管理 ---
    @property
    def action_manager(self):
        """プレイヤー行動マネージャー取得 (遅延初期化)"""
        if not hasattr(self, '_action_manager') or self._action_manager is None:
            try:
                from naRou.player_actions import PlayerActionManager
            except ImportError:
                from player_actions import PlayerActionManager
            self._action_manager = PlayerActionManager()
            self._action_manager.load_from_yaml("data/action_costs.yaml")
        return self._action_manager

    def perform_action(self, action_type: str, player: Any, **kwargs) -> Any:
        """行動実行"""
        try:
            from naRou.player_actions import ActionResult, ActionType
        except ImportError:
            from player_actions import ActionResult, ActionType
        try:
            at = ActionType(action_type)
        except ValueError:
            return ActionResult(False, f"不明な行動: {action_type}")
        return self.action_manager.perform(at, player, **kwargs)

    def can_perform_action(self, action_type: str, player: Any, **kwargs) -> tuple[bool, str]:
        """行動可能判定"""
        try:
            from naRou.player_actions import ActionType
        except ImportError:
            from player_actions import ActionType
        try:
            at = ActionType(action_type)
        except ValueError:
            return False, f"不明な行動: {action_type}"
        return self.action_manager.can_perform(at, player, **kwargs)

    # --- コールバック登録 ---
    def on_phase_changed(self, callback: callable) -> None:
        self._on_phase_changed_callbacks.append(callback)

    def on_hour_changed(self, callback: callable) -> None:
        self._on_hour_changed_callbacks.append(callback)

    def on_day_changed(self, callback: callable) -> None:
        self._on_day_changed_callbacks.append(callback)

    # --- 時間経過 ---
    def advance(self, hours: int = 1) -> None:
        """指定時間経過させる"""
        for _ in range(hours):
            self._advance_one_hour()

    def _advance_one_hour(self) -> None:
        """1時間経過"""
        old_hour = self.hour
        old_phase = self._current_phase
        old_day = self.day

        self.hour += 1

        if self.hour >= 24:
            self.hour = 0
            self._advance_one_day()

        # フェーズ判定
        new_phase = TimePhase.from_hour(self.hour)
        if new_phase != old_phase:
            self._current_phase = new_phase
            self._fire_phase_changed(old_phase, new_phase)

        # 時変更コールバック
        if self.hour != old_hour:
            self._fire_hour_changed(self.hour)

        # 日変更コールバック
        if self.day != old_day:
            self._fire_day_changed(self.day)

    def _advance_one_day(self) -> None:
        """1日経過"""
        self.day += 1
        if self.day > 30:
            self.day = 1
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1

        # NEW_DAY イベント発行
        if self.event_bus:
            self.event_bus.publish("NEW_DAY", {"day": self.day, "month": self.month})

    def advance_ticks(self, ticks: int) -> None:
        """ティック経過 (内部用)"""
        self.total_ticks += ticks
        self.ticks_in_current_hour += ticks

        while self.ticks_in_current_hour >= self.config.ticks_per_hour:
            self.ticks_in_current_hour -= self.config.ticks_per_hour
            self._advance_one_hour()

    # --- コールバック発火 ---
    def _fire_phase_changed(self, old_phase: TimePhase, new_phase: TimePhase) -> None:
        if self.event_bus:
            self.event_bus.publish("PHASE_CHANGED", {"old": old_phase, "new": new_phase})
            # 検査官襲撃チェック (DAYフェーズ開始時)
            if new_phase == TimePhase.DAY:
                import random
                if random.random() < 0.3:  # 30%の確率で襲撃
                    self.event_bus.publish("INSPECTOR_RAID", {"intensity": random.randint(1, 3)})
            # 闘技場開催 (DUSK/NIGHT開始時)
            if new_phase in (TimePhase.DUSK, TimePhase.NIGHT):
                self.event_bus.publish("ARENA_OPEN", {"phase": new_phase})
            # 闘技場終了 (DAWN開始時)
            if new_phase == TimePhase.DAWN:
                self.event_bus.publish("ARENA_CLOSE", {})
        for cb in self._on_phase_changed_callbacks:
            try:
                cb(old_phase, new_phase)
            except Exception:
                pass

    def _fire_hour_changed(self, hour: int) -> None:
        # 時報用コールバック
        for cb in self._on_hour_changed_callbacks:
            try:
                cb(hour)
            except Exception:
                pass

    def _fire_day_changed(self, day: int) -> None:
        for cb in self._on_day_changed_callbacks:
            try:
                cb(day)
            except Exception:
                pass

    # --- 表示 ---
    def get_phase(self) -> TimePhase:
        return self._current_phase

    def to_string(self, short: bool = False) -> str:
        """時刻文字列取得"""
        phase_name = self._current_phase.short_name if short else self._current_phase.display_name
        return f"{self.year}年{self.month:02d}月{self.day:02d}日 {phase_name} {self.hour:02d}:{self.minute:02d}"

    def get_time_tuple(self) -> tuple[int, int, int, int, int]:
        return (self.year, self.month, self.day, self.hour, self.minute)

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "total_ticks": self.total_ticks,
            "ticks_in_current_hour": self.ticks_in_current_hour,
        }

    @classmethod
    def from_dict(cls, data: dict, event_bus=None) -> "WorldClock":
        config = TimeConfig()
        clock = cls(config, event_bus)
        clock.year = data.get("year", config.start_year)
        clock.month = data.get("month", config.start_month)
        clock.day = data.get("day", config.start_day)
        clock.hour = data.get("hour", config.start_hour)
        clock.minute = data.get("minute", config.start_minute)
        clock.total_ticks = data.get("total_ticks", 0)
        clock.ticks_in_current_hour = data.get("ticks_in_current_hour", 0)
        clock._current_phase = TimePhase.from_hour(clock.hour)
        return clock

    @classmethod
    def load_config(cls, path: str) -> TimeConfig:
        from pathlib import Path

        import yaml
        p = Path(path)
        if not p.exists():
            return TimeConfig()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        tc = data.get("time_config", {})
        return TimeConfig(
            ticks_per_hour=tc.get("ticks_per_hour", 100),
            ticks_per_minute=tc.get("ticks_per_minute", 10),
            start_year=tc.get("start_year", 517),
            start_month=tc.get("start_month", 8),
            start_day=tc.get("start_day", 15),
            start_hour=tc.get("start_hour", 8),
            start_minute=tc.get("start_minute", 0),
        )


# --- シングルトンアクセス (Step 7) ---
_world_clock_instance: WorldClock | None = None


def get_world_clock(event_bus=None) -> WorldClock:
    """グローバルWorldClockインスタンス取得"""
    global _world_clock_instance
    if _world_clock_instance is None:
        config = WorldClock.load_config("data/time_config.yaml")
        _world_clock_instance = WorldClock(config, event_bus)
    elif event_bus and _world_clock_instance.event_bus is None:
        _world_clock_instance.event_bus = event_bus
    return _world_clock_instance


def set_world_clock(clock: WorldClock) -> None:
    """グローバルWorldClockインスタンス設定 (初期化時用)"""
    global _world_clock_instance
    _world_clock_instance = clock
