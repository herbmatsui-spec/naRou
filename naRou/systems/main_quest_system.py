"""
Main Quest System Module
Handles the progression of the primary story line, quest tracking, and reward distribution of rewards.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

import yaml
from naRou.relationship_system import RelationshipManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from game import Engine
    from naRou.quest_condition_ast import ConditionNode
    from naRou.quest_condition_evaluator import EvaluationContext


# 遅延インポートで循環参照回避
def _get_condition_parser():
    from naRou.quest_condition_parser import parse_condition_from_yaml

    return parse_condition_from_yaml


def _get_evaluator():
    from naRou.quest_condition_evaluator import EvaluationContext, evaluate_condition

    return evaluate_condition, EvaluationContext


class QuestStatus(Enum):
    LOCKED = auto()  # 解放前
    AVAILABLE = auto()  # 受注可能
    ACTIVE = auto()  # 進行中
    COMPLETED = auto()  # 完了
    FAILED = auto()  # 失敗


@dataclass
class QuestObjective:
    """クエストの達成条件 (CQCT完全移行版)"""

    objective_id: str
    description: str
    is_completed: bool = False
    # CQCTフィールド
    condition_tree: ConditionNode | None = None  # 複合条件AST
    condition_dsl: str = ""  # DSL文字列（YAML保存用・必須）
    auto_evaluate: bool = True  # イベント駆動で自動評価するか
    # ナラティブDAG拡張 (Phase 4 Step 17)
    narrative_dag_id: str = ""  # 関連ナラティブDAG ID
    narrative_started: bool = False  # ナラティブ開始済みフラグ
    # 追加: NPC関係ゲート
    relationship_gate: list[dict] = field(default_factory=list)
    # 追加: 進行ステップごとの関係変化
    relationship_effect_per_step: dict[str, int] = field(default_factory=dict)

    def evaluate(self, context: EvaluationContext) -> bool:
        """CQCT評価：条件ツリーを必須で評価"""
        if not self.condition_tree:
            raise RuntimeError(
                f"QuestObjective '{self.objective_id}' に condition_tree が構築されていません。"
                f"condition_dsl を設定し build_condition_tree() を呼んでください。"
            )
        self.is_completed = self.condition_tree.evaluate(context)
        return self.is_completed

    def apply_relationship_effects(self, player, relationship_manager: RelationshipManager) -> list[str]:
        """進行ステップごとの関係変化を適用"""
        logs = []
        for npc_id, delta in self.relationship_effect_per_step.items():
            try:
                trust, mood = relationship_manager.update_relationship(
                    player, npc_id, delta_trust=delta
                )
                logs.append(f"関係変化: {npc_id} trust={trust} mood={mood}")
            except Exception as e:
                logs.append(f"関係変化エラー ({npc_id}): {e}")
        return logs

    def to_dict(self) -> dict[str, Any]:
        """シリアライズ"""
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "is_completed": self.is_completed,
            "condition_dsl": self.condition_dsl,
            "auto_evaluate": self.auto_evaluate,
            "narrative_dag_id": self.narrative_dag_id,
            "narrative_started": self.narrative_started,
            "relationship_gate": self.relationship_gate,
            "relationship_effect_per_step": self.relationship_effect_per_step,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestObjective:
        """デシリアライズ（condition_treeは別途構築）"""
        obj = cls(
            objective_id=data.get("objective_id", ""),
            description=data.get("description", ""),
            is_completed=data.get("is_completed", False),
            condition_dsl=data.get("condition_dsl", ""),
            auto_evaluate=data.get("auto_evaluate", True),
            narrative_dag_id=data.get("narrative_dag_id", ""),
            narrative_started=data.get("narrative_started", False),
            relationship_gate=data.get("relationship_gate", []),
            relationship_effect_per_step=data.get("relationship_effect_per_step", {}),
        )
        return obj

    def build_condition_tree(self) -> None:
        """DSL文字列から条件ツリーを構築（必須）"""
        if not self.condition_dsl:
            raise ValueError(
                f"QuestObjective '{self.objective_id}' に condition_dsl が設定されていません。"
            )
        if not self.condition_tree:
            parser = _get_condition_parser()
            self.condition_tree = parser(self.condition_dsl)


@dataclass
class MainQuest:
    """メインクエスト定義 (非線形・並行進行対応版)"""

    quest_id: str
    title: str
    description: str
    required_phase: str = ""  # WorldPhaseの文字列（フォールバック用）
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: dict[str, Any] = field(default_factory=dict)
    # 非線形化拡張
    prerequisite_quest_ids: list[str] = field(default_factory=list)  # 解放前提クエストID群
    is_parallel: bool = False  # 並行進行可能フラグ
    next_quest_ids: list[str] = field(default_factory=list)  # 次クエストID群（複数可）
    next_quest_id: str | None = None  # 後方互換用（単一）
    phase_unlock_condition: str = ""  # フェーズ移行条件DSL
    status: QuestStatus = QuestStatus.LOCKED
    # CQCT拡張: クエスト全体の解放条件
    unlock_condition: ConditionNode | None = None
    unlock_dsl: str = ""
    # ナラティブDAG拡張 (Phase 4 Step 17)
    narrative_dag_id: str = ""  # クエスト全体のナラティブDAG
    # 失敗条件・タイムアウト
    failure_conditions: list[str] = field(default_factory=list)
    timeout_turns: int = 0
    on_failure: dict[str, Any] = field(default_factory=dict)

    def check_unlock(self, context: EvaluationContext) -> bool:
        """解放条件チェック（優先順位: unlock_condition > prerequisite_quest_ids > required_phase）"""
        # 1. CQCT解放条件
        if self.unlock_condition:
            return self.unlock_condition.evaluate(context)
        
        # 2. 前提クエスト完了チェック
        if self.prerequisite_quest_ids:
            return self._check_prerequisites(context)
        
        # 3. フォールバック: required_phaseのみ
        if self.required_phase:
            from naRou.world_state_system import REGISTRY, WorldStateManager
            ws_manager = WorldStateManager(REGISTRY)
            return ws_manager.get_phase().name == self.required_phase
        
        return False

    def _check_prerequisites(self, context: EvaluationContext) -> bool:
        """前提クエスト全完了チェック"""
        # EvaluationContext からクエスト状態を参照
        for prereq_id in self.prerequisite_quest_ids:
            # quest.completed.{quest_id} キーで判定
            completed = context.resolve(f"quest.completed.{prereq_id}")
            if not completed:
                return False
        return True

    def is_completed(self) -> bool:
        return all(obj.is_completed for obj in self.objectives)

    def get_next_quest_ids(self) -> list[str]:
        """次クエストIDリスト取得（互換性込み）"""
        if self.next_quest_ids:
            return self.next_quest_ids
        if self.next_quest_id:
            return [self.next_quest_id]
        return []

    def to_dict(self) -> dict[str, Any]:
        """シリアライズ"""
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "required_phase": self.required_phase,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "rewards": self.rewards,
            "prerequisite_quest_ids": self.prerequisite_quest_ids,
            "is_parallel": self.is_parallel,
            "next_quest_ids": self.next_quest_ids,
            "next_quest_id": self.next_quest_id,
            "phase_unlock_condition": self.phase_unlock_condition,
            "status": self.status.name,
            "unlock_dsl": self.unlock_dsl,
            "narrative_dag_id": self.narrative_dag_id,
            "failure_conditions": self.failure_conditions,
            "timeout_turns": self.timeout_turns,
            "on_failure": self.on_failure,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MainQuest:
        """デシリアライズ"""
        objectives = [QuestObjective.from_dict(obj) for obj in data.get("objectives", [])]
        quest = cls(
            quest_id=data.get("quest_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            required_phase=data.get("required_phase", ""),
            objectives=objectives,
            rewards=data.get("rewards", {}),
            prerequisite_quest_ids=data.get("prerequisite_quest_ids", []),
            is_parallel=data.get("is_parallel", False),
            next_quest_ids=data.get("next_quest_ids", []),
            next_quest_id=data.get("next_quest_id"),
            phase_unlock_condition=data.get("phase_unlock_condition", ""),
            unlock_dsl=data.get("unlock_dsl", ""),
            narrative_dag_id=data.get("narrative_dag_id", ""),
            failure_conditions=data.get("failure_conditions", []),
            timeout_turns=data.get("timeout_turns", 0),
            on_failure=data.get("on_failure", {}),
        )
        quest.status = QuestStatus[data.get("status", "LOCKED")]
        return quest

    def build_condition_trees(self) -> None:
        """全ての目的と解放条件のツリーを構築"""
        for obj in self.objectives:
            obj.build_condition_tree()
        if self.unlock_dsl and not self.unlock_condition:
            parser = _get_condition_parser()
            self.unlock_condition = parser(self.unlock_dsl)
        # phase_unlock_condition は MainQuestSystem 側で評価


class MainQuestSystem:
    """メインクエスト管理エンジン"""

    def __init__(self, data_path: str = "data/main_quests.yaml"):
        self.data_path = data_path
        self.quests: dict[str, MainQuest] = {}
        self.active_quest_ids: set[str] = set()  # 複数並行進行対応
        self.quest_timeouts: dict[str, int] = {}
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
                objectives = [QuestObjective(**obj) for obj in q_data.get("objectives", [])]
                quest = MainQuest(
                    quest_id=q_data["quest_id"],
                    title=q_data["title"],
                    description=q_data["description"],
                    required_phase=q_data.get("required_phase", ""),
                    objectives=objectives,
                    rewards=q_data.get("rewards", {}),
                    # 非線形化フィールド
                    prerequisite_quest_ids=q_data.get("prerequisite_quest_ids", []),
                    is_parallel=q_data.get("is_parallel", False),
                    next_quest_ids=q_data.get("next_quest_ids", []),
                    next_quest_id=q_data.get("next_quest_id"),
                    phase_unlock_condition=q_data.get("phase_unlock_condition", ""),
                    unlock_dsl=q_data.get("unlock_condition", ""),
                    narrative_dag_id=q_data.get("narrative_dag_id", ""),
                )
                self.quests[quest.quest_id] = quest

        # 条件ツリーの遅延構築
        for quest in self.quests.values():
            quest.build_condition_trees()

    def _create_default_quests(self) -> None:
        """初期テスト用クエスト（非線形版）"""
        q1 = MainQuest(
            quest_id="prologue_01",
            title="運命の始まり",
            description="村の長から古文書を受け取り、世界の異変について知る。",
            required_phase="BEGINNING",
            prerequisite_quest_ids=[],
            is_parallel=False,
            objectives=[
                QuestObjective(
                    objective_id="talk_elder",
                    description="村の長に話しかける",
                    condition_dsl="(has player.visited_locations.village_elder)",
                    auto_evaluate=True,
                    narrative_dag_id="prologue_branching",
                )
            ],
            rewards={"gold": 100, "world_phase": "AWAKENING"},
            next_quest_ids=["awakening_01"],
            phase_unlock_condition="(truthy quest.completed.prologue_01)",
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
        イベントに基づいてクエスト進行を更新する（CQCT完全移行版・並行進行対応）。
        event_type, target_id, amount は互換性のため残すが、評価は condition_tree のみで行う。
        """
        logs = []
        
        # アクティブなクエストがない場合、条件を満たすものを自動的にアクティブにする
        if not self.active_quest_ids:
            self._try_activate_available_quests(player, engine)
            if not self.active_quest_ids:
                return logs

        # コンテキスト作成（全クエスト共通）
        _evaluator_func, EvaluationContext = _get_evaluator()
        context = EvaluationContext(player, engine)

        # 全アクティブクエストを評価
        completed_quest_ids = []
        for quest_id in list(self.active_quest_ids):
            quest = self.quests.get(quest_id)
            if not quest or quest.status != QuestStatus.ACTIVE:
                continue

            # 全ての目的を CQCT で評価
            for obj in quest.objectives:
                if obj.auto_evaluate:
                    try:
                        was_completed = obj.is_completed
                        if obj.evaluate(context):
                            if not was_completed:
                                logs.append(f"【クエスト進行】{quest.title}: {obj.description} (達成！)")
                    except RuntimeError as e:
                        logger.error("Objective evaluation failed: %s", e)
                        logs.append(f"【エラー】{quest.title}: {obj.description} - {e}")

            # 進行ステップごとの関係変化適用
            rel_mgr = RelationshipManager()
            for obj in quest.objectives:
                effect_logs = obj.apply_relationship_effects(player, rel_mgr)
                logs.extend(effect_logs)

            # クエスト完了判定
            if all(obj.is_completed for obj in quest.objectives):
                completed_quest_ids.append(quest_id)
                logs.append(f"★メインクエスト【{quest.title}】を完了した！")

        # 完了したクエストを処理
        for quest_id in completed_quest_ids:
            quest = self.quests[quest_id]
            self._complete_quest(player, quest, engine)

        # 失敗したクエストを処理
        failed_quest_ids = []
        for quest_id in list(self.active_quest_ids):
            quest = self.quests.get(quest_id)
            if not quest:
                continue
            # タイムアウト処理
            if quest.timeout_turns:
                remaining = self.quest_timeouts.get(quest_id, quest.timeout_turns) - 1
                self.quest_timeouts[quest_id] = remaining
                if remaining <= 0:
                    failed_quest_ids.append(quest_id)
                    logs.append(f"【クエスト失敗】{quest.title}: タイムアウト")
                    continue
            # 条件失敗処理
            failure_conds = getattr(quest, "failure_conditions", [])
            if failure_conds:
                if any(_evaluator_func(cond, context) for cond in failure_conds):
                    failed_quest_ids.append(quest_id)
                    logs.append(f"【クエスト失敗】{quest.title}: 条件不成立")
        for quest_id in failed_quest_ids:
            quest = self.quests[quest_id]
            self._fail_quest(player, quest, engine, logs)

        return logs

    def _try_activate_available_quests(self, player: Entity, engine: Engine | None) -> None:
        """条件を満たす全クエストをアクティブにする（並行進行対応）"""
        from naRou.world_state_system import REGISTRY, WorldStateManager

        ws_manager = WorldStateManager(REGISTRY)

        # コンテキスト作成
        _evaluator_func, EvaluationContext = _get_evaluator()
        context = EvaluationContext(player, engine)
        context.extra_vars["quest_system"] = self

        for q_id, q in self.quests.items():
            if q.status in (QuestStatus.LOCKED, QuestStatus.AVAILABLE) and q.check_unlock(context):
                q.status = QuestStatus.ACTIVE
                self.active_quest_ids.add(q_id)
                if q.timeout_turns:
                    self.quest_timeouts[q_id] = q.timeout_turns

    def _complete_quest(self, player: Entity, quest: MainQuest, engine: Engine | None) -> None:
        """クエスト完了処理と報酬付与"""
        quest.status = QuestStatus.COMPLETED
        self.active_quest_ids.discard(quest.quest_id)

        # 報酬付与
        rewards = quest.rewards
        if "gold" in rewards:
            # SurvivalSystem経由でゴールド追加（実際の実装に合わせて調整）
            if hasattr(engine, "survival_system"):
                engine.survival_system.gold += rewards["gold"]

        # ワールドフェーズ移行判定
        self._check_and_apply_phase_unlock(quest, engine)

        # 次のクエストを準備
        for next_qid in quest.get_next_quest_ids():
            if next_qid in self.quests:
                next_quest = self.quests[next_qid]
                if next_quest.status == QuestStatus.LOCKED:
                    next_quest.status = QuestStatus.AVAILABLE

        # 条件を満たすクエストを自動アクティブ化
        self._try_activate_available_quests(player, engine)

        # クエスト完了時にナラティブDAGがある場合は自動開始
        if quest.narrative_dag_id and engine:
            self._start_quest_narrative(quest.narrative_dag_id, player, engine)

    def _check_and_apply_phase_unlock(self, quest: MainQuest, engine: Engine | None) -> None:
        """フェーズ移行条件チェックと適用"""
        if not engine or not quest.phase_unlock_condition:
            # フォールバック: 従来の rewards.world_phase
            if "world_phase" in quest.rewards:
                self._apply_world_phase(quest.rewards["world_phase"], engine)
            return

        # DSL条件評価
        try:
            _evaluator_func, EvaluationContext = _get_evaluator()
            context = EvaluationContext(player=None, engine=engine)
            # MainQuestSystem インスタンスをコンテキストに追加してクエスト状態参照可能にする
            context.extra_vars["quest_system"] = self
            
            parser = _get_condition_parser()
            condition_tree = parser(quest.phase_unlock_condition)
            if condition_tree.evaluate(context):
                # 条件を満たす場合、rewards.world_phase があれば適用
                if "world_phase" in quest.rewards:
                    self._apply_world_phase(quest.rewards["world_phase"], engine)
        except Exception as e:
            logger.error("Phase unlock condition evaluation failed: %s", e)

    def _apply_world_phase(self, phase_name: str, engine: Engine) -> None:
        """ワールドフェーズ適用"""
        from naRou.world_state_system import REGISTRY, WorldStateManager, WorldPhase
        ws_manager = WorldStateManager(REGISTRY)
        try:
            ws_manager.set_phase(WorldPhase[phase_name], engine)
        except KeyError:
            pass

    def _fail_quest(self, player: Entity, quest: MainQuest, engine: Engine | None, logs: list[str]) -> None:
        """クエスト失敗処理とペナルティ適用"""
        quest.status = QuestStatus.FAILED
        self.active_quest_ids.discard(quest.quest_id)
        # ペナルティ適用
        on_failure = getattr(quest, "on_failure", {})
        penalty = on_failure.get("penalty", {})
        if penalty and engine and hasattr(engine, "survival_system"):
            gold = penalty.get("gold")
            if gold:
                engine.survival_system.gold += gold
        # 代替クエスト解放
        alt_id = on_failure.get("alternative_quest_id")
        if alt_id and alt_id in self.quests:
            alt = self.quests[alt_id]
            if alt.status == QuestStatus.LOCKED:
                alt.status = QuestStatus.AVAILABLE
        # ナラティブ分岐開始
        branch = on_failure.get("narrative_branch")
        if branch and engine:
            self._start_quest_narrative(branch, player, engine)
        logs.append(f"【クエスト失敗】{quest.title} が失敗処理済み")

    def _start_quest_narrative(self, dag_id: str, player: Entity, engine: Engine) -> list[str]:
        """クエスト関連ナラティブを開始"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            state = NARRATIVE_EXECUTOR.start_narrative(dag_id, player)
            if state:
                return [f"【ナラティブ開始】{dag_id}"]
        except Exception as e:
            return [f"ナラティブ開始エラー: {e}"]
        return []

    def make_narrative_choice(self, player: Entity, edge_id: str) -> list[str]:
        """ナラティブ選択肢を実行"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.make_choice(player, edge_id)
        except Exception as e:
            return [f"ナラティブ選択エラー: {e}"]

    def get_active_narrative_node(self, player: Entity):
        """現在のアクティブなナラティブノードを取得"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.get_current_node(player)
        except Exception as e:
            logger.warning("Failed to get active narrative node: %s", e)
            return None

    def get_narrative_choices(self, player: Entity) -> list[dict[str, Any]]:
        """現在のナラティブで選択可能な選択肢一覧を取得"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            edges = NARRATIVE_EXECUTOR.get_available_choices(player)
            return [
                {
                    "edge_id": e.edge_id,
                    "choice_text": e.choice_text,
                    "edge_type": e.edge_type.name,
                }
                for e in edges
            ]
        except Exception as e:
            logger.warning("Failed to get narrative choices: %s", e)
            return []

    def get_available_endings(self, player: Entity) -> list[dict[str, Any]]:
        """解放可能なエンディング一覧を取得"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

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
        except Exception as e:
            logger.warning("Failed to get available endings: %s", e)
            return []

    def get_narrative_state(self, player: Entity) -> dict[str, Any] | None:
        """ナラティブ状態をシリアライズして取得"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            state = NARRATIVE_EXECUTOR.get_active_state(player)
            if state:
                return state.to_dict()
        except Exception as e:
            logger.warning("Failed to get narrative state: %s", e)
        return None

    def load_narrative_state(self, player: Entity, data: dict[str, Any]) -> bool:
        """ナラティブ状態を復元"""
        try:
            from naRou.narrative_executor import NARRATIVE_EXECUTOR

            return NARRATIVE_EXECUTOR.load_state(player, data)
        except Exception as e:
            logger.warning("Failed to load narrative state: %s", e)
            return False
