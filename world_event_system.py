"""
World Event System Module (Steps 67-71)
"""

from __future__ import annotations
import os
import yaml
import random
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity

from reward_manager import RewardManager
from ranking_manager import RankingManager
from title_manager import TitleManager
from event_scheduler import EventScheduler
from community_goal_manager import COMMUNITY_GOAL_MANAGER


# Step 68: WorldEventData
@dataclass
class WorldEventData:
    """ワールドイベントデータ (Step 68)"""
    id: str
    name: str = ""
    description: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    duration: int = 100
    effects: Dict[str, Any] = field(default_factory=dict)
    story_triggers: List[str] = field(default_factory=list)
    # シーズンイベント用追加フィールド
    quarter: Optional[int] = None  # 1:春, 2:夏, 3:秋, 4:冬
    rewards: Dict[str, Any] = field(default_factory=dict)
    rankings: Dict[str, Any] = field(default_factory=dict)
    titles: List[Dict[str, Any]] = field(default_factory=list)
    community_goal: Dict[str, Any] = field(default_factory=dict)
    announcement_period: int = 0  # イベント開始前何ターンから予告するか
    start_turn: Optional[int] = None  # イベント開始ターン（Noneの場合はスケジュールしない）
    end_turn: Optional[int] = None    # イベント終了ターン


# Step 69, 70: WorldEventRegistry
class WorldEventRegistry:
    """ワールドイベントレジストリ (Step 69, 70)"""
    _instance: Optional[WorldEventRegistry] = None

    def __new__(cls) -> WorldEventRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._events = {}
        return cls._instance

    def load(self, file_path: str = "data/world_events.yaml") -> None:
        """YAMLからワールドイベントを読み込む (Step 70)"""
        self._events = {}
        if not os.path.exists(file_path):
            self._events["blood_moon"] = WorldEventData(
                id="blood_moon", name="血の月", duration=100,
                quarter=None, rewards={}, rankings={}, titles=[], community_goal={},
                announcement_period=0, start_turn=None, end_turn=None
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
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
                end_turn=edata.get("end_turn")
            )

    def get(self, event_id: str) -> Optional[WorldEventData]:
        return self._events.get(event_id)

    def all_events(self) -> Dict[str, WorldEventData]:
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
    def __init__(self, registry: Optional[WorldEventRegistry] = None):
        self.registry = registry or REGISTRY

    def check_event_triggers(self, player: "Entity", engine: Optional[Any] = None, current_turn: Optional[int] = None) -> Optional[WorldEventData]:
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

    def trigger_event(self, player: "Entity", event_id: str, engine: Optional[Any] = None) -> bool:
        """イベントを発生 (Step 71)"""
        edata = self.registry.get(event_id)
        if not edata or not player:
            return False

        if event_id not in player.active_world_events:
            player.active_world_events.append(event_id)

        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"🌌【世界変動】『{edata.name}』が発生した！ {edata.description}", (255, 100, 100))
            # イベント発生時に報酬を付与（基本実装）
            REWARD_MANAGER.grant_event_rewards(player, edata)

        return True

    def add_event_points(self, player: "Entity", event_id: str, action_type: str, amount: int = 1) -> None:
        """指定されたイベントにプレイヤーのアクションからポイントを加算する"""
        event_data = self.registry.get(event_id)
        if event_data:
            points = RANKING_MANAGER.calculate_points(event_data, action_type, amount)
            if points > 0:
                RANKING_MANAGER.add_points(event_id, getattr(player, 'id', str(id(player))), points)
                COMMUNITY_GOAL_MANAGER.add_progress(event_id, "total_points", points)

    def check_and_grant_event_titles(self, player: "Entity", event_data: Any, stats: Dict[str, Any]) -> List[str]:
        """イベントデータとプレイヤーの統計に基づいて称号を付与し、新規獲得した称号を返す"""
        return TITLE_MANAGER.check_and_grant_titles(player, event_data, stats)

    def update_active_events(self, player: "Entity", engine: Optional[Any] = None) -> None:
        """アクティブイベントの進行 (Step 71)"""
        pass
