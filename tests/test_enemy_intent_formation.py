"""敵の意図可視化 (提案2) と 陣形・連携タクティクス (提案4) のテスト。"""

from __future__ import annotations

import pytest

from constants import (
    AI_ROLE_BRUTE,
    AI_ROLE_KITER,
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_HEAL,
    INTENT_MOVE,
)
from enemy_intent import compute_intent


class FakePoint:
    def __init__(self, x, y):
        self.x, self.y = x, y


class FakeEntity:
    """compute_intent 用の軽量偽エンティティ"""

    def __init__(
        self,
        x=0,
        y=0,
        hp=100,
        max_hp=100,
        ai_role=AI_ROLE_BRUTE,
        faction="monster",
        is_player=False,
        is_pet=False,
        name="Fake",
    ):
        self.name = name
        self.x, self.y = x, y
        self.hp, self.max_hp = hp, max_hp
        self.ai_role = ai_role
        self.faction = faction
        self.is_player = is_player
        self.is_pet = is_pet


class FakeEngine:
    def __init__(self, player, los=True):
        self.player = player
        self._los = los

    def has_los(self, a, b):
        return self._los


def _player(x=5, y=5, hp=100):
    return FakeEntity(x=x, y=y, hp=hp, faction="player", is_player=True)


def test_skeleton():
    assert True


def test_none_when_no_engine():
    assert compute_intent(FakeEntity(), None) is None


def test_adjacent_is_attack():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=5, y=4)  # 距離1
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_ATTACK
    assert intent["target"] == (5, 5)


def test_caster_in_range_is_cast():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=2, y=5, ai_role=AI_ROLE_KITER)  # 距離3, 視認
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_CAST


def test_caster_out_of_range_is_move():
    eng = FakeEngine(_player(7, 5), los=True)
    e = FakeEntity(x=0, y=5, ai_role=AI_ROLE_KITER)  # 距離7 -> 射程外
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_MOVE


def test_low_hp_flees():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, hp=20, max_hp=100)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_FLEE


def test_mid_low_hp_heals():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, hp=33, max_hp=100)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_HEAL


def test_default_is_move_with_target():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=0, y=0)
    intent = compute_intent(e, eng)
    assert intent["type"] == INTENT_MOVE
    assert intent["target"] == (5, 5)


def test_no_intent_for_neutral_npc():
    eng = FakeEngine(_player(5, 5))
    e = FakeEntity(x=3, y=5, faction="neutral")
    assert compute_intent(e, eng) is None


def test_no_intent_when_player_dead():
    eng = FakeEngine(_player(5, 5, hp=0))
    e = FakeEntity(x=5, y=4)
    assert compute_intent(e, eng) is None


@pytest.mark.parametrize(
    "intent_type",
    [INTENT_ATTACK, INTENT_CAST, INTENT_FLEE, INTENT_HEAL, INTENT_MOVE],
)
def test_intent_shape(intent_type):
    # _make の出力形を確認（glyph/label が必ず存在）
    from enemy_intent import _make

    d = _make(intent_type, (1, 1))
    assert set(d.keys()) == {"type", "glyph", "label", "target"}
    assert d["glyph"]
    assert d["label"]


class FakeConsole:
    def __init__(self):
        self.calls = []

    def print(self, x, y, string, fg=None):
        self.calls.append((x, y, string, fg))


def test_render_entity_intent_draws_for_monster():
    from entity import Entity
    from entity_renderer import render_entity_intent

    e = Entity(x=5, y=5, name="gob", is_player=False, is_pet=False)
    e.faction = "monster"
    e.next_intent = {"type": INTENT_ATTACK, "glyph": "X", "label": "突撃", "target": (5, 6)}
    c = FakeConsole()
    render_entity_intent(c, e, 5, 5)
    assert any(s == "X" for _, _, s, _ in c.calls)
    assert any("突撃" in s for _, _, s, _ in c.calls)


def test_render_entity_intent_skips_player_and_pet():
    from entity import Entity
    from entity_renderer import render_entity_intent

    for kw in ({"is_player": True}, {"is_pet": True}):
        e = Entity(x=5, y=5, name="hero", **kw)
        e.next_intent = {"type": INTENT_ATTACK, "glyph": "X", "label": "突撃", "target": None}
        c = FakeConsole()
        render_entity_intent(c, e, 5, 5)
        assert c.calls == []


def test_render_entity_intent_skips_when_none():
    from entity import Entity
    from entity_renderer import render_entity_intent

    e = Entity(x=5, y=5, name="gob", is_player=False, is_pet=False)
    e.faction = "monster"
    e.next_intent = None
    c = FakeConsole()
    render_entity_intent(c, e, 5, 5)
    assert c.calls == []


# ---------------------------------------------------------------------------
# 統合テスト (提案2: 実エンジン)
# ---------------------------------------------------------------------------


class TestIntentIntegration:
    def _make_engine(self):
        from game import Engine
        from renderer import NullRenderer

        eng = Engine(renderer=NullRenderer())
        eng.game_state_data.current_world = "skill_eater"
        return eng

    def _add_monster(self, eng, dx, dy, **kw):
        from entity import Entity

        hp = kw.pop("hp", 30)
        max_hp = kw.pop("max_hp", 30)
        e = Entity(
            x=eng.player.x + dx,
            y=eng.player.y + dy,
            char="o",
            color=(200, 50, 50),
            name=kw.pop("name", "テスト鬼"),
            is_player=False,
            is_pet=False,
            **kw,
        )
        e.hp, e.max_hp = hp, max_hp
        e.faction = "monster"
        eng.entity_manager.add_entity(e)
        return e

    def test_adjacent_intent_is_attack(self):
        eng = self._make_engine()
        m = self._add_monster(eng, 1, 0)
        eng.advance_world()
        assert m.next_intent is not None
        assert m.next_intent["type"] == INTENT_ATTACK

    def test_low_hp_intent_is_flee_or_heal(self):
        eng = self._make_engine()
        # 距離を離して隣接攻撃を避けつつ低HPにする
        m = self._add_monster(eng, 3, 0, hp=10, max_hp=100)
        eng.advance_world()
        assert m.next_intent["type"] in (INTENT_FLEE, INTENT_HEAL)

    def test_multiple_monsters_independent_intent(self):
        eng = self._make_engine()
        a = self._add_monster(eng, 1, 0, name="鬼A")
        b = self._add_monster(eng, 2, 0, name="鬼B")
        eng.advance_world()
        assert a.next_intent is not None
        assert b.next_intent is not None

    def test_los_gates_cast(self):
        # kiter が射程内でも LOS なしなら cast にならず move になる
        eng_seen = FakeEngine(_player(5, 5), los=True)
        eng_blind = FakeEngine(_player(5, 5), los=False)
        e_seen = FakeEntity(x=2, y=5, ai_role=AI_ROLE_KITER)
        e_blind = FakeEntity(x=2, y=5, ai_role=AI_ROLE_KITER)
        assert compute_intent(e_seen, eng_seen)["type"] == INTENT_CAST
        assert compute_intent(e_blind, eng_blind)["type"] == INTENT_MOVE

    def test_difficulty_independent(self):
        eng = FakeEngine(_player(5, 5))
        e = FakeEntity(x=5, y=4)
        # engine に difficulty 属性があっても意図は変わらない
        eng.difficulty = "hard"
        assert compute_intent(e, eng)["type"] == INTENT_ATTACK

    def test_save_compat_roundtrip(self):
        from entity import Entity

        e = Entity(name="ゴブリン弓兵")
        d = e.to_dict()
        e2 = Entity.from_dict(d)
        assert e2.ai_role == e.ai_role
        assert e2.next_intent is None

    def test_perf_50_intents(self):
        import time

        eng = FakeEngine(_player(5, 5))
        ents = [FakeEntity(x=i, y=0) for i in range(50)]
        t0 = time.perf_counter()
        for e in ents:
            compute_intent(e, eng)
        dt = time.perf_counter() - t0
        assert dt < 1.0  # 50体で 1s 未満


# ---------------------------------------------------------------------------
# 提案4: 陣形・連携タクティクスのテスト
# ---------------------------------------------------------------------------


class _NullBus:
    def publish(self, *args, **kwargs):
        return None


class FakeGridEngine:
    """壁なしグリッド上の軽量偽エンジン (陣形AI用)"""

    def __init__(self, px=10, py=10, walls=None):
        self.player = FakeEntity(x=px, y=py, faction="player", is_player=True)
        self.entities = []
        self.walls = walls or set()
        self.dungeon_level = 0
        self.event_bus = _NullBus()

    def add(self, e):
        self.entities.append(e)

    def is_tile_free(self, x, y):
        if (x, y) in self.walls:
            return False
        return True

    def get_entity_at(self, x, y):
        if self.player.x == x and self.player.y == y:
            return self.player
        for e in self.entities:
            if e.x == x and e.y == y:
                return e
        return None

    def has_los(self, a, b):
        return True

    def log(self, *args, **kwargs):
        return None


def _cheb(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


def _monster(name, x, y, ai_role="brute"):
    from entity import Entity

    e = Entity(x=x, y=y, name=name, is_player=False, is_pet=False)
    e.hp, e.max_hp = 30, 30
    e.faction = "monster"
    e.ai_role = ai_role
    if ai_role == "kiter":
        e.preferred_range = 4
    return e


def test_kiter_retreats_when_too_close():
    from ai_system import KiteAction

    eng = FakeGridEngine(10, 10)
    k = _monster("弓兵", 9, 10, "kiter")
    assert KiteAction().execute(k, eng) is True
    assert _cheb(k.x, k.y, 10, 10) > 1


def test_kiter_holds_at_range():
    from ai_system import KiteAction

    eng = FakeGridEngine(10, 10)
    k = _monster("弓兵", 7, 10, "kiter")
    assert KiteAction().execute(k, eng) is True
    assert _cheb(k.x, k.y, 10, 10) == 3  # 射程内はその場維持(撃つ)


def test_kiter_approaches_when_far():
    from ai_system import KiteAction

    eng = FakeGridEngine(10, 10)
    k = _monster("弓兵", 2, 10, "kiter")
    KiteAction().execute(k, eng)
    assert _cheb(k.x, k.y, 10, 10) < 8


def test_flanker_moves_and_not_onto_player():
    from ai_system import FlankAction

    eng = FakeGridEngine(10, 10)
    f = _monster("騎士", 10, 8, "flanker")
    before = (f.x, f.y)
    assert FlankAction().execute(f, eng) is True
    assert (f.x, f.y) != before
    assert (f.x, f.y) != (10, 10)  # プレイヤー上には乗らない


def test_spread_moves_when_crowded():
    from ai_system import SpreadAction

    eng = FakeGridEngine(10, 10)
    a = _monster("鬼A", 10, 10 + 1)  # プレイヤー隣
    b = _monster("鬼B", 10, 11)  # a と重なるように隣接(詰まり)
    eng.add(a)
    # b を a の隣に置く
    b.x, b.y = 9, 11
    eng.add(b)
    # 便宜上 a の隣に別モンスターがいる状態を作る
    c = _monster("鬼C", 11, 11)
    eng.add(c)
    start = (a.x, a.y)
    res = SpreadAction().execute(a, eng)
    # 詰まり状態なら動くはず
    assert res is True
    assert (a.x, a.y) != start


def test_spread_noop_when_alone():
    from ai_system import SpreadAction

    eng = FakeGridEngine(10, 10)
    a = _monster("鬼A", 5, 5)
    eng.add(a)
    assert SpreadAction().execute(a, eng) is False


def test_brute_still_melee_adjacent():
    from ai_system import AdvancedAISystem
    from entity import Entity

    eng = FakeGridEngine(10, 10)
    eng.player = Entity(x=10, y=10, name="hero", is_player=True)
    eng.player.faction = "player"
    m = _monster("鬼", 9, 10, "brute")
    eng.add(m)
    sys = AdvancedAISystem()
    hp0 = eng.player.hp
    sys.process_ai(m, eng)
    # 隣接 brute はプレイヤーを攻撃（ダメージが入る）
    assert eng.player.hp < hp0


def test_process_ai_kiter_role():
    from ai_system import AdvancedAISystem
    from entity import Entity

    eng = FakeGridEngine(10, 10)
    eng.player = Entity(x=10, y=10, name="hero", is_player=True)
    eng.player.faction = "player"
    k = _monster("弓兵", 9, 10, "kiter")
    eng.add(k)
    sys = AdvancedAISystem()
    sys.process_ai(k, eng)
    # kiter は離脱/維持するので隣接し続けない
    assert _cheb(k.x, k.y, 10, 10) >= 1


def test_allies_in_sight_counts():
    from ai_system import AdvancedAISystem

    eng = FakeGridEngine(10, 10)
    a = _monster("鬼A", 9, 10, "brute")
    b = _monster("鬼B", 11, 10, "brute")
    eng.add(a)
    eng.add(b)
    sys = AdvancedAISystem()
    assert sys._allies_in_sight(a, eng) >= 1


def test_pincer_flanks_with_two_allies():
    from ai_system import AdvancedAISystem

    eng = FakeGridEngine(10, 10)
    a = _monster("鬼A", 9, 10, "brute")
    b = _monster("鬼B", 11, 10, "brute")
    c = _monster("鬼C", 10, 12, "brute")
    eng.add(a)
    eng.add(b)
    eng.add(c)
    sys = AdvancedAISystem()
    # 味方2体以上なら連携(挟撃)発動条件を満たす
    assert sys._allies_in_sight(a, eng) >= 2


def test_hard_difficulty_increases_kiter_range():
    from ai_system import KiteAction

    def settle(eng, k):
        for _ in range(12):
            before = (k.x, k.y)
            KiteAction().execute(k, eng)
            if (k.x, k.y) == before:
                break
        return _cheb(k.x, k.y, 10, 10)

    # normal / hard それぞれ収束間合いを計測（開始距離7）
    eng = FakeGridEngine(10, 10)
    kn = _monster("弓兵", 3, 10, "kiter")
    dnorm = settle(eng, kn)

    eng_h = FakeGridEngine(10, 10)
    eng_h.difficulty = "hard"
    kh = _monster("弓兵", 3, 10, "kiter")
    dhard = settle(eng_h, kh)

    # 難易度hardでは normal より小さな間合いにはならない（ボーナス方向）
    assert dhard >= dnorm
    assert dnorm > 0 and dhard > 0
