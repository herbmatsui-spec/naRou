"""
Narrative Executor Module (偏執的クエストシステム / 設計書 Phase 4 Step 15-16)
DAG 実行エンジン：現在ノード管理・選択適用・フラグ更新。
story_choices.yaml / story_endings.yaml 連携（Step 16）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity

from naRou.quest_narrative_dag import (
    NarrativeContext,
    NarrativeDAG,
    NarrativeEdge,
    NarrativeEdgeType,
    NarrativeNode,
    NarrativeNodeType,
    build_dag_from_yaml,
)


@dataclass
class HistoryEntry:
    """ナラティブ履歴エントリ（選択・分岐の詳細記録）"""

    node_id: str                    # ノードID
    node_title: str                 # ノードタイトル
    node_type: str                  # ノードタイプ (START/CHOICE/EVENT/END 等)
    timestamp: str                  # ISO8601形式タイムスタンプ
    # 選択肢の場合のみ
    choice_text: str = ""           # 選択したテキスト
    choice_reason: str = ""         # 分岐理由（条件式や説明）
    # 結果
    immediate_rewards: dict = field(default_factory=dict)      # 即時報酬
    long_term_effects: dict = field(default_factory=dict)      # 長期効果
    flags_set: list[str] = field(default_factory=list)         # 設定されたフラグ
    flags_cleared: list[str] = field(default_factory=list)     # クリアされたフラグ
    # 到達時のコンテキストスナップショット（任意）
    karma_at_choice: int = 0
    faction_rep_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_title": self.node_title,
            "node_type": self.node_type,
            "timestamp": self.timestamp,
            "choice_text": self.choice_text,
            "choice_reason": self.choice_reason,
            "immediate_rewards": self.immediate_rewards,
            "long_term_effects": self.long_term_effects,
            "flags_set": self.flags_set,
            "flags_cleared": self.flags_cleared,
            "karma_at_choice": self.karma_at_choice,
            "faction_rep_snapshot": self.faction_rep_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        return cls(
            node_id=data.get("node_id", ""),
            node_title=data.get("node_title", ""),
            node_type=data.get("node_type", ""),
            timestamp=data.get("timestamp", ""),
            choice_text=data.get("choice_text", ""),
            choice_reason=data.get("choice_reason", ""),
            immediate_rewards=data.get("immediate_rewards", {}),
            long_term_effects=data.get("long_term_effects", {}),
            flags_set=data.get("flags_set", []),
            flags_cleared=data.get("flags_cleared", []),
            karma_at_choice=data.get("karma_at_choice", 0),
            faction_rep_snapshot=data.get("faction_rep_snapshot", {}),
        )


@dataclass
class NarrativeState:
    """ナラティブ実行状態（セーブデータ用）"""

    dag_id: str
    current_node_id: str
    flags: set[str] = field(default_factory=set)
    variables: dict[str, Any] = field(default_factory=dict)
    history: list[HistoryEntry] = field(default_factory=list)  # 通過したノードの詳細履歴
    completed: bool = False
    ending_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "current_node_id": self.current_node_id,
            "flags": list(self.flags),
            "variables": self.variables,
            "history": [h.to_dict() for h in self.history],
            "completed": self.completed,
            "ending_id": self.ending_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NarrativeState:
        # 旧形式互換: history が文字列リストの場合
        history_data = data.get("history", [])
        history: list[HistoryEntry] = []
        for h in history_data:
            if isinstance(h, str):
                # 旧形式: ノードIDのみの文字列
                history.append(HistoryEntry(
                    node_id=h,
                    node_title="",
                    node_type="",
                    timestamp="",
                ))
            elif isinstance(h, dict):
                history.append(HistoryEntry.from_dict(h))

        return cls(
            dag_id=data["dag_id"],
            current_node_id=data["current_node_id"],
            flags=set(data.get("flags", [])),
            variables=data.get("variables", {}),
            history=history,
            completed=data.get("completed", False),
            ending_id=data.get("ending_id"),
        )


@dataclass
class StoryChoiceConsequence:
    """選択肢の結果（story_choices.yaml）"""

    id: str
    description: str = ""
    immediate_effects: list[dict[str, Any]] = field(default_factory=list)
    long_term_effects: list[dict[str, Any]] = field(default_factory=list)
    world_state_changes: dict[str, Any] = field(default_factory=dict)


@dataclass
class StoryEnding:
    """ストーリー エンディング（story_endings.yaml）"""

    id: str
    name: str = ""
    description: str = ""
    unlock_conditions: list[str] = field(default_factory=list)
    ending_scene: str = ""
    rewards: dict[str, Any] = field(default_factory=dict)


class NarrativeExecutor:
    """ナラティブ DAG 実行エンジン"""

    def __init__(
        self,
        data_path: str = "data/quest_narratives.yaml",
        choices_path: str = "data/story_choices.yaml",
        endings_path: str = "data/story_endings.yaml",
    ):
        self.data_path = data_path
        self.choices_path = choices_path
        self.endings_path = endings_path
        self._dags: dict[str, NarrativeDAG] = {}
        self._choices: dict[str, StoryChoiceConsequence] = {}
        self._endings: dict[str, StoryEnding] = {}
        self._active_states: dict[str, NarrativeState] = {}  # player_id -> state
        self.load_all()

    def load_all(self) -> None:
        """全データ読み込み"""
        self.load_dags()
        self.load_choices()
        self.load_endings()

    def load_dags(self) -> None:
        """YAML から全 DAG を読み込み"""
        self._dags = {}
        if not os.path.exists(self.data_path):
            return

        with open(self.data_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for dag_id, dag_data in data.get("narrative_dags", {}).items():
            dag = build_dag_from_yaml(dag_id, dag_data)
            errors = dag.validate()
            if errors:
                for err in errors:
                    print(f"[NarrativeDAG Warning] {err}")
            self._dags[dag_id] = dag

    def load_choices(self) -> None:
        """story_choices.yaml 読み込み"""
        self._choices = {}
        if not os.path.exists(self.choices_path):
            return

        with open(self.choices_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for choice_id, choice_data in data.get("choice_consequences", {}).items():
            self._choices[choice_id] = StoryChoiceConsequence(
                id=choice_id,
                description=choice_data.get("description", ""),
                immediate_effects=choice_data.get("immediate_effects", []),
                long_term_effects=choice_data.get("long_term_effects", []),
                world_state_changes=choice_data.get("world_state_changes", {}),
            )

    def load_endings(self) -> None:
        """story_endings.yaml 読み込み"""
        self._endings = {}
        if not os.path.exists(self.endings_path):
            return

        with open(self.endings_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for ending_id, ending_data in data.get("story_endings", {}).items():
            self._endings[ending_id] = StoryEnding(
                id=ending_id,
                name=ending_data.get("name", ""),
                description=ending_data.get("description", ""),
                unlock_conditions=ending_data.get("unlock_conditions", []),
                ending_scene=ending_data.get("ending_scene", ""),
                rewards=ending_data.get("rewards", {}),
            )

    def get_choice(self, choice_id: str) -> StoryChoiceConsequence | None:
        return self._choices.get(choice_id)

    def get_ending(self, ending_id: str) -> StoryEnding | None:
        return self._endings.get(ending_id)

    def apply_choice_consequence(
        self,
        choice_id: str,
        context: NarrativeContext,
    ) -> list[str]:
        """選択肢の結果を適用（即時効果・長期効果・世界状態変更）"""
        choice = self._choices.get(choice_id)
        if not choice:
            return [f"選択肢結果 {choice_id} が見つかりません"]

        logs = []

        # 即時効果
        for effect in choice.immediate_effects:
            eff_type = effect.get("type")
            value = effect.get("value", 0)
            if eff_type == "gain_gold":
                context.variables["gold"] = context.variables.get("gold", 0) + value
                logs.append(f"ゴールド獲得: +{value}")
            elif eff_type == "gain_karma":
                context.variables["karma"] = context.variables.get("karma", 0) + value
                logs.append(f"カルマ変化: {value:+d}")
            elif eff_type == "gain_exp":
                context.variables["exp"] = context.variables.get("exp", 0) + value
                logs.append(f"経験値獲得: +{value}")
            elif eff_type == "gain_piety":
                context.variables["piety"] = context.variables.get("piety", 0) + value
                logs.append(f"信仰心変化: {value:+d}")
            elif eff_type == "gain_mp_max":
                context.variables["mp_max"] = context.variables.get("mp_max", 0) + value
                logs.append(f"最大MP増加: +{value}")

        # 長期効果
        for effect in choice.long_term_effects:
            eff_type = effect.get("type")
            value = effect.get("value", 0)
            context.variables[f"long_term_{eff_type}"] = value
            logs.append(f"長期効果登録: {eff_type} = {value}")

        # 世界状態変更
        for key, value in choice.world_state_changes.items():
            context.variables[f"world_{key}"] = value
            logs.append(f"世界状態更新: {key} = {value}")

        return logs

    def check_ending_unlock(
        self,
        ending_id: str,
        context: NarrativeContext,
        main_quest_system: Any = None,
    ) -> bool:
        """エンディング解放条件チェック（DSL対応版）"""
        ending = self._endings.get(ending_id)
        if not ending:
            return False

        # 全条件を満たす必要あり（AND）
        for condition_dsl in ending.unlock_conditions:
            if not condition_dsl.strip():
                continue
            try:
                # DSL パース
                from naRou.quest_condition_parser import parse_condition
                from naRou.quest_condition_evaluator import evaluate_condition, EvaluationContext
                
                condition_tree = parse_condition(condition_dsl)
                # NarrativeContext の情報を extra_vars 経由で EvaluationContext に渡す
                extra_vars = dict(context.variables)
                extra_vars["_narrative_flags"] = context.flags
                if main_quest_system:
                    extra_vars["quest_system"] = main_quest_system
                
                eval_context = EvaluationContext(
                    player=context.player,
                    extra_vars=extra_vars,
                )
                if not evaluate_condition(condition_tree, player=eval_context.player, extra_vars=eval_context.extra_vars):
                    return False
            except Exception as e:
                logger.warning("エンディング条件評価エラー (%s): %s", condition_dsl, e)
                # パース/評価失敗時は旧形式として互換チェック
                if not self._check_condition_legacy(condition_dsl, context):
                    return False
        return True

    def _check_condition_legacy(self, condition: str, context: NarrativeContext) -> bool:
        """旧形式条件チェック（互換性維持）"""
        # フラグチェック
        if condition.startswith("has_flag:"):
            flag = condition.split(":", 1)[1]
            return flag in context.flags
        # カルマチェック
        if condition.startswith("karma_good_"):
            threshold = int(condition.split("_")[-1])
            return context.variables.get("karma", 0) >= threshold
        if condition.startswith("karma_evil_"):
            threshold = int(condition.split("_")[-1])
            return context.variables.get("karma", 0) <= -threshold
        # キル数チェック
        if condition.startswith("kill_counts_total_"):
            threshold = int(condition.split("_")[-1])
            return context.variables.get("total_kills", 0) >= threshold
        # フラグ直接指定
        return condition in context.flags

    def grant_ending_rewards(self, ending_id: str, context: NarrativeContext) -> list[str]:
        """エンディング報酬付与"""
        ending = self._endings.get(ending_id)
        if not ending:
            return [f"エンディング {ending_id} が見つかりません"]

        logs = []
        for key, value in ending.rewards.items():
            if key == "title":
                context.variables["title"] = value
                logs.append(f"称号獲得: {value}")
            elif key == "gold":
                context.variables["gold"] = context.variables.get("gold", 0) + value
                logs.append(f"ゴールド獲得: +{value}")
            elif key == "item":
                context.variables.setdefault("items", []).append(value)
                logs.append(f"アイテム獲得: {value}")
            elif key == "ending_scene":
                context.variables["ending_scene"] = value
                logs.append(f"エンディングシーン: {value}")
        return logs

    def get_available_endings(self, context: NarrativeContext) -> list[StoryEnding]:
        """現在解放可能なエンディング一覧"""
        return [e for e in self._endings.values() if self.check_ending_unlock(e.id, context)]

    def get_dag(self, dag_id: str) -> NarrativeDAG | None:
        return self._dags.get(dag_id)

    def start_narrative(
        self,
        dag_id: str,
        player: Entity,
        initial_flags: set[str] | None = None,
        initial_variables: dict[str, Any] | None = None,
    ) -> NarrativeState | None:
        """ナラティブ開始"""
        dag = self._dags.get(dag_id)
        if not dag:
            return None

        start_node = dag.get_start_node()
        if not start_node:
            return None

        # コンテキスト生成
        context = NarrativeContext(
            player=player,
            flags=initial_flags or set(),
            variables={},
        )

        # 開始ノードの自動遷移を適用（state を渡して履歴記録）
        temp_state = NarrativeState(
            dag_id=dag_id,
            current_node_id=start_node.node_id,
            flags=context.flags,
            variables=context.variables,
        )
        current_node_id = self._apply_auto_transitions(dag, start_node.node_id, context, temp_state)

        state = NarrativeState(
            dag_id=dag_id,
            current_node_id=current_node_id,
            flags=context.flags,
            variables=context.variables,
            history=temp_state.history,
        )

        # プレイヤーIDで管理（簡易版：名前使用）
        player_id = getattr(player, "name", "player")
        self._active_states[player_id] = state

        # フラグ・変数適用
        self._apply_node_effects(dag.get_node(current_node_id), context)

        return state

    def get_active_state(self, player: Entity) -> NarrativeState | None:
        player_id = getattr(player, "name", "player")
        return self._active_states.get(player_id)

    def get_current_node(self, player: Entity) -> NarrativeNode | None:
        state = self.get_active_state(player)
        if not state:
            return None
        dag = self._dags.get(state.dag_id)
        if not dag:
            return None
        return dag.get_node(state.current_node_id)

    def get_available_choices(self, player: Entity) -> list[NarrativeEdge]:
        """現在のノードで選択可能なエッジ一覧取得"""
        state = self.get_active_state(player)
        if not state or state.completed:
            return []

        dag = self._dags.get(state.dag_id)
        if not dag:
            return []

        node = dag.get_node(state.current_node_id)
        if not node:
            return []

        context = NarrativeContext(
            flags=state.flags,
            variables=state.variables,
        )

        # 手動選択タイプのみ返す（CHOICE タイプ）
        available = []
        for edge in node.get_available_edges(context):
            if edge.edge_type == NarrativeEdgeType.CHOICE:
                available.append(edge)

        # 重み付きランダム順（決定的な順序が必要なら weight でソート）
        available.sort(key=lambda e: (-e.weight, e.edge_id))
        return available

    def make_choice(self, player: Entity, edge_id: str, engine: Any = None) -> list[str]:
        """選択肢を選択して遷移実行。ログメッセージリストを返す。"""
        state = self.get_active_state(player)
        if not state or state.completed:
            return ["ナラティブが進行中ではありません"]

        dag = self._dags.get(state.dag_id)
        if not dag:
            return ["DAG が見つかりません"]

        node = dag.get_node(state.current_node_id)
        if not node:
            return ["現在ノードが無効です"]

        # エッジ検索
        edge = None
        for e in node.outgoing_edges:
            if e.edge_id == edge_id:
                edge = e
                break

        if not edge:
            return ["指定された選択肢が見つかりません"]

        # コンテキスト再構築
        context = NarrativeContext(
            flags=state.flags,
            variables=state.variables,
        )

        # 遷移可能かチェック
        if not edge.is_available(context):
            return ["現在その選択肢は選べません"]

        # 選択肢の詳細情報を取得（履歴記録用）
        choice_text = edge.choice_text
        choice_reason = edge.condition_dsl if edge.condition_dsl else ""

        # 選択肢タイプの場合、選択肢の結果を適用
        logs = []
        immediate_rewards = {}
        long_term_effects = {}
        flags_before = set(context.flags)
        variables_before = dict(context.variables)
        
        if edge.edge_type == NarrativeEdgeType.CHOICE:
            choice_logs = self.apply_choice_consequence(edge.edge_id, context)
            logs.extend(choice_logs)
            # 報酬・効果を履歴用に抽出
            choice = self._choices.get(edge.edge_id)
            if choice:
                for eff in choice.immediate_effects:
                    immediate_rewards[eff.get("type", "")] = eff.get("value", 0)
                for eff in choice.long_term_effects:
                    long_term_effects[eff.get("type", "")] = eff.get("value", 0)
                immediate_rewards.update(choice.world_state_changes)

        # 遷移実行
        transition_logs = self._execute_transition(dag, edge, context, state, engine)
        logs.extend(transition_logs)

        # 履歴エントリ作成（遷移後の状態で）
        final_node = dag.get_node(state.current_node_id)
        flags_after = context.flags
        flags_set = list(flags_after - flags_before)
        flags_cleared = list(flags_before - flags_after)
        
        # カルマ・派閥評価スナップショット
        karma_at = context.variables.get("karma", 0)
        faction_rep_snapshot = {}
        for key, value in context.variables.items():
            if key.startswith("faction_rep.") or key.startswith("world_faction_rep."):
                faction_rep_snapshot[key] = value

        history_entry = HistoryEntry(
            node_id=state.current_node_id,
            node_title=final_node.title if final_node else "",
            node_type=final_node.node_type.name if final_node else "",
            timestamp=datetime.now().isoformat(),
            choice_text=choice_text,
            choice_reason=choice_reason,
            immediate_rewards=immediate_rewards,
            long_term_effects=long_term_effects,
            flags_set=flags_set,
            flags_cleared=flags_cleared,
            karma_at_choice=karma_at,
            faction_rep_snapshot=faction_rep_snapshot,
        )
        state.history.append(history_entry)

        return logs

    def _execute_transition(
        self,
        dag: NarrativeDAG,
        edge: NarrativeEdge,
        context: NarrativeContext,
        state: NarrativeState,
        engine: Any = None,
    ) -> list[str]:
        """エッジ遷移実行（履歴記録は呼び出し元 make_choice で行う）"""
        logs = []

        # エッジの効果適用
        for key, value in edge.effects.items():
            context.variables[key] = value
            logs.append(f"効果適用: {key} = {value}")

        # ターゲットノードへ移動
        target_node = dag.get_node(edge.target_node_id)
        if not target_node:
            return ["遷移先ノードが存在しません"]

        # 自動遷移チェイン適用
        final_node_id = self._apply_auto_transitions(dag, edge.target_node_id, context, state)

        # フラグ・変数更新（_apply_auto_transitions 内で更新済みだが念のため）
        state.current_node_id = final_node_id
        state.flags = context.flags
        state.variables = context.variables

        # 到達ノードの効果適用
        final_node = dag.get_node(final_node_id)
        if final_node:
            self._apply_node_effects(final_node, context)

        # 完了判定
        if final_node.node_type == NarrativeNodeType.END:
            state.completed = True
            state.ending_id = final_node.node_id
            logs.append(f"★ ナラティブ「{dag.dag_id}」が完了しました: {final_node.title}")

            # エンディング解放チェック・報酬付与
            mqs = getattr(engine, "main_quest_system", None)
            if self.check_ending_unlock(final_node.node_id, context, mqs):
                ending_logs = self.grant_ending_rewards(final_node.node_id, context)
                logs.extend(ending_logs)

        return logs

    def _apply_auto_transitions(
        self,
        dag: NarrativeDAG,
        start_node_id: str,
        context: NarrativeContext,
        state: NarrativeState | None = None,
    ) -> str:
        """自動遷移（AUTO/CONDITION_TRUE 等）を連鎖適用"""
        current_id = start_node_id
        visited = set()  # 無限ループ防止

        while True:
            if current_id in visited:
                break  # ループ検出
            visited.add(current_id)

            node = dag.get_node(current_id)
            if not node:
                break

            # ノードの効果適用
            self._apply_node_effects(node, context)

            # 自動遷移可能なエッジを探す
            auto_edge = None
            for edge in node.outgoing_edges:
                if edge.edge_type in (
                    NarrativeEdgeType.AUTO,
                    NarrativeEdgeType.CONDITION_TRUE,
                ) and edge.is_available(context):
                    auto_edge = edge
                    break

            if not auto_edge:
                break  # 自動遷移なし = ここで停止

            # 遷移実行
            for key, value in auto_edge.effects.items():
                context.variables[key] = value

            # 履歴記録（state が渡されている場合）
            if state is not None:
                prev_id = state.current_node_id
                state.current_node_id = auto_edge.target_node_id
                state.flags = context.flags
                state.variables = context.variables
                
                target_node = dag.get_node(auto_edge.target_node_id)
                history_entry = HistoryEntry(
                    node_id=auto_edge.target_node_id,
                    node_title=target_node.title if target_node else "",
                    node_type=target_node.node_type.name if target_node else "",
                    timestamp=datetime.now().isoformat(),
                    choice_text="",
                    choice_reason=f"Auto transition from {prev_id} via {auto_edge.edge_id}",
                    immediate_rewards=dict(auto_edge.effects),
                    flags_set=[],
                    flags_cleared=[],
                    karma_at_choice=context.variables.get("karma", 0),
                )
                state.history.append(history_entry)

            current_id = auto_edge.target_node_id

            # 終了ノードなら停止
            target_node = dag.get_node(current_id)
            if target_node and target_node.node_type == NarrativeNodeType.END:
                break

        return current_id

    def _apply_node_effects(self, node: NarrativeNode | None, context: NarrativeContext) -> None:
        """ノードのフラグ・変数・報酬効果を適用"""
        if not node:
            return

        for flag in node.set_flags:
            context.set_flag(flag)

        for flag in node.clear_flags:
            context.clear_flag(flag)

        for key, value in node.rewards.items():
            context.variables[key] = value

    def save_state(self, player: Entity) -> dict[str, Any] | None:
        """状態をシリアライズ"""
        state = self.get_active_state(player)
        if not state:
            return None
        return state.to_dict()

    def load_state(self, player: Entity, data: dict[str, Any]) -> bool:
        """状態をデシリアライズ"""
        try:
            state = NarrativeState.from_dict(data)
            dag = self._dags.get(state.dag_id)
            if not dag:
                return False

            player_id = getattr(player, "name", "player")
            self._active_states[player_id] = state
            return True
        except Exception:
            logger.exception("Unhandled exception")
            # If deserialization fails, indicate failure
            return False

    def force_transition(self, player: Entity, target_node_id: str) -> list[str]:
        """強制遷移（デバッグ・イベント連携用）"""
        state = self.get_active_state(player)
        if not state:
            return ["アクティブなナラティブがありません"]

        dag = self._dags.get(state.dag_id)
        if not dag:
            return ["DAG が見つかりません"]

        target_node = dag.get_node(target_node_id)
        if not target_node:
            return ["対象ノードが存在しません"]

        context = NarrativeContext(
            flags=state.flags,
            variables=state.variables,
        )

        # 強制遷移実行
        prev_id = state.current_node_id
        final_id = self._apply_auto_transitions(dag, target_node_id, context, state)
        state.current_node_id = final_id
        state.flags = context.flags
        state.variables = context.variables
        # 履歴は _apply_auto_transitions 内で記録済み

        return [f"強制遷移: {target_node_id} -> {final_id}"]


# グローバルシングルトン
NARRATIVE_EXECUTOR = NarrativeExecutor()


__all__ = [
    "NARRATIVE_EXECUTOR",
    "NarrativeExecutor",
    "NarrativeState",
]
