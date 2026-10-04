"""Step 10: ゲーム状態機械。

`GameState` は宣言されていたが、代入する場所が無かった。遷移表が閉じていて
未登録の遷移が例外になることを確認するのが Step 10 の DoD。
"""

from __future__ import annotations

import pytest
from naRou.engine.game_state import ALLOWED_TRANSITIONS, GameStateMachine

from tests.helpers.non_vacuity import assert_distinguishes


def _machine() -> GameStateMachine:
    return GameStateMachine("playing")


def _assert_rejected(sm: GameStateMachine, to: str) -> None:
    """`to` への遷移が例外になり、状態と履歴が汚れないことを確認する。"""
    before, history_before = sm.current, list(sm.history)
    with pytest.raises(ValueError, match="illegal game state transition"):
        sm.transition(to)
    assert sm.current == before
    assert sm.history == history_before


def test_unregistered_transition_raises():
    """未登録の遷移は黙って無視されず、必ず例外になる。"""
    sm = _machine()
    _assert_rejected(sm, "main_menu")


def test_unregistered_transition_is_detectable_not_vacuous():
    """同じ検査が「許可された遷移」を通ることを証明する。

    `_assert_allowed` は許可表 consult だけを見る。上のテストと同じ「許可表を
    そのまま返す」実装なら、good の `playing -> game_over` を通し、
    bad の `game_over -> victory` で必ず落ちる。機構で示さないと、上のテストは
    「全部を例外にする」実装でも緑になる。
    """
    def _assert_allowed(sm: GameStateMachine, to: str) -> None:
        assert sm.can_transition(to), f"{sm.current} -> {to} should be allowed"

    sm = _machine()
    assert_distinguishes(
        lambda s: _assert_allowed(s, "game_over"),
        sm,
        _terminal_machine(),
        label="the allowed table distinguishes legal from illegal transitions",
    )


def _terminal_machine() -> GameStateMachine:
    """`game_over` まで進んだ機械。`victory` へは遷移できない。"""
    sm = _machine()
    sm.transition("game_over")
    return sm


def test_allowed_table_matches_the_documented_edges():
    """許可表が計画書の形から勝手に増えていないことを固定する。"""
    assert dict(ALLOWED_TRANSITIONS) == {
        "playing": frozenset({"game_over", "victory"}),
        "game_over": frozenset({"title"}),
        "victory": frozenset({"title"}),
    }


def test_rejects_unknown_initial_state():
    """初期状態も許可表に無ければ受け付けない。"""
    def _build(state: str) -> None:
        assert GameStateMachine(state).current == state

    assert_distinguishes(
        _build,
        "playing",
        "main_menu",
        label="unknown initial state is rejected",
    )


# --- Step 11: playing から終局へ到達できることと履歴の記録 ---


def test_playing_to_game_over_is_allowed():
    """`playing -> game_over` は許可され、状態と履歴の両方が動く。"""
    sm = _machine()
    sm.transition("game_over")

    assert sm.current == "game_over"
    assert sm.is_terminal is True
    assert sm.is_playing is False
    assert [h[:2] for h in sm.history] == [("playing", "game_over")]


def test_victory_is_reachable_from_playing():
    """`playing -> victory` も許可される。勝利条件が Step 19 で使われる入口。"""
    sm = _machine()
    sm.transition("victory")

    assert sm.current == "victory"
    assert sm.is_terminal is True


def test_history_records_timestamps():
    """履歴は (from, to, 時刻) の列で、時刻は単調増加する。"""
    sm = _machine()
    sm.transition("game_over")
    sm.transition("title")

    assert len(sm.history) == 2
    first, second = sm.history
    assert (first[0], first[1]) == ("playing", "game_over")
    assert (second[0], second[1]) == ("game_over", "title")
    assert first[2] <= second[2], "history timestamps must not go backwards"


def test_game_over_is_a_dead_end_except_for_title():
    """終局から別の終局へは遷移できない（死亡と勝利が同時に起きない）。"""
    _assert_rejected(_terminal_machine(), "victory")
    _assert_rejected(_terminal_machine(), "playing")


def test_history_is_not_vacuous_for_the_victory_edge():
    """`victory` が許可表から消えると緑が壊れることの証明。

    `_assert_reachable` は `can_transition` の結果だけを，DISTINGUISHES の bad を
    「table を 1 削った機械」に差し替えることで機構を示す。表が全部許可する
    実装でも bad は落ちないため、このテストは空振りしない。
    """
    def _assert_reachable(sm: GameStateMachine, to: str) -> None:
        assert sm.can_transition(to), f"{sm.current} -> {to} must be reachable"

    def _table_without_victory() -> GameStateMachine:
        """`playing` から到達できる終局が `game_over` だけの（表から victory を除いたもの）。"""
        sm = _machine()
        sm.transition("game_over")
        return sm

    assert_distinguishes(
        lambda s: _assert_reachable(s, "victory"),
        _machine(),
        _table_without_victory(),
        label="victory edge is present in the allowed table",
    )
