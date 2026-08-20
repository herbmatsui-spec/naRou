"""
Quest Condition Parser Module (偏執的クエストシステム / 設計書 Phase 1 Step 2)
DSL 文字列 -> 条件 AST (``quest_condition_ast``) の変換を行う。

DSL は S 式形式を採用する（括弧で明示的な構造が堅牢）。

例::

    (and (>= player.level 10) (has inventory.sword))
    (or (not (in player.flags "met_elder")) (== world.phase "AWAKENING"))
    (xor (has flag.drank_potion) (has flag.read_scroll))
"""

from __future__ import annotations

from typing import Any

from quest_condition_ast import (
    COMBINATOR_OPERATORS,
    LEAF_OPERATORS,
    AndCondition,
    ConditionNodeBase,
    LeafCondition,
    NotCondition,
    OrCondition,
    XorCondition,
)


class ConditionParseError(ValueError):
    """DSL 文字列が不正な場合に送出される。"""


_Token = tuple[str, str]  # (kind, text)  kind: lparen|rparen|atom|str


def _tokenize(dsl: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    n = len(dsl)
    while i < n:
        c = dsl[i]
        if c == "(":
            tokens.append(("lparen", ""))
            i += 1
        elif c == ")":
            tokens.append(("rparen", ""))
            i += 1
        elif c.isspace():
            i += 1
        elif c in ('"', "'"):
            quote = c
            i += 1
            buf: list[str] = []
            while i < n and dsl[i] != quote:
                if dsl[i] == "\\" and i + 1 < n:
                    buf.append(dsl[i + 1])
                    i += 2
                else:
                    buf.append(dsl[i])
                    i += 1
            if i >= n:
                raise ConditionParseError("文字列リテラルが閉じられていません")
            i += 1  # 終端の引用符を消費
            tokens.append(("str", "".join(buf)))
        else:
            buf = []
            while i < n and dsl[i] not in "()\"' \t\n\r":
                buf.append(dsl[i])
                i += 1
            tokens.append(("atom", "".join(buf)))
    return tokens


def _coerce(text: str) -> Any:
    """atom トークンを Python リテラルに変換する。"""
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null" or low == "none":
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


class ConditionParser:
    """DSL 文字列を条件 AST へ変換するパーサー。"""

    def __init__(self) -> None:
        self._tokens: list[_Token] = []
        self._pos = 0

    def parse(self, dsl: str) -> ConditionNodeBase:
        if not dsl or not dsl.strip():
            raise ConditionParseError("空の条件式は解析できません")
        self._tokens = _tokenize(dsl)
        self._pos = 0
        node = self._parse_node()
        if self._pos != len(self._tokens):
            raise ConditionParseError("余分なトークンが残っています")
        return node

    def _peek(self) -> _Token:
        if self._pos >= len(self._tokens):
            raise ConditionParseError("予期せず式が終了しました")
        return self._tokens[self._pos]

    def _next(self) -> _Token:
        tok = self._peek()
        self._pos += 1
        return tok

    def _parse_node(self) -> ConditionNodeBase:
        kind, _ = self._peek()
        if kind != "lparen":
            raise ConditionParseError("'(' で始まる条件式が必要です")
        self._next()  # lparen 消費

        op_tok = self._next()
        if op_tok[0] == "lparen":
            raise ConditionParseError("演算子が必要です")
        op = op_tok[1]

        if op in COMBINATOR_OPERATORS:
            return self._parse_combinator(op)

        if op in LEAF_OPERATORS:
            return self._parse_leaf(op)

        raise ConditionParseError(f"未知の演算子: {op!r}")

    def _parse_combinator(self, op: str) -> ConditionNodeBase:
        children: list[ConditionNodeBase] = []
        while True:
            kind, _ = self._peek()
            if kind == "rparen":
                self._next()
                break
            children.append(self._parse_node())

        if op == "not":
            if len(children) != 1:
                raise ConditionParseError("not はちょうど1つの子条件を必要とします")
            return NotCondition(children[0])
        if op == "and":
            return AndCondition(children)
        if op == "or":
            return OrCondition(children)
        if op == "xor":
            if len(children) < 2:
                raise ConditionParseError("xor は2つ以上の子条件を必要とします")
            return XorCondition(children)
        raise ConditionParseError(f"未対応の組み合わせ演算子: {op!r}")

    def _parse_leaf(self, op: str) -> ConditionNodeBase:
        key_tok = self._next()
        if key_tok[0] not in ("atom", "str"):
            raise ConditionParseError("末端条件の key が不正です")
        key = key_tok[1]

        no_value_ops = ("exists", "truthy")
        optional_value_ops = ("has", "in", "contains")
        if op in no_value_ops:
            value: Any = None
        elif op in optional_value_ops:
            # 値は省略可能: 次が ')' ならキーの存在/真偽とみなす
            if self._peek()[0] == "rparen":
                value = None
            else:
                val_tok = self._next()
                value = _coerce(val_tok[1]) if val_tok[0] == "atom" else val_tok[1]
        else:
            val_tok = self._next()
            if val_tok[0] == "rparen":
                raise ConditionParseError(f"末端条件 {op} には値が必要です")
            value = _coerce(val_tok[1]) if val_tok[0] == "atom" else val_tok[1]

        close = self._next()
        if close[0] != "rparen":
            raise ConditionParseError("末端条件が ')' で閉じられていません")
        return LeafCondition(key, op, value)


PARSED_AST_CACHE: dict[str, ConditionNodeBase] = {}


def parse_condition(dsl: str) -> ConditionNodeBase:
    """DSL 文字列を条件 AST に変換する便利関数（キャッシュ対応）。"""
    if dsl in PARSED_AST_CACHE:
        return PARSED_AST_CACHE[dsl]
    node = ConditionParser().parse(dsl)
    PARSED_AST_CACHE[dsl] = node
    return node


__all__ = [
    "ConditionParser",
    "parse_condition",
    "parse_condition_from_yaml",
    "ConditionParseError",
    "PARSED_AST_CACHE",
]


def parse_condition_from_yaml(dsl: str):
    """YAML設定からのDSL文字列を条件ASTに変換する便利関数（後方互換用）。"""
    return parse_condition(dsl)
