"""difficulty.py - 難易度管理（Step 32 / Step 34）。

config の difficulty_presets から乗数を読み込み、戦闘ダメージ等に適用する。
"""

from __future__ import annotations

from typing import ClassVar


class DifficultyManager:
    """難易度プリセットに基づく乗数を提供する。"""

    _DEFAULTS: ClassVar[dict[str, dict[str, float]]] = {
        "easy": {"player_damage_taken": 0.5, "enemy_hp": 0.8, "player_regen": 1.5},
        "normal": {"player_damage_taken": 1.0, "enemy_hp": 1.0, "player_regen": 1.0},
        "hard": {"player_damage_taken": 1.5, "enemy_hp": 1.2, "player_regen": 0.8},
    }

    def __init__(self, difficulty: str | None = None) -> None:
        if difficulty is None:
            try:
                from config import get_config

                difficulty = get_config("game.difficulty")
            except ImportError:
                # TODO: handle exception properly
                difficulty = None
        if difficulty not in self._DEFAULTS:
            difficulty = "normal"
        self.difficulty = difficulty
        self.multipliers = self._load_multipliers(difficulty)

    def _load_multipliers(self, difficulty: str) -> dict[str, float]:
        try:
            from config import get_config

            preset = get_config(f"game.difficulty_presets.{difficulty}")
            if isinstance(preset, dict):
                return {
                    "player_damage_taken": float(
                        preset.get("player_damage_taken", 1.0)
                    ),
                    "enemy_hp": float(preset.get("enemy_hp", 1.0)),
                    "player_regen": float(preset.get("player_regen", 1.0)),
                }
        except ImportError:
            # TODO: handle exception properly
            pass
        return dict(self._DEFAULTS.get(difficulty, self._DEFAULTS["normal"]))

    def player_damage_taken(self, raw_damage: float) -> float:
        """プレイヤーが受けるダメージを難易度で補正（最小1）。"""
        return max(1.0, raw_damage * self.multipliers["player_damage_taken"])

    def enemy_hp(self, base_hp: float) -> float:
        return base_hp * self.multipliers["enemy_hp"]

    def player_regen(self, base_regen: float) -> float:
        return base_regen * self.multipliers["player_regen"]
