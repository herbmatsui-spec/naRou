"""Step 21: TextRenderer の単体テスト。"""

from __future__ import annotations

import io
import sys

from core.text_renderer import TextRenderer, get_text_action


def test_init_grid():
    tr = TextRenderer(80, 50)
    assert len(tr.chars) == 50
    assert len(tr.chars[0]) == 80


def test_draw_tile():
    tr = TextRenderer(10, 10)
    tr.draw_tile(1, 2, "#", (200, 0, 0))
    assert tr.chars[2][1] == "#"
    assert tr.colors[2][1] == (200, 0, 0)


def test_draw_text():
    tr = TextRenderer(10, 10)
    tr.draw_text(0, 0, "HP", (0, 255, 0))
    assert tr.chars[0][0] == "H"
    assert tr.chars[0][1] == "P"


def test_clear():
    tr = TextRenderer(10, 10)
    tr.draw_tile(1, 2, "#")
    tr.clear()
    assert tr.chars[2][1] == " "
    assert tr.colors[2][1] == (255, 255, 255)


def test_nearest_256():
    tr = TextRenderer(10, 10)
    assert tr._nearest_256(255, 0, 0) == 196


def test_present_contains_escape_and_invert():
    tr = TextRenderer(10, 10)
    tr.draw_tile(0, 0, "@", (200, 0, 0))
    tr.set_cursor(3, 3)
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        tr.present()
    finally:
        sys.stdout = old
    out = buf.getvalue()
    assert "38;5;" in out
    assert "7m" in out


def test_get_text_action_move():
    import builtins

    old_input = builtins.input
    builtins.input = lambda *_: "w"
    try:
        assert get_text_action() == {"move": (0, -1)}
    finally:
        builtins.input = old_input


def test_get_text_action_quit():
    import builtins

    old_input = builtins.input
    builtins.input = lambda *_: "q"
    try:
        assert get_text_action() == {"quit": True}
    finally:
        builtins.input = old_input
