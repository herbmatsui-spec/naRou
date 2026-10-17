"""Step 45: アクセシビリティ設定の単体テスト。"""

from __future__ import annotations

from core.accessibility import detect_os_a11y, get_active_tokens, load_design_tokens
from core.difficulty import DifficultyManager


def test_load_design_tokens_variants():
    for variant in ("none", "deutan", "protan", "tritan"):
        tokens = load_design_tokens(variant)
        assert isinstance(tokens, dict)
        assert "color" in tokens


def test_get_active_tokens_default():
    tokens = get_active_tokens()
    assert isinstance(tokens, dict)


def test_color_vision_env_override(monkeypatch):
    monkeypatch.setenv("COLOR_VISION", "deutan")
    tokens = load_design_tokens("none")
    assert "color" in tokens


def test_detect_os_a11y_stub():
    assert detect_os_a11y() == "none"


def test_difficulty_manager_presets():
    easy = DifficultyManager("easy")
    assert easy.player_damage_taken(10) == 5.0
    normal = DifficultyManager("normal")
    assert normal.player_damage_taken(10) == 10.0
    hard = DifficultyManager("hard")
    assert hard.player_damage_taken(10) == 15.0


def test_difficulty_invalid_falls_back_to_normal():
    dm = DifficultyManager("bogus")
    assert dm.difficulty == "normal"
    assert dm.player_damage_taken(10) == 10.0
