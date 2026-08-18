"""
Quest Condition AST Module (偏執的クエストシステム / 設計書 Phase 1 Step 1)
条件分岐ツリー (CQCT) の抽象構文木 (AST) 定義。

各ノードは ``evaluate(context) -> bool`` を実装し、状態コンテキストに対して
自身を評価する（Step 1 / Step 3 の責務は同一 AST に内包しつつ、
演算子ロジックは :func:`_apply_operator` に集約している）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Union

# 比較演算子・述語演算子の許可リスト
LEAF_OPERATORS = (
    "==", "!=", ">=", "<=", ">", "<",
    "has", "in", "contains", "exists", "truthy",
)
# 組み合わせ演算子（論理結合子）
COMBINATOR_OPERATORS = ("and", "or", "xor", "not")


def _apply_operator(op: str, left: Any, right: Any) -> bool:
    """Leaf の比較/述語演算子を実行する。"""
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op in (">=", "<=", ">", "<"):
        try:
            if op == ">=":
                return left >= right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            return left < right
        except TypeError:
            return False
    if op in ("has", "contains"):
        if right is None:
            return bool(left)
        if isinstance(left, (list, tuple, set, dict, str)):
            return right in left
        return left == right
    if op == "in":
        if right is None:
            return bool(left)
        if isinstance(right, (list, tuple, set, dict, str)):
            return left in right
        return False
    if op == "exists":
        return left is not None
    if op == "truthy":
        return bool(left)
    raise ValueError(f"未対応の演算子: {op!r}")


class ConditionNode(ABC):
    """AST ノードの基底クラス。全ノードは evaluate を実装する。"""

    @abstractmethod
    def evaluate(self, context: Any) -> bool:
        """状態コンテキストを元に条件を評価し、真偽を返す。"""


@dataclass(frozen=True)
class LeafCondition(ConditionNode):
    """末端条件ノード。

    ``key`` はドット区切りの状態パス (例: ``player.level``)、
    ``op`` は比較/述語演算子、``value`` は比較対象値。
    """

    key: str
    op: str
    value: Any

    def evaluate(self, context: Any) -> bool:
        left = context.resolve(self.key)
        return _apply_operator(self.op, left, self.value)


@dataclass(frozen=True)
class NotCondition(ConditionNode):
    """否定ノード。単一の子を反転させる。"""

    child: ConditionNode

    def evaluate(self, context: Any) -> bool:
        return not self.child.evaluate(context)


@dataclass(frozen=True)
class AndCondition(ConditionNode):
    """論理積ノード。全ての子が真なら真。"""

    children: List[ConditionNode]

    def evaluate(self, context: Any) -> bool:
        return all(child.evaluate(context) for child in self.children)


@dataclass(frozen=True)
class OrCondition(ConditionNode):
    """論理和ノード。いずれかの子が真なら真。"""

    children: List[ConditionNode]

    def evaluate(self, context: Any) -> bool:
        return any(child.evaluate(context) for child in self.children)


@dataclass(frozen=True)
class XorCondition(ConditionNode):
    """排他的論理和ノード。ちょうど1つの子が真なら真。"""

    children: List[ConditionNode]

    def evaluate(self, context: Any) -> bool:
        return sum(1 for child in self.children if child.evaluate(context)) == 1


ConditionNodeBase = ConditionNode  # main_quest_system 互換エイリアス


def is_condition_node(obj: Any) -> bool:
    """任意のオブジェクトが条件ノード AST か判定する。"""
    return isinstance(obj, ConditionNode)


__all__ = [
    "ConditionNode",
    "ConditionNodeBase",
    "LeafCondition",
    "NotCondition",
    "AndCondition",
    "OrCondition",
    "XorCondition",
    "is_condition_node",
    "LEAF_OPERATORS",
    "COMBINATOR_OPERATORS",
    "_apply_operator",
]
