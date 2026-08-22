"""
敵の「次回行動（意図）」予測 (提案2: 意図可視化)

compute_intent(entity, engine) は、敵が次に取るであろう行動を予測し辞書で返す。
この情報は描画・予測のみに使用され、戦闘結果そのものは変えない（非破壊）。
"""

from __future__ import annotations

from typing import Any

from constants import (
    AI_ROLE_KITER,
    AI_ROLE_SUPPORT,
    FLEE_HP_RATIO,
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_GLYPH,
    INTENT_HEAL,
    INTENT_LABEL_JA,
    INTENT_MOVE,
)

# 遠隔・詠唱系とみなすロール/ai_type
_RANGED_ROLES = (AI_ROLE_KITER, AI_ROLE_SUPPORT)
_CAST_RANGE_MIN = 2
_CAST_RANGE_MAX = 5
_HEAL_HP_RATIO = 0.35


def _is_ranged(entity: Any) -> bool:
    if entity.ai_role in _RANGED_ROLES:
        return True
    return getattr(entity, "ai_type", None) == "caster"


def _chebyshev(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


def compute_intent(entity: Any, engine: Any) -> dict | None:
    """敵 entity の次回行動を予測して dict を返す。予測不能なら None。"""
    # プレイヤー/ペット自身には意図なし
    if getattr(entity, "is_player", False) or getattr(entity, "is_pet", False):
        return None
    # モンスター以外（中立NPC等）には意図を表示しない
    if getattr(entity, "faction", None) != "monster":
        return None
    if engine is None:
        return None

    player = getattr(engine, "player", None)
    if player is None or getattr(player, "hp", 0) <= 0:
        return None

    px, py = player.x, player.y
    ex, ey = entity.x, entity.y
    dist = _chebyshev(ex, ey, px, py)

    has_los = True
    los_fn = getattr(engine, "has_los", None)
    if los_fn is not None:
        from core_framework import Point

        has_los = bool(los_fn(Point(ex, ey), Point(px, py)))

    max_hp = max(1, getattr(entity, "max_hp", 1))
    hp_ratio = getattr(entity, "hp", 0) / max_hp

    # 1) 隣接 -> 攻撃
    if dist <= 1:
        return _make(INTENT_ATTACK, (px, py))

    # 2) 低HP -> 逃走（治癒より優先）
    if hp_ratio < FLEE_HP_RATIO:
        return _make(INTENT_FLEE, None)

    # 3) 低HP -> 回復
    if hp_ratio < _HEAL_HP_RATIO:
        return _make(INTENT_HEAL, None)

    # 4) 遠隔系かつ射程内かつ視認 -> 詠唱
    if _is_ranged(entity) and _CAST_RANGE_MIN <= dist <= _CAST_RANGE_MAX and has_los:
        return _make(INTENT_CAST, (px, py))

    # 5) それ以外 -> 接近（追跡）
    return _make(INTENT_MOVE, (px, py))


def _make(intent_type: str, target) -> dict:
    return {
        "type": intent_type,
        "glyph": INTENT_GLYPH.get(intent_type, "·"),
        "label": INTENT_LABEL_JA.get(intent_type, intent_type),
        "target": target,
    }
