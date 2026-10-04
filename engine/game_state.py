"""GameStateMachine — ゲーム状態遷移の正本 (Step 10)。

`constants.GameState` は状態名を列挙するが、代入する場所が無く、
`GAME_OVER` / `VICTORY` は製品コードで一度も到達しなかった。文字列を
素で持ち回던状態を「遷移できる状態機械」に置き換えるのがこのモジュールの目的。

許可表は閉じて書く。未登録の遷移は `ValueError` に落とす。登録漏れの遷移を黙って
無視すると、その状態は到達しないまま残って事故になる。必ず例外にする。
"""

from __future__ import annotations

import time

PLAYING = "playing"
GAME_OVER = "game_over"
VICTORY = "victory"
TITLE = "title"

#: 許可される遷移。`to` がこの表に無い限り遷移できない。
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PLAYING: frozenset({GAME_OVER, VICTORY}),
    GAME_OVER: frozenset({TITLE}),
    VICTORY: frozenset({TITLE}),
}


class GameStateMachine:
    """現在のゲーム状態と遷移履歴を持つ最小の状態機械。

    `history` は `(from, to, monotonic_timestamp)` の列で、入 state's contract を
    「この run がどう終わったか」を後から答えられる形で残す。
    """

    def __init__(self, current: str = PLAYING) -> None:
        if current not in ALLOWED_TRANSITIONS:
            raise ValueError(f"unknown initial game state: {current!r}")
        self.current: str = current
        self.history: list[tuple[str, str, float]] = []

    @property
    def is_playing(self) -> bool:
        return self.current == PLAYING

    @property
    def is_terminal(self) -> bool:
        """run が終わった状態か (game_over / victory)。"""
        return self.current in (GAME_OVER, VICTORY)

    def can_transition(self, to: str) -> bool:
        return to in ALLOWED_TRANSITIONS.get(self.current, frozenset())

    def transition(self, to: str) -> None:
        """`to` へ遷移する。許可されていない遷移は `ValueError`。"""
        if not self.can_transition(to):
            raise ValueError(f"illegal game state transition: {self.current!r} -> {to!r}")
        self.history.append((self.current, to, time.monotonic()))
        self.current = to


__all__ = [
    "ALLOWED_TRANSITIONS",
    "GAME_OVER",
    "PLAYING",
    "TITLE",
    "VICTORY",
    "GameStateMachine",
]
