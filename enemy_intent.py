"""
敵の「次回行動（意図）」予測 (提案2: 意図可視化)

compute_intent(entity, engine) は、敵が次に取るであろう行動を予測し辞書で返す。
この情報は描画・予測のみに使用され、戦闘結果そのものは変えない（非破壊）。

予測は skill_eater.ai のビヘイビアツリーを「実行せずに読む」ことで行う。
AI が持っていない行動（回復・逃走など）は表示しない — 表示できる意図を捏造しないことが最優先で、
木やアクションが読めない場合のみ HP 閾値による旧来表示へフォールバックする。
"""

from __future__ import annotations

from typing import Any

from constants import (
    AI_ROLE_BRUTE,
    AI_ROLE_FLANKER,
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

_DIRS8 = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))

# ai_system 側の索敵距離 (ChaseAction._find_target / FleeAction)
_SIGHT_RANGE = 8

# コンパイル済み木の種類タグ
_OR = "or"
_AND = "and"
_LEAF = "leaf"

_UNSET = object()

_TREE_CACHE: dict[str, tuple] = {}
_TREE_CAPABILITIES: dict[str, tuple[bool, bool]] = {}
_ACTION_GUARDS: dict[type, Any] = {}
_AI_LOADED = False


class _Undetermined:
    """「予測できない」を表す番兵 (閾値フォールバックへ送る)"""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<意図: 未判定>"


_UNDETERMINED = _Undetermined()


def _is_ranged(entity: Any) -> bool:
    if getattr(entity, "ai_role", None) in _RANGED_ROLES:
        return True
    return getattr(entity, "ai_type", None) == "caster"


def _chebyshev(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


# ---------------------------------------------------------------------------
# 実AIの読み込み（木のコンパイルは1度だけ）
# ---------------------------------------------------------------------------


def _compile(node: Any, mod: Any) -> tuple:
    """木を実行せずに読めるよう、(種別, 内容) の入れ構造へ変換する。"""
    if isinstance(node, mod.SelectorNode):
        return (_OR, tuple(_compile(c, mod) for c in node.children))
    if isinstance(node, mod.SequenceNode):
        return (_AND, tuple(_compile(c, mod) for c in node.children))
    return (_LEAF, node)


def _capabilities(tree: tuple, mod: Any) -> tuple[bool, bool]:
    """(回復アクションを持つか, 逃走アクションを持つか) を実際に辿って判定する。"""
    kind, payload = tree
    if kind == _LEAF:
        return (isinstance(payload, mod.HealSelfAction), isinstance(payload, mod.FleeAction))
    has_heal = has_flee = False
    for child in payload:
        child_heal, child_flee = _capabilities(child, mod)
        has_heal = has_heal or child_heal
        has_flee = has_flee or child_flee
    return (has_heal, has_flee)


def _load_ai() -> None:
    """AI モジュールから木と予測関数を一度だけ取り込む。読み込めない場合も描画は止めない。"""
    global _AI_LOADED
    if _AI_LOADED:
        return
    _AI_LOADED = True
    try:
        from skill_eater.ai import ai_system as mod
    except Exception:  # noqa: BLE001 - AI 不在でも閾値フォールバックで意図を出す
        return

    system = mod.AdvancedAISystem()
    for name, tree in system.trees.items():
        compiled = _compile(tree, mod)
        _TREE_CACHE[name] = compiled
        _TREE_CAPABILITIES[name] = _capabilities(compiled, mod)

    _ACTION_GUARDS.update(
        {
            mod.HealSelfAction: _g_heal,
            mod.FleeAction: _g_flee,
            mod.MeleeAttackAction: _g_melee,
            mod.CastSpellAction: _g_cast,
            mod.ChaseAction: _g_chase,
            mod.WanderAction: _g_wander,
            mod.SpreadAction: _g_spread,
            mod.KiteAction: _g_kite,
            mod.FlankAction: _g_flank,
        }
    )


def _action_guards() -> dict[type, Any]:
    """アクション種別 → 意図予測関数。未登録のアクションは閾値フォールバックに落ちる。"""
    _load_ai()
    return _ACTION_GUARDS


def _resolve_tree(entity: Any) -> tuple[str, tuple] | None:
    """process_ai と同じ振り分けで、entity が実際に実行する木を選ぶ。

    挟撃( allies_in_sight )で brute→flanker に持ち替わる分岐は反映しない。
    両方の木が [近接攻撃, 追跡, 彷徨] を持ち回復も逃走も無いため、
    いずれの場合も意图の種類は変わらない（協力時の移動の内訳だけが違う）。
    """
    role = getattr(entity, "ai_role", AI_ROLE_BRUTE)
    if role == AI_ROLE_KITER:
        name = "kiter"
    elif role == AI_ROLE_FLANKER:
        name = "flanker"
    else:
        name = getattr(entity, "ai_type", "aggressive")
        if name not in _TREE_CACHE:
            name = "aggressive"
    compiled = _TREE_CACHE.get(name)
    return None if compiled is None else (name, compiled)


# ---------------------------------------------------------------------------
# 予測コンテキスト (エンジン参照の走査を纏めて1回だけ行う)
# ---------------------------------------------------------------------------


class _Ctx:
    """1体ぶんの予測に必要な盤面情報。隣接マスの走査結果は使い回す。"""

    __slots__ = (
        "entity",
        "engine",
        "px",
        "py",
        "dist",
        "has_los",
        "hp",
        "max_hp",
        "hp_ratio",
        "_free",
        "_adjacent",
        "_crowded",
    )

    def __init__(self, entity: Any, engine: Any) -> None:
        player = engine.player
        self.entity = entity
        self.engine = engine
        self.px, self.py = player.x, player.y
        self.dist = _chebyshev(entity.x, entity.y, self.px, self.py)

        los_fn = getattr(engine, "has_los", None)
        if los_fn is None:
            self.has_los = True
        else:
            from core_framework import Point

            self.has_los = bool(los_fn(Point(entity.x, entity.y), Point(self.px, self.py)))

        self.hp = getattr(entity, "hp", 0)
        self.max_hp = max(1, getattr(entity, "max_hp", 1))
        self.hp_ratio = self.hp / self.max_hp
        self._free = None
        self._adjacent = _UNSET
        self._crowded = None

    def free_neighbours(self) -> list:
        """移動先になり得る隣接タイル。Spread/Kite/Chase/Flee どれも同じ判定を使う。"""
        if self._free is None:
            free_fn = getattr(self.engine, "is_tile_free", None)
            tiles = []
            if free_fn is not None:
                ex, ey = self.entity.x, self.entity.y
                for dx, dy in _DIRS8:
                    nx, ny = ex + dx, ey + dy
                    if free_fn(nx, ny):
                        tiles.append((nx, ny))
            self._free = tiles
        return self._free

    def adjacent_enemy(self):
        """MeleeAttackAction が殴る相手 (プレイヤー or ペットの隣接個体)。"""
        if self._adjacent is _UNSET:
            self._adjacent = None
            get_at = getattr(self.engine, "get_entity_at", None)
            if get_at is not None:
                ex, ey = self.entity.x, self.entity.y
                for dx, dy in _DIRS8:
                    ent = get_at(ex + dx, ey + dy)
                    if (
                        ent is not None
                        and getattr(ent, "hp", 0) > 0
                        and (getattr(ent, "is_player", False) or getattr(ent, "is_pet", False))
                    ):
                        self._adjacent = ent
                        break
        return self._adjacent

    def crowded(self) -> bool:
        """SpreadAction と同じ「味方が隣接にいる」判定。"""
        if self._crowded is None:
            self._crowded = False
            get_at = getattr(self.engine, "get_entity_at", None)
            if get_at is not None:
                ex, ey = self.entity.x, self.entity.y
                for dx, dy in _DIRS8:
                    ent = get_at(ex + dx, ey + dy)
                    if ent is self.entity:
                        continue
                    if ent is not None and getattr(ent, "faction", None) == "monster":
                        self._crowded = True
                        break
        return self._crowded


# ---------------------------------------------------------------------------
# アクション別の意図予測 (各 execute() の成功条件を副作用なしで判定する)
# ---------------------------------------------------------------------------


def _g_heal(node: Any, ctx: _Ctx):
    """HealSelfAction: HP が実木の閾値以下なら自己修復する。"""
    if ctx.hp > ctx.max_hp * node.threshold:
        return None
    return (INTENT_HEAL, None)


def _g_flee(node: Any, ctx: _Ctx):
    """FleeAction: 追跡範囲内で、距離を取れる隣接マスがあれば逃げる。"""
    if ctx.dist > _SIGHT_RANGE:
        return None
    for nx, ny in ctx.free_neighbours():
        if _chebyshev(nx, ny, ctx.px, ctx.py) > ctx.dist:
            return (INTENT_FLEE, None)
    return None


def _g_melee(node: Any, ctx: _Ctx):
    """MeleeAttackAction: 隣接するプレイヤー or ペットがいれば殴る。"""
    target = ctx.adjacent_enemy()
    if target is None:
        return None
    return (INTENT_ATTACK, (target.x, target.y))


def _g_cast(node: Any, ctx: _Ctx):
    """CastSpellAction: 射程内かつ視認できれば魔矢を放つ (命中は 40% ロール)。"""
    if _CAST_RANGE_MIN <= ctx.dist <= _CAST_RANGE_MAX and ctx.has_los:
        return (INTENT_CAST, (ctx.px, ctx.py))
    return None


def _g_chase(node: Any, ctx: _Ctx):
    """ChaseAction: 視界内のプレイヤーへ経路を迪って追いかける。

    A* を毎ティック回すのは高すぎるので「移動可能な隣接マスがあるか」で代用する。
    それも無ければ隣接マスを踏めず確実に動けないので、追跡しないものとして扱う。
    """
    if ctx.dist > _SIGHT_RANGE or not ctx.has_los:
        return None
    if not ctx.free_neighbours():
        return None
    return (INTENT_MOVE, (ctx.px, ctx.py))


def _g_spread(node: Any, ctx: _Ctx):
    """SpreadAction: 味方が密集しているときだけ隙間で位置調整する (狙いはプレイヤーではない)。"""
    if not ctx.free_neighbours() or not ctx.crowded():
        return None
    return (INTENT_MOVE, None)


def _g_wander(node: Any, ctx: _Ctx):
    """WanderAction: 進む向きも移動可否も不定なので「意図」として提示できない。

    発生しない扱いにしても木全体の結果は変わらない（どの木でも最後尾のため）。
    """
    return None


def _g_kite(node: Any, ctx: _Ctx):
    """KiteAction: 間合いに応じて射撃・後退・接近を切り替える。"""
    if _is_ranged(ctx.entity) and _CAST_RANGE_MIN <= ctx.dist <= _CAST_RANGE_MAX and ctx.has_los:
        return (INTENT_CAST, (ctx.px, ctx.py))
    if not ctx.free_neighbours():
        return None
    pref = _kite_range(ctx)
    if ctx.dist < pref:
        return (INTENT_MOVE, None)  # プレイヤーから距離を取る移動
    if ctx.dist > pref:
        return (INTENT_MOVE, (ctx.px, ctx.py))
    return None


def _g_flank(node: Any, ctx: _Ctx):
    """FlankAction: 隣接なら攻撃、隣接でなければプレイヤー迂回 목표로踏み込む。"""
    if ctx.dist <= 1:
        target = ctx.adjacent_enemy()
        if target is None:
            return None
        return (INTENT_ATTACK, (target.x, target.y))
    if not ctx.free_neighbours():
        return None
    return (INTENT_MOVE, (ctx.px, ctx.py))


def _kite_range(ctx: _Ctx) -> int:
    """KiteAction と同じ間合い計算 (ai_system 側の公開関数をそのまま使う)。"""
    from constants import HARD_KITER_RANGE_BONUS
    from skill_eater.ai.ai_system import kiter_range

    pref = kiter_range(ctx.entity, getattr(ctx.engine, "dungeon_level", 0))
    if getattr(ctx.engine, "difficulty", "normal") == "hard":
        pref += HARD_KITER_RANGE_BONUS
    return pref


# ---------------------------------------------------------------------------
# 木を「読んで成立する枝を選ぶ」演繹 (実行はしない)
# ---------------------------------------------------------------------------


def _predict(tree: tuple, ctx: _Ctx):
    """コンパイル済み木を順に評価し、最初に成立する行動の意図を返す。

    戻り値: (意図種別, 標的) / None(この枝は成立しない) / _UNDETERMINED(判定不能)
    """
    kind, payload = tree
    if kind == _LEAF:
        guard = _ACTION_GUARDS.get(type(payload))
        return _UNDETERMINED if guard is None else guard(payload, ctx)

    fired = None
    for child in payload:
        result = _predict(child, ctx)
        if result is _UNDETERMINED:
            return _UNDETERMINED
        if result is None:
            if kind == _AND and fired is None:
                # 成立前に失敗したシーケンスはそれ以降も実行されない
                return None
            continue
        if kind == _OR:
            return result
        if fired is None:
            fired = result
    return fired


def _threshold_intent(ctx: _Ctx, capabilities: tuple[bool, bool] | None):
    """選択論理が読めなかったときのフォールバック。

    回復/逃走はその木に実在するアクションがあるときだけ表示する。
    木ごと読めない場合は旧来の閾値表示にそのまま委ねる。
    """
    if capabilities is None:
        has_heal, has_flee = True, True
    else:
        has_heal, has_flee = capabilities
    if ctx.hp_ratio < FLEE_HP_RATIO and has_flee:
        return (INTENT_FLEE, None)
    if ctx.hp_ratio < _HEAL_HP_RATIO and has_heal:
        return (INTENT_HEAL, None)
    if ctx.dist <= 1:
        return (INTENT_ATTACK, (ctx.px, ctx.py))
    if _is_ranged(ctx.entity) and _CAST_RANGE_MIN <= ctx.dist <= _CAST_RANGE_MAX and ctx.has_los:
        return (INTENT_CAST, (ctx.px, ctx.py))
    return (INTENT_MOVE, (ctx.px, ctx.py))


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

    _load_ai()
    ctx = _Ctx(entity, engine)

    resolved = _resolve_tree(entity)
    if resolved is None:
        result = _UNDETERMINED
        capabilities = None
    else:
        name, tree = resolved
        result = _predict(tree, ctx)
        capabilities = _TREE_CAPABILITIES.get(name)

    if result is _UNDETERMINED:
        result = _threshold_intent(ctx, capabilities)

    # 意図として提示できない (何もしない/ランダム彷徨) 場合は「無い」と答える
    return None if result is None else _make(result[0], result[1])


def _make(intent_type: str, target) -> dict:
    return {
        "type": intent_type,
        "glyph": INTENT_GLYPH.get(intent_type, "·"),
        "label": INTENT_LABEL_JA.get(intent_type, intent_type),
        "target": target,
    }
