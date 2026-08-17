"""
Main Quest System Module
Handles the progression of the primary story line, quest tracking, and reward distribution of rewards.
"""

from __future__ import annotations
import yaml
import os
from typing import List, Tuple, Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine
    from world_state_system import WorldPhase

class QuestStatus(Enum):
    LOCKED = auto()      # 解放前
    AVAILABLE = auto()   # 受注可能
    ACTIVE = auto()      # 進行中
    COMPLETED = auto()   # 完了
    FAILED = auto()      # 失敗

@dataclass
class QuestObjective:
    """クエストの達成条件 (設計書 2.2)"""
    objective_id: str
    description: str
    target_type: str  # "kill", "visit", "collect", "variable"
    target_id: str    # モンスター名, 場所名, アイテムID, 変数名
    required_count: int = 1
    current_count: int = 0
    is_completed: bool = False

    def update(self, target: str, amount: int = 1) -> bool:
        if self.target_id == target and not self.is_completed:
            self.current_count += amount
            if self.current_count >= self.required_count:
                self.is_completed = True
            return True
        return False

@dataclass
class MainQuest:
    """メインクエスト定義 (設計書 2.2)"""
    quest_id: str
    title: str
    description: str
    required_phase: str  # WorldPhaseの文字列
    objectives: List[QuestObjective]
    rewards: Dict[str, Any] = field(default_factory=dict)
    next_quest_id: Optional[str] = None
    status: QuestStatus = QuestStatus.LOCKED

class MainQuestSystem:
    """メインクエスト管理エンジン"""
    def __init__(self, data_path: str = "data/main_quests.yaml"):
        self.data_path = data_path
        self.quests: Dict[str, MainQuest] = {}
        self.active_quest_id: Optional[str] = None
        self.load_quests()

    def load_quests(self) -> None:
        """YAMLからクエストデータをロード"""
        if not os.path.exists(self.data_path):
            # デフォルトのクエストを定義（ファイルがない場合）
            self._create_default_quests()
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            q_list = data.get("main_quests", [])
            for q_data in q_list:
                objectives = [
                    QuestObjective(**obj) for obj in q_data.get("objectives", [])
                ]
                quest = MainQuest(
                    quest_id=q_data["quest_id"],
                    title=q_data["title"],
                    description=q_data["description"],
                    required_phase=q_data["required_phase"],
                    objectives=objectives,
                    rewards=q_data.get("rewards", {}),
                    next_quest_id=q_data.get("next_quest_id")
                )
                self.quests[quest.quest_id] = quest

    def _create_default_quests(self) -> None:
        """初期テスト用クエスト"""
        q1 = MainQuest(
            quest_id="prologue_01",
            title="運命の始まり",
            description="村の長から古文書を受け取り、世界の異変について知る。",
            required_phase="BEGINNING",
            objectives=[QuestObjective("talk_elder", "村の長に話しかける", "visit", "village_elder")],
            rewards={"gold": 100, "world_phase": "AWAKENING"},
            next_quest_id="awakening_01"
        )
        self.quests[q1.quest_id] = q1

    def update_progress(self, player: "Entity", event_type: str, target_id: str, amount: int = 1, engine: Optional["Engine"] = None) -> List[str]:
        """
        イベントに基づいてクエスト進行を更新する。
        event_type: "kill", "visit", "collect", "variable"
        """
        logs = []
        if not self.active_quest_id:
            # アクティブなクエストがない場合、条件を満たすものを自動的にアクティブにする
            self._try_activate_next_quest(player, engine)
            if not self.active_quest_id:
                return logs

        quest = self.quests.get(self.active_quest_id)
        if not quest:
            return logs

        # 全ての目的をチェック
        changed = False
        for obj in quest.objectives:
            if obj.target_type == event_type:
                if obj.update(target_id, amount):
                    changed = True
                    logs.append(f"【クエスト進行】{quest.title}: {obj.description} ({obj.current_count}/{obj.required_count})")

        # クエスト完了判定
        if all(obj.is_completed for obj in quest.objectives):
            logs.append(f"★メインクエスト【{quest.title}】を完了した！")
            self._complete_quest(player, quest, engine)
            
        return logs

    def _try_activate_next_quest(self, player: "Entity", engine: Optional["Engine"]) -> None:
        """条件を満たすクエストをアクティブにする"""
        from world_state_system import WorldStateManager, REGISTRY
        ws_manager = WorldStateManager(REGISTRY)
        current_phase = ws_manager.get_phase().name

        for q_id, q in self.quests.items():
            if q.status == QuestStatus.LOCKED and q.required_phase == current_phase:
                q.status = QuestStatus.ACTIVE
                self.active_quest_id = q_id
                # プレイヤーに通知するためのログはupdate_progress側で処理されるか、EventBusで飛ばす
                break

    def _complete_quest(self, player: "Entity", quest: MainQuest, engine: Optional["Engine"]) -> None:
        """クエスト完了処理と報酬付与"""
        quest.status = QuestStatus.COMPLETED
        
        # 報酬付与
        rewards = quest.rewards
        if "gold" in rewards:
            # SurvivalSystem経由でゴールド追加（実際の実装に合わせて調整）
            if hasattr(engine, "survival_system"):
                engine.survival_system.gold += rewards["gold"]
        
        if "world_phase" in rewards:
            # ワールドフェーズの更新
            if engine:
                from world_state_system import WorldStateManager, REGISTRY
                ws_manager = WorldStateManager(REGISTRY)
                try:
                    from world_state_system import WorldPhase
                    ws_manager.set_phase(WorldPhase[rewards["world_phase"]], engine)
                except KeyError:
                    pass

        # 次のクエストを準備
        self.active_quest_id = None # 次の更新タイミングで _try_activate_next_quest が呼ばれる
        if quest.next_quest_id and quest.next_quest_id in self.quests:
            self.quests[quest.next_quest_id].status = QuestStatus.AVAILABLE
