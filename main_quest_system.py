"""
Main Quest System Module
Handles the progression of the primary story line, quest tracking, and reward distribution of rewards.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine
    from quest_condition_ast import ConditionNode
    from quest_condition_evaluator import EvaluationContext


# 遅延インポートで循環参照回避
def _get_condition_parser():
    from quest_condition_parser import parse_condition_from_yaml

    return parse_condition_from_yaml


def _get_evaluator():
    from quest_condition_evaluator import EvaluationContext, evaluate_condition

    return evaluate_condition, EvaluationContext


class QuestStatus(Enum):
    LOCKED = auto()  # 解放前
    AVAILABLE = auto()  # 受注可能
    ACTIVE = auto()  # 進行中
    COMPLETED = auto()  # 完了
    FAILED = auto()  # 失敗


@dataclass
class QuestObjective:
    """クエストの達成条件 (設計書 2.2 + CQCT拡張 + ナラティブDAG拡張)"""

    objective_id: str
    description: str
    target_type: str = ""  # 従来互換: "kill", "visit", "collect", "variable"
    target_id: str = ""  # 従来互換: モンスター名, 場所名, アイテムID, 変数名
    required_count: int = 1
    current_count: int = 0
    is_completed: bool = False
    # CQCT拡張フィールド
    condition_tree: ConditionNode | None = None  # 複合条件AST
    condition_dsl: str = ""  # DSL文字列（YAML保存用）
    auto_evaluate: bool = True  # イベント駆動で自動評価するか
    # ナラティブDAG拡張 (Phase 4 Step 17)
    narrative_dag_id: str = ""  # 関連ナラティブDAG ID
    narrative_started: bool = False  # ナラティブ開始済みフラグ

    def update(self, target: str, amount: int = 1) -> bool:
        """従来互換：単純カウント更新"""
        if self.target_id == target and not self.is_completed:
            self.current_count += amount
            if self.current_count >= self.required_count:
                self.is_completed = True
            return True
        return False

    def evaluate(self, context: EvaluationContext) -> bool:
        """CQCT評価：条件ツリーがある場合はそれを優先"""
        if self.condition_tree:
            self.is_completed = self.condition_tree.evaluate(context)
            return self.is_completed
        # フォールバック：従来のカウントベース
        return self.is_completed

    def to_dict(self) -> dict[str, Any]:
        """シリアライズ"""
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "is_completed": self.is_completed,
            "condition_dsl": self.condition_dsl,
            "auto_evaluate": self.auto_evaluate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestObjective:
        """デシリアライズ（condition_treeは別途構築）"""
        obj = cls(
            objective_id=data.get("objective_id", ""),
            description=data.get("description", ""),
            target_type=data.get("target_type", ""),
            target_id=data.get("target_id", ""),
            required_count=data.get("required_count", 1),
            current_count=data.get("current_count", 0),
            is_completed=data.get("is_completed", False),
            condition_dsl=data.get("condition_dsl", ""),
            auto_evaluate=data.get("auto_evaluate", True),
        )
        return obj

    def build_condition_tree(self) -> None:
        """DSL文字列から条件ツリーを構築（遅延初期化）"""
        if self.condition_dsl and not self.condition_tree:
            parser = _get_condition_parser()
            self.condition_tree = parser(self.condition_dsl)


@dataclass
class MainQuest:
    """メインクエスト定義 (設計書 2.2 + CQCT拡張 + ナラティブDAG拡張)"""

    quest_id: str
    title: str
    description: str
    required_phase: str  # WorldPhaseの文字列
    objectives: list[QuestObjective]
    rewards: dict[str, Any] = field(default_factory=dict)
    next_quest_id: str | None = None
    status: QuestStatus = QuestStatus.LOCKED
    # CQCT拡張: クエスト全体の解放条件
    unlock_condition: ConditionNode | None = None
    unlock_dsl: str = ""
    # ナラティブDAG拡張 (Phase 4 Step 17)
    narrative_dag_id: str = ""  # クエスト全体のナラティブDAG

    def check_unlock(self, context: EvaluationContext) -> bool:
        """解放条件チェック"""
        if self.unlock_condition:
            return self.unlock_condition.evaluate(context)
        # フォールバック: required_phaseのみ
        from world_state_system import REGISTRY, WorldStateManager

        ws_manager = WorldStateManager(REGISTRY)
        return ws_manager.get_phase().name == self.required_phase

    def is_completed(self) -> bool:
        return all(obj.is_completed for obj in self.objectives)

    def build_condition_trees(self) -> None:
        """全ての目的と解放条件のツリーを構築"""
        for obj in self.objectives:
            obj.build_condition_tree()
        if self.unlock_dsl and not self.unlock_condition:
            parser = _get_condition_parser()
            self.unlock_condition = parser(self.unlock_dsl)


class MainQuestSystem:
    """メインクエスト管理エンジン"""

    def __init__(self, data_path: str = "data/main_quests.yaml"):
        self.data_path = data_path
        self.quests: dict[str, MainQuest] = {}
        self.active_quest_id: str | None = None
        self.load_quests()

    def load_quests(self) -> None:
        """YAMLからクエストデータをロード"""
        if not os.path.exists(self.data_path):
            # デフォルトのクエストを定義（ファイルがない場合）
            self._create_default_quests()
            return

        with open(self.data_path, encoding="utf-8") as f:
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
                    next_quest_id=q_data.get("next_quest_id"),
                    unlock_dsl=q_data.get("unlock_condition", ""),
                    narrative_dag_id=q_data.get("narrative_dag_id", ""),
                )
                self.quests[quest.quest_id] = quest

        # 条件ツリーの遅延構築
        for quest in self.quests.values():
            quest.build_condition_trees()

    def _create_default_quests(self) -> None:
        """初期テスト用クエスト"""
        q1 = MainQuest(
            quest_id="prologue_01",
            title="運命の始まり",
            description="村の長から古文書を受け取り、世界の異変について知る。",
            required_phase="BEGINNING",
            objectives=[
                QuestObjective(
                    "talk_elder",
                    "村の長に話しかける",
                    "visit",
                    "village_elder",
                    narrative_dag_id="prologue_branching",
                )
            ],
            rewards={"gold": 100, "world_phase": "AWAKENING"},
            next_quest_id="awakening_01",
            narrative_dag_id="prologue_branching",
        )
        self.quests[q1.quest_id] = q1

    def update_progress(
        self,
        player: Entity,
        event_type: str,
        target_id: str,
        amount: int = 1,
        engine: Engine | None = None,
    ) -> list[str]:
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

        # コンテキスト作成
        _evaluator_func, EvaluationContext = _get_evaluator()
        context = EvaluationContext(player, engine)

        # 全ての目的をチェック
        for obj in quest.objectives:
            # 自動評価が有効かつ条件ツリーがある場合は評価
            if obj.auto_evaluate and obj.condition_tree:
                # イベントタイプが条件に関連しているかチェック（簡易版）
                if obj.evaluate(context):
                    logs.append(
                        f"【クエスト進行】{quest.title}: {obj.description} (達成！)"
                    )
            # 従来の更新ロジック（後方互換性）
            elif obj.target_type == event_type:
                if obj.update(target_id, amount):
                    logs.append(
                        f"【クエスト進行】{quest.title}: {obj.description} ({obj.current_count}/{obj.required_count})"
                    )

        # クエスト完了判定
        if all(obj.is_completed for obj in quest.objectives):
            logs.append(f"★メインクエスト【{quest.title}】を完了した！")
            self._complete_quest(player, quest, engine)

        return logs

    def _try_activate_next_quest(self, player: Entity, engine: Engine | None) -> None:
        """条件を満たすクエストをアクティブにする"""
        from world_state_system import REGISTRY, WorldStateManager

        ws_manager = WorldStateManager(REGISTRY)
        # TODO: フェーズ名をログ/UI に使用

        # コンテキスト作成
        _evaluator_func, EvaluationContext = _get_evaluator()
        context = EvaluationContext(player, engine)

        for q_id, q in self.quests.items():
            if q.status == QuestStatus.LOCKED and q.check_unlock(context):
                q.status = QuestStatus.ACTIVE
                self.active_quest_id = q_id
                # プレイヤーに通知するためのログはupdate_progress側で処理されるか、EventBusで飛ばす
                break

    def _complete_quest(
        self, player: Entity, quest: MainQuest, engine: Engine | None
    ) -> None:
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
                from world_state_system import REGISTRY, WorldStateManager

                ws_manager = WorldStateManager(REGISTRY)
                try:
                    from world_state_system import WorldPhase

                    ws_manager.set_phase(WorldPhase[rewards["world_phase"]], engine)
                except KeyError:
                    pass

        # 次のクエストを準備
        self.active_quest_id = (
            None  # 次の更新タイミングで _try_activate_next_quest が呼ばれる
        )
        if quest.next_quest_id and quest.next_quest_id in self.quests:
            self.quests[quest.next_quest_id].status = QuestStatus.AVAILABLE

        # クエスト完了時にナラティブDAGがある場合は自動開始
        if quest.narrative_dag_id and engine:
            self._start_quest_narrative(quest.narrative_dag_id, player, engine)

    def _start_quest_narrative(
        self, dag_id: str, player: Entity, engine: Engine
    ) -> list[str]:
        """クエスト関連ナラティブを開始"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            state = NARRATIVE_EXECUTOR.start_narrative(dag_id, player)
            if state:
                return [f"【ナラティブ開始】{dag_id}"]
        except Exception as e:
            return [f"ナラティブ開始エラー: {e}"]
        return []

    def make_narrative_choice(self, player: Entity, edge_id: str) -> list[str]:
        """ナラティブ選択肢を実行"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.make_choice(player, edge_id)
        except Exception as e:
            return [f"ナラティブ選択エラー: {e}"]

    def get_active_narrative_node(self, player: Entity):
        """現在のアクティブなナラティブノードを取得"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.get_current_node(player)
        except Exception:
            # TODO: handle exception properly
            return None

    def get_narrative_choices(self, player: Entity) -> list[dict[str, Any]]:
        """現在のナラティブで選択可能な選択肢一覧を取得"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            edges = NARRATIVE_EXECUTOR.get_available_choices(player)
            return [
                {
                    "edge_id": e.edge_id,
                    "choice_text": e.choice_text,
                    "edge_type": e.edge_type.name,
                }
                for e in edges
            ]
        except Exception:
            # TODO: handle exception properly
            return []

    def get_available_endings(self, player: Entity) -> list[dict[str, Any]]:
        """解放可能なエンディング一覧を取得"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            state = NARRATIVE_EXECUTOR.get_active_state(player)
            if not state:
                return []
            dag = NARRATIVE_EXECUTOR.get_dag(state.dag_id)
            if not dag:
                return []
            context = NARRATIVE_EXECUTOR.NarrativeContext(
                flags=state.flags,
                variables=state.variables,
            )
            endings = NARRATIVE_EXECUTOR.get_available_endings(context)
            return [
                {
                    "ending_id": e.id,
                    "name": e.name,
                    "description": e.description,
                    "rewards": e.rewards,
                }
                for e in endings
            ]
        except Exception:
            # TODO: handle exception properly
            return []

    def get_narrative_state(self, player: Entity) -> dict[str, Any] | None:
        """ナラティブ状態をシリアライズして取得"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            state = NARRATIVE_EXECUTOR.get_active_state(player)
            if state:
                return state.to_dict()
        except Exception:
            # TODO: handle exception properly
            pass
        return None

    def load_narrative_state(self, player: Entity, data: dict[str, Any]) -> bool:
        """ナラティブ状態を復元"""
        try:
            from narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.load_state(player, data)
        except Exception:
            # TODO: handle exception properly
            return False
