"""
Quest Narrative DAG Module (偏執的クエストシステム / 設計書 Phase 4 Step 13)
ナラティブ分岐 DAG: ノード/エッジ定義と DAG 検証。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entity import Entity


class NarrativeNodeType(Enum):
    """ナラティブノードの種類"""

    START = auto()  # 開始ノード
    CHOICE = auto()  # 選択肢ノード
    EVENT = auto()  # イベントノード（自動進行）
    CONDITION = auto()  # 条件分岐ノード
    END = auto()  # 終了ノード（エンディング）
    MERGE = auto()  # 分岐合流ノード


class NarrativeEdgeType(Enum):
    """エッジの種類"""

    CHOICE = auto()  # プレイヤー選択による遷移
    AUTO = auto()  # 自動遷移（条件満たし等）
    CONDITION_TRUE = auto()  # 条件真
    CONDITION_FALSE = auto()  # 条件偽


@dataclass
class NarrativeEdge:
    """ナラティブエッジ（分岐）"""

    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: NarrativeEdgeType = NarrativeEdgeType.CHOICE
    # 選択肢表示用
    choice_text: str = ""
    # 条件遷移用（CQCT 連携）
    condition_dsl: str = ""
    # 遷移時の副作用
    effects: dict[str, Any] = field(default_factory=dict)
    # 必要フラグ（設定されていれば自動遷移）
    required_flags: list[str] = field(default_factory=list)
    # 禁止フラグ（設定されていれば遷移不可）
    forbidden_flags: list[str] = field(default_factory=list)
    # 重み（ランダム選択用）
    weight: float = 1.0
    # 隠し選択肢フラグ
    hidden: bool = False

    def is_available(self, context: NarrativeContext) -> bool:
        """遷移可能か判定"""
        # 必要フラグチェック
        for flag in self.required_flags:
            if not context.has_flag(flag):
                return False
        # 禁止フラグチェック
        for flag in self.forbidden_flags:
            if context.has_flag(flag):
                return False
        # 条件 DSL チェック
        if self.condition_dsl:
            from quest_condition_evaluator import evaluate
            from quest_condition_parser import parse_condition

            try:
                node = parse_condition(self.condition_dsl)
                return evaluate(node, context)
            except Exception:
                return False
        return True


@dataclass
class NarrativeNode:
    """ナラティブノード"""

    node_id: str
    node_type: NarrativeNodeType = NarrativeNodeType.EVENT
    # 表示テキスト
    title: str = ""
    description: str = ""
    # このノードで実行されるアクション
    actions: list[dict[str, Any]] = field(default_factory=list)
    # 報酬
    rewards: dict[str, Any] = field(default_factory=dict)
    # 出力エッジ
    outgoing_edges: list[NarrativeEdge] = field(default_factory=list)
    # 入力エッジ（逆参照用）
    incoming_edges: list[str] = field(default_factory=list)
    # フラグ操作
    set_flags: list[str] = field(default_factory=list)
    clear_flags: list[str] = field(default_factory=list)
    # メタデータ
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_edge(self, edge: NarrativeEdge) -> None:
        """エッジ追加（双方向リンク）"""
        self.outgoing_edges.append(edge)

    def get_available_edges(self, context: NarrativeContext) -> list[NarrativeEdge]:
        """現在のコンテキストで利用可能なエッジを取得"""
        return [e for e in self.outgoing_edges if e.is_available(context)]


class NarrativeContext:
    """ナラティブ実行コンテキスト"""

    def __init__(
        self,
        player: Entity | None = None,
        flags: set[str] | None = None,
        variables: dict[str, Any] | None = None,
    ):
        self.player = player
        self.flags = flags or set()
        self.variables = variables or {}

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def set_flag(self, flag: str) -> None:
        self.flags.add(flag)

    def clear_flag(self, flag: str) -> None:
        self.flags.discard(flag)

    def get_var(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_var(self, key: str, value: Any) -> None:
        self.variables[key] = value


class NarrativeDAG:
    """ナラティブ DAG 全体管理"""

    def __init__(self, dag_id: str):
        self.dag_id = dag_id
        self._nodes: dict[str, NarrativeNode] = {}
        self._start_node_id: str | None = None
        self._end_node_ids: set[str] = set()

    def add_node(self, node: NarrativeNode) -> None:
        """ノード追加"""
        self._nodes[node.node_id] = node
        if node.node_type == NarrativeNodeType.START:
            self._start_node_id = node.node_id
        if node.node_type == NarrativeNodeType.END:
            self._end_node_ids.add(node.node_id)

    def get_node(self, node_id: str) -> NarrativeNode | None:
        return self._nodes.get(node_id)

    def get_start_node(self) -> NarrativeNode | None:
        if self._start_node_id:
            return self._nodes.get(self._start_node_id)
        return None

    def get_end_nodes(self) -> list[NarrativeNode]:
        return [self._nodes[nid] for nid in self._end_node_ids if nid in self._nodes]

    def validate(self) -> list[str]:
        """DAG 検証（サイクル検出、到達不能ノード検出等）"""
        errors = []

        # 開始ノード存在チェック
        if not self._start_node_id:
            errors.append(f"DAG {self.dag_id}: 開始ノードが定義されていません")
        elif self._start_node_id not in self._nodes:
            errors.append(
                f"DAG {self.dag_id}: 開始ノード {self._start_node_id} が存在しません"
            )

        # 終了ノード存在チェック
        if not self._end_node_ids:
            errors.append(f"DAG {self.dag_id}: 終了ノードが定義されていません")

        # エッジの参照先存在チェック
        for node in self._nodes.values():
            for edge in node.outgoing_edges:
                if edge.target_node_id not in self._nodes:
                    errors.append(
                        f"DAG {self.dag_id}: エッジ {edge.edge_id} のターゲット {edge.target_node_id} が存在しません"
                    )

        # サイクル検出（DFS）
        visited = set()
        rec_stack = set()

        def dfs(nid: str) -> bool:
            if nid in rec_stack:
                return True  # サイクル検出
            if nid in visited:
                return False
            visited.add(nid)
            rec_stack.add(nid)
            node = self._nodes.get(nid)
            if node:
                for edge in node.outgoing_edges:
                    if dfs(edge.target_node_id):
                        return True
            rec_stack.remove(nid)
            return False

        if self._start_node_id and dfs(self._start_node_id):
            errors.append(f"DAG {self.dag_id}: サイクルが検出されました")

        # 到達不能ノード検出
        reachable = set()

        def mark_reachable(nid: str) -> None:
            if nid in reachable:
                return
            reachable.add(nid)
            node = self._nodes.get(nid)
            if node:
                for edge in node.outgoing_edges:
                    mark_reachable(edge.target_node_id)

        if self._start_node_id:
            mark_reachable(self._start_node_id)

        for nid in self._nodes:
            if nid not in reachable:
                errors.append(
                    f"DAG {self.dag_id}: ノード {nid} が開始ノードから到達不能です"
                )

        return errors

    def all_nodes(self) -> dict[str, NarrativeNode]:
        return dict(self._nodes)


# YAML からの構築ヘルパー
def build_dag_from_yaml(dag_id: str, data: dict[str, Any]) -> NarrativeDAG:
    """YAML データから NarrativeDAG を構築"""
    dag = NarrativeDAG(dag_id)

    # ノード作成
    nodes_data = data.get("nodes", {})
    for node_id, node_data in nodes_data.items():
        node_type = NarrativeNodeType[node_data.get("type", "EVENT").upper()]
        node = NarrativeNode(
            node_id=node_id,
            node_type=node_type,
            title=node_data.get("title", ""),
            description=node_data.get("description", ""),
            actions=node_data.get("actions", []),
            rewards=node_data.get("rewards", {}),
            set_flags=node_data.get("set_flags", []),
            clear_flags=node_data.get("clear_flags", []),
            metadata=node_data.get("metadata", {}),
        )
        dag.add_node(node)

    # エッジ作成
    edges_data = data.get("edges", [])
    for edge_data in edges_data:
        edge = NarrativeEdge(
            edge_id=edge_data["edge_id"],
            source_node_id=edge_data["source"],
            target_node_id=edge_data["target"],
            edge_type=NarrativeEdgeType[edge_data.get("type", "CHOICE").upper()],
            choice_text=edge_data.get("choice_text", ""),
            condition_dsl=edge_data.get("condition_dsl", ""),
            effects=edge_data.get("effects", {}),
            required_flags=edge_data.get("required_flags", []),
            forbidden_flags=edge_data.get("forbidden_flags", []),
            weight=edge_data.get("weight", 1.0),
            hidden=edge_data.get("hidden", False),
        )
        source_node = dag.get_node(edge.source_node_id)
        if source_node:
            source_node.add_edge(edge)
            # 逆参照も追加
            target_node = dag.get_node(edge.target_node_id)
            if target_node:
                target_node.incoming_edges.append(edge.source_node_id)

    return dag


__all__ = [
    "NarrativeNodeType",
    "NarrativeEdgeType",
    "NarrativeEdge",
    "NarrativeNode",
    "NarrativeContext",
    "NarrativeDAG",
    "build_dag_from_yaml",
]
