"""
Quest Condition Evaluator Module (偏執的クエストシステム / 設計書 Phase 1 Step 3)
プレイヤー/ワールド状態 (context) を条件 AST に通し、bool を返す評価エンジン。

評価ロジックの本体は ``quest_condition_ast`` の各ノードの ``evaluate`` に内包
されており、このモジュールはコンテキストの定義と評価のファサードを提供する。
"""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from quest_condition_ast import ConditionNode


@runtime_checkable
class EvaluationContext(Protocol):
    """評価コンテキストが満たすべきプロトコル (main_quest_system 互換名)。"""

    def resolve(self, key: str) -> Any:
        """ドット区切りパス (例: ``player.level``) を状態値に解決する。"""
        ...


class DictContext:
    """入れ子辞書で状態を保持する標準コンテキスト実装。"""

    def __init__(self, state: Dict[str, Any]) -> None:
        self._state = state

    def resolve(self, key: str) -> Any:
        node: Any = self._state
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node


# 後方互換のための別名
ConditionContext = EvaluationContext


def _as_context(context: Any) -> EvaluationContext:
    if isinstance(context, EvaluationContext):
        return context
    if isinstance(context, dict):
        return DictContext(context)
    raise TypeError("評価コンテキストは EvaluationContext または dict である必要があります")


def evaluate(node: ConditionNode, context: Any) -> bool:
    """条件 AST を評価し、真偽を返す（ノードの evaluate に委譲）。"""
    return node.evaluate(_as_context(context))


class QuestConditionEvaluator:
    """評価エンジンのファサード（再利用用）。"""

    def evaluate(self, node: ConditionNode, context: Any) -> bool:
        return evaluate(node, context)


__all__ = [
    "evaluate",
    "EvaluationContext",
    "ConditionContext",
    "DictContext",
    "QuestConditionEvaluator",
]
