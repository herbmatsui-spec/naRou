"""敵の意図表示 (enemy_intent) が「実際のAIの行動」と一致することを検証するテスト。

方針: 表示されている意図を鵜呑みにせず、実AIを実際に1ターン回した結果
(HP・座標・ダメージ) と突き合わせて検証する。判定材料はすべて実物から読む。

  - ビヘイビアツリー … skill_eater.ai.ai_system.AdvancedAISystem.trees (実行はしない)
  - モンスター/プレイヤー … ecs.entity.Entity
  - エンジン … game.Engine (実マップ・実LOS・実タイル判定)
"""

from __future__ import annotations

import time

import pytest

from constants import (
    AI_ROLE_BRUTE,
    AI_ROLE_FLANKER,
    AI_ROLE_KITER,
    FLEE_HP_RATIO,
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_GLYPH,
    INTENT_HEAL,
    INTENT_MOVE,
    KITER_PREFERRED_RANGE,
)
from enemy_intent import compute_intent
from skill_eater.ai.ai_system import (
    AdvancedAISystem,
    CastSpellAction,
    ChaseAction,
    FlankAction,
    FleeAction,
    HealSelfAction,
    KiteAction,
    MeleeAttackAction,
    SelectorNode,
    SequenceNode,
    SpreadAction,
    WanderAction,
)

# ---------------------------------------------------------------------------
# 実データからの参照ヘルパ (実AIの実行はせず、木の構造だけを読む)
# ---------------------------------------------------------------------------


def _tree_for(ai_type: str, ai_role: str):
    """process_ai が選ぶビヘイビアツリーを実データから特定する (ai_system と同じ振り分け)。"""
    ai = AdvancedAISystem()
    if ai_role == AI_ROLE_KITER:
        return ai.trees["kiter"]
    if ai_role == AI_ROLE_FLANKER:
        return ai.trees["flanker"]
    return ai.trees.get(ai_type, ai.trees["aggressive"])


def _actions_of(node) -> list:
    """木を再帰的に平坦化し、実際に実行されるアクション「インスタンス」の並びを返す。"""
    if isinstance(node, (SelectorNode, SequenceNode)):
        return [a for child in node.children for a in _actions_of(child)]
    return [node]


def _actions(ai_type: str, ai_role: str) -> list:
    return _actions_of(_tree_for(ai_type, ai_role))


def _heal_threshold(ai_type: str, ai_role: str) -> float | None:
    """その木が持つ回復アクションの閾値を実インスタンスから読む (ハードコードしない)。"""
    for action in _actions(ai_type, ai_role):
        if isinstance(action, HealSelfAction):
            return action.threshold
    return None


# ---------------------------------------------------------------------------
# テストシーン (実エンジン)
# ---------------------------------------------------------------------------


class _Scene:
    """実エンジン上でモンスターを1体だけ立ち上げるためのヘルパ。"""

    def __init__(self, eng):
        self.eng = eng
        self.player = eng.player

    def spawn(
        self, ai_type: str, ai_role: str, hp: int, max_hp: int = 100, dx: int = 0, dy: int = 0
    ):
        from ecs.entity import Entity

        e = Entity(
            x=self.player.x + dx,
            y=self.player.y + dy,
            name="テストモンスター",
            is_player=False,
            is_pet=False,
        )
        e.faction = "monster"
        e.ai_type = ai_type
        e.ai_role = ai_role
        e.preferred_range = KITER_PREFERRED_RANGE if ai_role == AI_ROLE_KITER else 1
        e.hp, e.max_hp = hp, max_hp
        assert self.eng.game_map.is_walkable(e.x, e.y), f"spawn ({dx},{dy}) は壁の中"
        self.eng.entity_manager.add_entity(e)
        return e

    def dist_to_player(self, entity) -> int:
        return max(abs(entity.x - self.player.x), abs(entity.y - self.player.y))


@pytest.fixture(scope="module")
def _engine():
    from game import Engine
    from renderer import NullRenderer

    eng = Engine(renderer=NullRenderer())
    eng.game_state_data.current_world = "skill_eater"
    return eng


@pytest.fixture
def scene(_engine):
    """テストごとに附加したモンスターとプレイヤー状態をもとに戻す。"""
    eng = _engine
    player = eng.player
    saved_entities = list(eng.entity_manager.entities)
    saved_state = (player.hp, player.x, player.y)
    yield _Scene(eng)
    eng.entity_manager.entities[:] = saved_entities
    player.hp, player.x, player.y = saved_state


# ---------------------------------------------------------------------------
# 前提: 役割ごとの回復/逃走アクションの有無 (実データから読む)
# ---------------------------------------------------------------------------

# HealSelfAction も FleeAction も持たないロール =「回復/逃走と表示してはいけない」ロール
_ROLES_WITHOUT_HEAL_OR_FLEE = [
    ("aggressive", AI_ROLE_BRUTE),
    ("boss", AI_ROLE_BRUTE),
    ("aggressive", AI_ROLE_KITER),
    ("aggressive", AI_ROLE_FLANKER),
]

# HealSelfAction を持つロール = 回復表示が正当化されるロール
_ROLES_WITH_HEAL = [
    ("coward", AI_ROLE_BRUTE),
    ("caster", AI_ROLE_BRUTE),
    ("tactical", AI_ROLE_BRUTE),
]

_ALL_ROLES = _ROLES_WITHOUT_HEAL_OR_FLEE + _ROLES_WITH_HEAL


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITHOUT_HEAL_OR_FLEE)
def test_premise_no_heal_or_flee_action_in_role(ai_type, ai_role):
    """前提の検証: 該当ロールの木に HealSelfAction / FleeAction は実在しない。"""
    types = [type(a) for a in _actions(ai_type, ai_role)]
    assert HealSelfAction not in types
    assert FleeAction not in types


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITH_HEAL)
def test_premise_heal_action_exists_in_role(ai_type, ai_role):
    types = [type(a) for a in _actions(ai_type, ai_role)]
    assert HealSelfAction in types
    assert _heal_threshold(ai_type, ai_role) is not None


@pytest.mark.parametrize(("ai_type", "ai_role"), _ALL_ROLES)
def test_premise_every_action_has_an_intent_forecast(ai_type, ai_role):
    """未知のアクションが追加されたら閾値フォールバックに落ちるよう察知する。"""
    from enemy_intent import _action_guards

    for action in _actions(ai_type, ai_role):
        assert type(action) in _action_guards(), f"{type(action).__name__} の予測が未定義"


def test_premise_all_real_actions_are_known():
    """将来アクションが追加されたらこのテストが落ちる (予測未定義を検知)。"""
    from enemy_intent import _action_guards

    ai = AdvancedAISystem()
    for tree in ai.trees.values():
        for action in _actions_of(tree):
            assert type(action) in _action_guards(), f"未対応: {type(action).__name__}"


# ---------------------------------------------------------------------------
# 主題1: 回復の「嘘」を打つな
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITHOUT_HEAL_OR_FLEE)
def test_low_hp_never_reports_heal_without_heal_action(ai_type, ai_role, scene):
    """aggressive/boss などが低HPでも「回復」意図を表示してはいけない。"""
    monster = scene.spawn(ai_type, ai_role, hp=30, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent is not None, "低HPの敵に意図が無いのは別の話"
    assert intent["type"] != INTENT_HEAL


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITHOUT_HEAL_OR_FLEE)
def test_low_hp_monster_without_heal_action_really_does_not_heal(ai_type, ai_role, scene):
    """表示だけでなく、実AIを1ターン回してもHPが増えないことを確認する。"""
    monster = scene.spawn(ai_type, ai_role, hp=30, dx=3)
    intent = compute_intent(monster, scene.eng)
    hp_before = monster.hp
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert monster.hp == hp_before, "回復しないはずの敵が回復した"
    assert intent["type"] != INTENT_HEAL


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITH_HEAL)
def test_heal_capable_role_reports_heal_at_real_threshold(ai_type, ai_role, scene):
    """ハードコードした 35% ではなく、実 HealSelfAction の閾値を使う。"""
    threshold = _heal_threshold(ai_type, ai_role)
    monster = scene.spawn(ai_type, ai_role, hp=int(100 * threshold), max_hp=100, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_HEAL


@pytest.mark.parametrize(("ai_type", "ai_role"), _ROLES_WITH_HEAL)
def test_heal_capable_role_above_real_threshold_does_not_heal(ai_type, ai_role, scene):
    threshold = _heal_threshold(ai_type, ai_role)
    hp = min(100, int(100 * threshold) + 5)
    monster = scene.spawn(ai_type, ai_role, hp=hp, max_hp=100, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] != INTENT_HEAL


# ---------------------------------------------------------------------------
# 主題2: 閾値ではなく「実際に次にやる行動」の予測であること
# ---------------------------------------------------------------------------


def test_role_without_flee_action_does_not_flee_at_low_hp(scene):
    """aggressive には FleeAction が無いので、25%以下でも「逃走」は嘘。"""
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=10, dx=3)
    assert monster.hp / monster.max_hp < FLEE_HP_RATIO
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_MOVE
    assert intent["target"] == (scene.player.x, scene.player.y)


def test_coward_flees_above_heal_threshold(scene):
    """coward の木は Sequence[Heal(0.5), Flee]。回復しない tick には必ず逃走する。"""
    monster = scene.spawn("coward", AI_ROLE_BRUTE, hp=55, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_FLEE


def test_low_hp_aggressive_really_chases(scene):
    """「移動」と表示した実AIは、実際に追跡した (距離が縮まった)。"""
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=10, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_MOVE

    before = scene.dist_to_player(monster)
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert scene.dist_to_player(monster) < before, "追跡していない"


def test_coward_really_heals_when_heal_is_shown(scene):
    monster = scene.spawn("coward", AI_ROLE_BRUTE, hp=30, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_HEAL

    hp_before = monster.hp
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert monster.hp > hp_before, "回復していない"


def test_coward_really_flees_when_flee_is_shown(scene):
    monster = scene.spawn("coward", AI_ROLE_BRUTE, hp=55, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_FLEE

    before = scene.dist_to_player(monster)
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert scene.dist_to_player(monster) > before, "距離を取っていない"


def test_adjacent_aggressive_really_attacks(scene, monkeypatch):
    # 近接攻撃は命中判定の抽選を行うため、検証のために命中を固定する
    monkeypatch.setattr("random.randint", lambda a, b: 1)
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=100, dx=1)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_ATTACK

    hp_before = scene.player.hp
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert scene.player.hp < hp_before, "ダメージを与えていない"


def test_adjacent_kiter_retreats_instead_of_attacking(scene):
    """kiter の木は KiteAction が先頭。隣接時は間合いを広げる (近接攻撃はしない)。"""
    monster = scene.spawn("aggressive", AI_ROLE_KITER, hp=100, dx=1)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_MOVE
    assert intent["target"] is None, "プレイヤーから離れる移動にプレイヤー位置は付けない"

    before = scene.dist_to_player(monster)
    AdvancedAISystem().process_ai(monster, scene.eng)
    assert scene.dist_to_player(monster) > before, "間合いを広げていない"


def test_caster_in_cast_range_is_cast(scene):
    monster = scene.spawn("caster", AI_ROLE_BRUTE, hp=100, dx=3)
    intent = compute_intent(monster, scene.eng)
    assert intent["type"] == INTENT_CAST


# ---------------------------------------------------------------------------
# 主題3: 予測できないものは「無い」と正直に言う
# ---------------------------------------------------------------------------


def test_monster_out_of_reach_reports_no_intent(scene):
    """索敵範囲外で追跡もできない敵は「移動」と嘘をつかず、意図なしを返す。"""
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=100, dx=12)
    assert scene.dist_to_player(monster) > 8  # ChaseAction の索敵範囲外
    assert compute_intent(monster, scene.eng) is None


def test_low_hp_unreachable_monster_does_not_claim_heal(scene):
    monster = scene.spawn("boss", AI_ROLE_BRUTE, hp=5, dx=12)
    assert compute_intent(monster, scene.eng) is None


# ---------------------------------------------------------------------------
# 既存契約の維持
# ---------------------------------------------------------------------------


def test_no_intent_for_player_pet_and_neutral(scene):
    from ecs.entity import Entity

    for kwargs in ({"is_player": True}, {"is_pet": True}):
        e = Entity(x=scene.player.x + 3, y=scene.player.y, name="npc", **kwargs)
        e.hp, e.max_hp = 30, 100
        assert compute_intent(e, scene.eng) is None

    neutral = Entity(
        x=scene.player.x + 3, y=scene.player.y, name="npc", is_player=False, is_pet=False
    )
    neutral.hp, neutral.max_hp = 30, 100
    neutral.faction = "neutral"
    assert compute_intent(neutral, scene.eng) is None


def test_no_intent_without_engine_or_with_dead_player(scene):
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=100, dx=3)
    assert compute_intent(monster, None) is None

    scene.player.hp = 0
    assert compute_intent(monster, scene.eng) is None


def test_intent_shape_and_glyph_vocabulary_unchanged(scene):
    """レンダラが読む形 (type/glyph/label/target) と既存の記号はそのまま。"""
    monster = scene.spawn("aggressive", AI_ROLE_BRUTE, hp=100, dx=1)
    intent = compute_intent(monster, scene.eng)
    assert set(intent) == {"type", "glyph", "label", "target"}
    assert intent["glyph"] == INTENT_GLYPH[intent["type"]]


def test_forecast_is_cheap_enough_for_visible_monsters(scene):
    """毎ティック、可視モンスター全員分を回しても実用上十分安い。"""
    monsters = [
        scene.spawn("aggressive", AI_ROLE_BRUTE, hp=30, dx=3 + i % 5, dy=i % 4) for i in range(50)
    ]
    start = time.perf_counter()
    for m in monsters:
        compute_intent(m, scene.eng)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"50体で {elapsed:.3f}s (1s 未満ではない)"
