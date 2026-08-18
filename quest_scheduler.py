"""
Quest Scheduler Module (偏執的クエストシステム / 設計書 Phase 3 Step 10)
5軸スケジューラエンジン: 時間・天候・季節・月齢・フェーズによるクエスト利用可否判定。
"""

from __future__ import annotations

import os
import yaml
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from enum import Enum, auto

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine
    from world_state_system import WorldStateManager


class ScheduleAxis(Enum):
    """スケジュール判定軸"""
    TIME_OF_DAY = auto()      # 時間帯 (HH:MM)
    DAY_OF_WEEK = auto()      # 曜日 (0-6)
    MOON_PHASE = auto()       # 月齢
    SEASON = auto()           # 季節
    WEATHER = auto()          # 天候
    WORLD_PHASE = auto()      # ワールドフェーズ


class LogicOperator(Enum):
    AND = auto()
    OR = auto()


@dataclass
class TimeWindow:
    """時間窓 (HH:MM 形式)"""
    start: str      # "05:00"
    end: str        # "19:00"

    def contains(self, current_time: datetime) -> bool:
        """現在時刻が窓内か判定（日付跨ぎ対応）"""
        current_minutes = current_time.hour * 60 + current_time.minute
        start_minutes = self._parse_time(self.start)
        end_minutes = self._parse_time(self.end)

        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes <= end_minutes
        # 日付跨ぎ (例: 23:00-03:00)
        return current_minutes >= start_minutes or current_minutes <= end_minutes

    def _parse_time(self, t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m


@dataclass
class ScheduleCondition:
    """単一スケジュール条件"""
    # テンプレート参照
    template: Optional[str] = None
    # 直接指定
    time_windows: List[TimeWindow] = field(default_factory=list)
    day_of_week: Optional[int] = None          # 0-6
    moon_phase: Optional[str] = None           # new|waxing|full|waning
    season: Optional[str] = None               # spring|summer|autumn|winter
    weather: Optional[str] = None              # clear|rain|storm|snow|fog
    world_phase: Optional[str] = None          # ワールドフェーズ名
    location: Optional[str] = None             # 場所制限
    npcs: List[str] = field(default_factory=list)  # 特定NPCでのみ利用可
    duration_days: int = 0                     # 期間延長（月齢用等）

    def __post_init__(self):
        # テンプレートから展開は外部で行う
        pass

    def evaluate(self, context: ScheduleContext) -> bool:
        """条件評価"""
        # 時間帯
        if self.time_windows:
            if not any(tw.contains(context.current_time) for tw in self.time_windows):
                return False
        # 曜日
        if self.day_of_week is not None:
            if context.day_of_week != self.day_of_week:
                return False
        # 月齢
        if self.moon_phase is not None:
            if context.moon_phase != self.moon_phase:
                return False
        # 季節
        if self.season is not None:
            if context.season != self.season:
                return False
        # 天候
        if self.weather is not None:
            if context.weather != self.weather:
                return False
        # ワールドフェーズ
        if self.world_phase is not None:
            if context.world_phase != self.world_phase:
                return False
        return True


@dataclass
class QuestSchedule:
    """クエストスケジュール定義"""
    quest_id: str
    title: str = ""
    description: str = ""
    conditions: List[ScheduleCondition] = field(default_factory=list)
    logic: LogicOperator = LogicOperator.AND
    requirements: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def is_available(self, context: "ScheduleContext") -> bool:
        """利用可能か判定"""
        if not self.enabled:
            return False
        if not self.conditions:
            return True  # 条件なし = 常時利用可

        results = [c.evaluate(context) for c in self.conditions]
        if self.logic == LogicOperator.AND:
            return all(results)
        return any(results)


class ScheduleContext:
    """スケジュール評価用コンテキスト（ワールド状態のスナップショット）"""

    def __init__(
        self,
        current_time: Optional[datetime] = None,
        day_of_week: Optional[int] = None,
        moon_phase: Optional[str] = None,
        season: Optional[str] = None,
        weather: Optional[str] = None,
        world_phase: Optional[str] = None,
        location: Optional[str] = None,
        npc_id: Optional[str] = None,
    ):
        self.current_time = current_time or datetime.now()
        # day_of_week 未指定時は current_time から計算 (0=月曜 ... 6=日曜)
        self.day_of_week = day_of_week if day_of_week is not None else self.current_time.weekday()
        self.moon_phase = moon_phase
        self.season = season
        self.weather = weather
        self.world_phase = world_phase
        self.location = location
        self.npc_id = npc_id

    @classmethod
    def from_engine(cls, engine: "Engine") -> "ScheduleContext":
        """エンジンからコンテキスト生成"""
        ws_mgr = getattr(engine, 'world_state_manager', None)
        if ws_mgr:
            phase = ws_mgr.get_phase()
            world_phase = phase.name if phase else None
            # 時刻・季節・天候・月齢は WorldStateManager から取得想定
            return cls(
                current_time=ws_mgr.get_current_datetime() if hasattr(ws_mgr, 'get_current_datetime') else None,
                day_of_week=ws_mgr.get_day_of_week() if hasattr(ws_mgr, 'get_day_of_week') else None,
                moon_phase=ws_mgr.get_moon_phase() if hasattr(ws_mgr, 'get_moon_phase') else None,
                season=ws_mgr.get_season() if hasattr(ws_mgr, 'get_season') else None,
                weather=ws_mgr.get_weather() if hasattr(ws_mgr, 'get_weather') else None,
                world_phase=world_phase,
            )
        return cls()


class QuestScheduler:
    """クエストスケジューラエンジン"""

    def __init__(self, data_path: str = "data/quest_schedules.yaml"):
        self.data_path = data_path
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._schedules: Dict[str, QuestSchedule] = {}
        self._overrides: Dict[str, Dict[str, Any]] = {}
        self.load_schedules()

    def load_schedules(self) -> None:
        """YAML からスケジュール読み込み"""
        self._templates = {}
        self._schedules = {}
        self._overrides = {}

        if not os.path.exists(self.data_path):
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # テンプレート読み込み
        self._templates = data.get("schedule_templates", {})

        # スケジュール読み込み
        for s_data in data.get("quest_schedules", []):
            schedule = self._parse_schedule(s_data)
            self._schedules[schedule.quest_id] = schedule

        # 上書き読み込み
        self._overrides = {o["quest_id"]: o for o in data.get("schedule_overrides", [])}

    def _parse_schedule(self, s_data: Dict[str, Any]) -> QuestSchedule:
        """スケジュールデータから QuestSchedule 構築"""
        conditions = []
        schedule_data = s_data.get("schedule", {})

        # テンプレート単体
        if "template" in schedule_data:
            conditions.append(self._expand_template(schedule_data["template"], schedule_data))
        # 複数条件
        elif "conditions" in schedule_data:
            logic = LogicOperator[schedule_data.get("logic", "AND")]
            for cond_data in schedule_data["conditions"]:
                if "template" in cond_data:
                    conditions.append(self._expand_template(cond_data["template"], cond_data))
                else:
                    conditions.append(self._parse_condition(cond_data))
            return QuestSchedule(
                quest_id=s_data["quest_id"],
                title=s_data.get("title", ""),
                description=s_data.get("description", ""),
                conditions=conditions,
                logic=logic,
                requirements=s_data.get("requirements", {}),
                rewards=s_data.get("rewards", {}),
                enabled=s_data.get("enabled", True),
            )

        return QuestSchedule(
            quest_id=s_data["quest_id"],
            title=s_data.get("title", ""),
            description=s_data.get("description", ""),
            conditions=conditions,
            logic=LogicOperator.AND,
            requirements=s_data.get("requirements", {}),
            rewards=s_data.get("rewards", {}),
            enabled=s_data.get("enabled", True),
        )

    def _expand_template(self, template_name: str, override: Dict[str, Any]) -> ScheduleCondition:
        """テンプレート展開 + 上書きマージ"""
        tmpl = self._templates.get(template_name, {})
        merged = {**tmpl, **override}
        return self._parse_condition(merged)

    def _parse_condition(self, data: Dict[str, Any]) -> ScheduleCondition:
        """条件データから ScheduleCondition 構築"""
        time_windows = []
        for tw in data.get("time_windows", []):
            time_windows.append(TimeWindow(tw["start"], tw["end"]))

        return ScheduleCondition(
            time_windows=time_windows,
            day_of_week=data.get("day_of_week"),
            moon_phase=data.get("moon_phase"),
            season=data.get("season"),
            weather=data.get("weather"),
            world_phase=data.get("world_phase"),
            location=data.get("location"),
            npcs=data.get("npcs", []),
            duration_days=data.get("duration_days", 0),
        )

    def get_schedule(self, quest_id: str) -> Optional[QuestSchedule]:
        """スケジュール取得"""
        return self._schedules.get(quest_id)

    def get_available_quests(
        self,
        context: ScheduleContext,
        player: Optional["Entity"] = None,
    ) -> List[QuestSchedule]:
        """現在利用可能なクエスト一覧取得"""
        available = []
        for schedule in self._schedules.values():
            # 上書きチェック
            override = self._overrides.get(schedule.quest_id)
            if override and not override.get("enabled", True):
                # 日付条件付き無効化の場合、日付が合致する時のみ無効
                if self._check_override(override, context):
                    continue
                # 日付不一致なら無効化しない（overrideを無視）

            if schedule.is_available(context):
                # 要件チェック（プレイヤー渡し時）
                if player and not self._check_requirements(schedule, player):
                    continue
                available.append(schedule)
        return available

    def _check_requirements(self, schedule: QuestSchedule, player: "Entity") -> bool:
        """要件チェック"""
        req = schedule.requirements
        if not req:
            return True

        # 最小好感度
        if "min_favorability" in req:
            # 関係システム連携
            from relationship_system import REGISTRY as REL_REG
            rel_mgr = REL_REG
            # ここでは簡易チェック（実装時に詳細化）
            pass

        # 最小レベル
        if "min_level" in req:
            if player.level < req["min_level"]:
                return False

        # スキルチェック
        for skill_key in ["skill_performance", "skill_herbalism"]:
            if skill_key in req:
                skill_name = skill_key.replace("skill_", "")
                if hasattr(player, 'skills'):
                    skill = player.skills.get(skill_name)
                    if not skill or skill.level < req[skill_key]:
                        return False

        # メインクエスト完了チェック
        if "main_quest" in req:
            from main_quest_system import MainQuestSystem
            mqs = MainQuestSystem()
            quest = mqs.quests.get(req["main_quest"])
            if not quest or quest.status != quest.status.__class__.COMPLETED:
                return False

        return True

    def _check_override(self, override: Dict[str, Any], context: ScheduleContext) -> bool:
        """上書きが現在のコンテキストに適用されるか判定"""
        # 日付指定がある場合
        if "date" in override:
            date_str = override["date"]
            # 形式: "year_1_month_3_day_15"
            try:
                parts = date_str.split("_")
                year = int(parts[1])
                month = int(parts[3])
                day = int(parts[5])
                target_date = datetime(year, month, day)
                return context.current_time.date() == target_date.date()
            except (ValueError, IndexError):
                return False
        if "date_range" in override:
            dr = override["date_range"]
            try:
                start_str = dr["start"]
                end_str = dr["end"]
                start_parts = start_str.split("_")
                end_parts = end_str.split("_")
                start_date = datetime(int(start_parts[1]), int(start_parts[3]), int(start_parts[5]))
                end_date = datetime(int(end_parts[1]), int(end_parts[3]), int(end_parts[5]))
                return start_date.date() <= context.current_time.date() <= end_date.date()
            except (ValueError, IndexError, KeyError):
                return False
        return True

    def is_quest_available(
        self,
        quest_id: str,
        context: ScheduleContext,
        player: Optional["Entity"] = None,
    ) -> bool:
        """特定クエストの利用可否判定"""
        schedule = self._schedules.get(quest_id)
        if not schedule:
            return False

        override = self._overrides.get(quest_id)
        if override and not override.get("enabled", True):
            # 日付条件付き無効化の場合、日付が合致する時のみ無効
            if not self._check_override(override, context):
                pass  # 条件不一致なら無効化しない
            else:
                return False

        if not schedule.is_available(context):
            return False

        if player and not self._check_requirements(schedule, player):
            return False

        return True

    def get_next_available_time(
        self,
        quest_id: str,
        from_time: Optional[datetime] = None,
        max_days: int = 30,
    ) -> Optional[datetime]:
        """次回利用可能時刻を予測（簡易版：日単位で探索、時間窓も考慮）"""
        from_time = from_time or datetime.now()
        schedule = self._schedules.get(quest_id)
        if not schedule:
            return None

        # 全条件から時間窓を収集
        time_windows = []
        for cond in schedule.conditions:
            time_windows.extend(cond.time_windows)

        if not time_windows:
            # 時間窓指定なしなら日付のみで判定
            for day in range(max_days):
                check_time = from_time + timedelta(days=day)
                context = ScheduleContext(current_time=check_time)
                if self.is_quest_available(quest_id, context):
                    return check_time
            return None

        # 時間窓がある場合：各日について各時間窓をチェック
        for day in range(max_days):
            base_date = (from_time + timedelta(days=day)).date()
            for tw in time_windows:
                # 時間窓の開始時刻をその日の日付で作成
                start_h, start_m = map(int, tw.start.split(":"))
                candidate = datetime.combine(base_date, datetime.min.time().replace(hour=start_h, minute=start_m))
                if candidate < from_time:
                    continue
                context = ScheduleContext(current_time=candidate)
                if self.is_quest_available(quest_id, context):
                    return candidate
        return None


# グローバルシングルトン
QUEST_SCHEDULER = QuestScheduler()


__all__ = [
    "ScheduleAxis",
    "LogicOperator",
    "TimeWindow",
    "ScheduleCondition",
    "QuestSchedule",
    "ScheduleContext",
    "QuestScheduler",
    "QUEST_SCHEDULER",
]