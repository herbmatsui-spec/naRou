"""core/difficulty.py (DifficultyManager) の単体テスト。

正常系・異常系・境界値をカバーし、難易度乗数の動作を検証する。
"""

from __future__ import annotations

import pytest

from core.difficulty import DifficultyManager


class TestInitialization:
    """DifficultyManager の初期化をテストする。"""

    @pytest.mark.parametrize(
        "difficulty,expected",
        [
            (
                "easy",
                {"player_damage_taken": 0.5, "enemy_hp": 0.8, "player_regen": 1.2},
            ),
            (
                "normal",
                {"player_damage_taken": 1.0, "enemy_hp": 1.0, "player_regen": 1.0},
            ),
            (
                "hard",
                {"player_damage_taken": 1.5, "enemy_hp": 1.2, "player_regen": 0.8},
            ),
        ],
    )
    def test_explicit_difficulty_uses_code_defaults(self, difficulty, expected):
        """明示指定時はコード内基準プリセット _DEFAULTS を使う。"""
        dm = DifficultyManager(difficulty)
        assert dm.difficulty == difficulty
        assert dm.multipliers == expected

    def test_invalid_difficulty_falls_back_to_normal(self):
        """不正な難易度文字列は 'normal' にフォールバックする。"""
        dm = DifficultyManager("bogus")
        assert dm.difficulty == "normal"
        assert dm.multipliers == {
            "player_damage_taken": 1.0,
            "enemy_hp": 1.0,
            "player_regen": 1.0,
        }

    def test_none_reads_difficulty_from_config(self):
        """difficulty=None なら config の game.difficulty を読む。"""
        dm = DifficultyManager()
        assert dm.difficulty == "normal"


class TestConfigDrivenPath:
    """config 読み込み経路（_load_multipliers の dict 分岐）をテストする。"""

    def test_config_preset_dict_is_applied(self, monkeypatch):
        """config の difficulty_presets が dict ならその値を乗数に使う。"""

        def fake_get_config(key, default=None):
            table = {
                "game.difficulty": "hard",
                "game.difficulty_presets.hard": {
                    "player_damage_taken": 2.0,
                    "enemy_hp": 1.5,
                    "player_regen": 0.5,
                },
            }
            return table.get(key, default)

        monkeypatch.setattr("config.get_config", fake_get_config)
        dm = DifficultyManager()  # None -> config から "hard" -> _load_multipliers
        assert dm.difficulty == "hard"
        assert dm.multipliers == {
            "player_damage_taken": 2.0,
            "enemy_hp": 1.5,
            "player_regen": 0.5,
        }

    def test_config_preset_non_dict_falls_back_to_defaults(self, monkeypatch):
        """config の値が dict でない場合は _DEFAULTS にフォールバックする。"""

        def fake_get_config(key, default=None):
            if key == "game.difficulty":
                return "hard"
            if key == "game.difficulty_presets.hard":
                return "not_a_dict"
            return default

        monkeypatch.setattr("config.get_config", fake_get_config)
        dm = DifficultyManager()  # None -> config から "hard" -> 非 dict -> デフォルト
        assert dm.difficulty == "hard"
        assert dm.multipliers == {
            "player_damage_taken": 1.5,
            "enemy_hp": 1.2,
            "player_regen": 0.8,
        }


class TestDamageAndStats:
    """ダメージ・HP・再生計算メソッドをテストする。"""

    def test_player_damage_taken_applies_multiplier(self):
        dm = DifficultyManager("hard")
        assert dm.player_damage_taken(10.0) == 15.0

    def test_player_damage_taken_minimum_one(self):
        """raw_damage が 0 以下でも最小 1.0 を返す（境界値）。"""
        dm = DifficultyManager("normal")
        assert dm.player_damage_taken(0.0) == 1.0
        assert dm.player_damage_taken(0.5) == 1.0

    def test_enemy_hp_applies_multiplier(self):
        dm = DifficultyManager("easy")
        assert dm.enemy_hp(100.0) == 80.0

    def test_player_regen_applies_multiplier(self):
        dm = DifficultyManager("hard")
        assert dm.player_regen(10.0) == 8.0
