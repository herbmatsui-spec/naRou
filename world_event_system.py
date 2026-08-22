"""
World Event System Module (Steps 67-71)
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity

from typing_extensions import Self

from community_goal_manager import COMMUNITY_GOAL_MANAGER
from event_scheduler import EventScheduler
from ranking_manager import RankingManager
from reward_manager import RewardManager
from title_manager import TitleManager

# Phase 3 Step 12: QuestScheduler 連携
try:
    from quest_scheduler import (
        LogicOperator,
        QuestSchedule,
        QuestScheduler,
        ScheduleCondition,
        TimeWindow,
    )

    _HAS_QUEST_SCHEDULER = True
except ImportError:
    _HAS_QUEST_SCHEDULER = False


# Step 68: WorldEventData
@dataclass
class WorldEventData:
    """ワールドイベントデータ (Step 68)"""

    id: str
    name: str = ""
    description: str = ""
    trigger_conditions: dict[str, Any] = field(default_factory=dict)
    duration: int = 100
    effects: dict[str, Any] = field(default_factory=dict)
    story_triggers: list[str] = field(default_factory=list)
    # シーズンイベント用追加フィールド
    quarter: int | None = None  # 1:春, 2:夏, 3:秋, 4:冬
    rewards: dict[str, Any] = field(default_factory=dict)
    rankings: dict[str, Any] = field(default_factory=dict)
    titles: list[dict[str, Any]] = field(default_factory=list)
    community_goal: dict[str, Any] = field(default_factory=dict)
    announcement_period: int = 0  # イベント開始前何ターンから予告するか
    start_turn: int | None = None  # イベント開始ターン（Noneの場合はスケジュールしない）
    end_turn: int | None = None  # イベント終了ターン


# Step 69, 70: WorldEventRegistry
class WorldEventRegistry:
    """ワールドイベントレジストリ (Step 69, 70)"""

    _instance: WorldEventRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._events = {}
        return cls._instance

    def load(self, file_path: str = "data/world_events.yaml") -> None:
        """YAMLからワールドイベントを読み込む (Step 70)"""
        self._events = {}
        if not os.path.exists(file_path):
            self._events["blood_moon"] = WorldEventData(
                id="blood_moon",
                name="血の月",
                duration=100,
                quarter=None,
                rewards={},
                rankings={},
                titles=[],
                community_goal={},
                announcement_period=0,
                start_turn=None,
                end_turn=None,
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        e_dict = raw.get("world_events", {})
        for eid, edata in e_dict.items():
            self._events[eid] = WorldEventData(
                id=eid,
                name=edata.get("name", eid),
                description=edata.get("description", ""),
                trigger_conditions=edata.get("trigger_conditions", {}),
                duration=int(edata.get("duration", 100)),
                effects=edata.get("effects", {}),
                story_triggers=edata.get("story_triggers", []),
                quarter=edata.get("quarter"),
                rewards=edata.get("rewards", {}),
                rankings=edata.get("rankings", {}),
                titles=edata.get("titles", []),
                community_goal=edata.get("community_goal", {}),
                announcement_period=int(edata.get("announcement_period", 0)),
                start_turn=edata.get("start_turn"),
                end_turn=edata.get("end_turn"),
            )

    def get(self, event_id: str) -> WorldEventData | None:
        return self._events.get(event_id)

    def all_events(self) -> dict[str, WorldEventData]:
        return dict(self._events)


REGISTRY = WorldEventRegistry()

# マネージャークラスのシングルトンインスタンス
REWARD_MANAGER = RewardManager()
RANKING_MANAGER = RankingManager()
TITLE_MANAGER = TitleManager()
EVENT_SCHEDULER = EventScheduler(REGISTRY)


# Step 71: WorldEventManager
class WorldEventManager:
    """ワールドイベント発生・進行管理 (Step 71)"""

    def __init__(self, registry: WorldEventRegistry | None = None):
        self.registry = registry or REGISTRY

    def check_event_triggers(
        self, player: Entity, engine: Any | None = None, current_turn: int | None = None
    ) -> WorldEventData | None:
        """イベント発生判定 (Step 71)"""
        # スケジュールされたシーズンイベントをチェック
        if current_turn is not None:
            scheduled_event = EVENT_SCHEDULER.get_current_seasonal_event(current_turn)
            if scheduled_event and scheduled_event.id not in player.active_world_events:
                return scheduled_event
        # ランダムイベントをチェック（後方互換性のため）
        for eid, edata in self.registry.all_events().items():
            if eid not in player.active_world_events:
                cond = edata.trigger_conditions
                chance = cond.get("chance", 0.05)
                if random.random() < chance:
                    return edata
        return None

    def trigger_event(self, player: Entity, event_id: str, engine: Any | None = None) -> bool:
        """イベントを発生 (Step 71)"""
        edata = self.registry.get(event_id)
        if not edata or not player:
            return False

        if event_id not in player.active_world_events:
            player.active_world_events.append(event_id)

        if engine:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
            engine.log(
                f"🌌【世界変動】『{edata.name}』が発生した！ {edata.description}",
                (255, 100, 100),
            )
            # イベント発生時に報酬を付与（基本実装）
            REWARD_MANAGER.grant_event_rewards(player, edata)

            # Phase 3 Step 12: 動的スケジュール注入
            if hasattr(engine, "quest_scheduler"):
                self.inject_event_schedule(
                    event_id, engine.quest_scheduler, duration_turns=edata.duration
                )

        return True

    def add_event_points(
        self, player: Entity, event_id: str, action_type: str, amount: int = 1
    ) -> None:
        """指定されたイベントにプレイヤーのアクションからポイントを加算する"""
        event_data = self.registry.get(event_id)
        if event_data:
            points = RANKING_MANAGER.calculate_points(event_data, action_type, amount)
            if points > 0:
                RANKING_MANAGER.add_points(event_id, getattr(player, "id", str(id(player))), points)
                COMMUNITY_GOAL_MANAGER.add_progress(event_id, "total_points", points)

    def check_and_grant_event_titles(
        self, player: Entity, event_data: Any, stats: dict[str, Any]
    ) -> list[str]:
        """イベントデータとプレイヤーの統計に基づいて称号を付与し、新規獲得した称号を返す"""
        return TITLE_MANAGER.check_and_grant_titles(player, event_data, stats)

    def update_active_events(self, player: Entity, engine: Any | None = None) -> None:
        """アクティブイベントの進行 (Step 71)"""

    # Phase 3 Step 12: ワールドイベント連携 - 動的スケジュール注入
    def inject_event_schedule(
        self,
        event_id: str,
        scheduler: QuestScheduler,
        duration_turns: int = 100,
    ) -> bool:
        """ワールドイベント発生時に対応するクエストスケジュールを動的注入"""
        if not _HAS_QUEST_SCHEDULER:
            return False

        event_data = self.registry.get(event_id)
        if not event_data:
            return False

        # イベントタイプに基づくスケジュール生成
        schedule = self._create_event_schedule(event_data, duration_turns)
        if schedule:
            scheduler._schedules[schedule.quest_id] = schedule
            return True
        return False

    def _create_event_schedule(
        self,
        event_data: WorldEventData,
        duration_turns: int,
    ) -> QuestSchedule | None:
        """イベントデータからスケジュール生成"""
        if not _HAS_QUEST_SCHEDULER:
            return None

        # イベント名からスケジュールタイプ判定
        name_lower = event_data.name.lower()

        # 季節祭り系
        if any(kw in name_lower for kw in ["祭り", "festival", "祭典"]):
            season = "spring"
            if "夏" in event_data.name or "summer" in name_lower:
                season = "summer"
            elif "秋" in event_data.name or "autumn" in name_lower:
                season = "autumn"
            elif "冬" in event_data.name or "winter" in name_lower:
                season = "winter"

            return QuestSchedule(
                quest_id=f"event_{event_data.id}_festival",
                title=f"{event_data.name} 限定クエスト",
                description=f"{event_data.name} 開催期間中の特別依頼",
                conditions=[
                    ScheduleCondition(season=season, duration_days=duration_turns // 24),
                ],
                logic=LogicOperator.AND,
                rewards=event_data.rewards or {"gold": 1000, "fame": 50},
            )

        # 月齢系 (蝕・満月等)
        if any(kw in name_lower for kw in ["蝕", "eclipse", "月食", "日食", "満月", "full_moon"]):
            moon_phase = "full"
            if "新月" in event_data.name or "new_moon" in name_lower:
                moon_phase = "new"
            elif "上弦" in event_data.name or "waxing" in name_lower:
                moon_phase = "waxing"
            elif "下弦" in event_data.name or "waning" in name_lower:
                moon_phase = "waning"

            return QuestSchedule(
                quest_id=f"event_{event_data.id}_moon",
                title=f"{event_data.name} の儀式",
                description=f"{event_data.name} の夜にのみ実行可能な儀式",
                conditions=[
                    ScheduleCondition(moon_phase=moon_phase, duration_days=3),
                ],
                logic=LogicOperator.AND,
                rewards=event_data.rewards or {"artifact": "moon_fragment", "piety": 30},
            )

        # 流星群・天体系
        if any(kw in name_lower for kw in ["流星", "meteor", "星", "星屑"]):
            return QuestSchedule(
                quest_id=f"event_{event_data.id}_meteor",
                title=f"{event_data.name} 採集",
                description=f"{event_data.name} の夜に落ちる星屑を拾う",
                conditions=[
                    ScheduleCondition(time_windows=[TimeWindow("20:00", "04:00")], duration_days=2),
                ],
                logic=LogicOperator.AND,
                rewards=event_data.rewards or {"items": {"star_dust": 5}, "exp": 500},
            )

        # 汎用: 時間帯限定
        return QuestSchedule(
            quest_id=f"event_{event_data.id}_general",
            title=f"{event_data.name} 関連依頼",
            description=event_data.description or f"{event_data.name} に関連する依頼",
            conditions=[
                ScheduleCondition(
                    time_windows=[TimeWindow("06:00", "22:00")],
                    duration_days=duration_turns // 24,
                ),
            ],
            logic=LogicOperator.AND,
            rewards=event_data.rewards or {"gold": 500},
        )
