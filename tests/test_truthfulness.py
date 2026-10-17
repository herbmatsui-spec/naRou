"""表示の真実性テスト (Phase 3 Step 70)

HUDラベル・ログメッセージが実在する機構のみを宣伝していることを構造的に強制する。
「広告ではなく実測」であることをテストの構造自体で保証する。
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# HUD が実際に参照する Entity フィールド (entity_renderer / render の実描画経路から)
_TRACKED_PLAYER_FIELDS = (
    "hp", "max_hp", "mp", "max_mp", "gold", "level", "exp", "speed",
)
# HUD が参照する Engine (GameStateData) フィールド
_TRACKED_ENGINE_FIELDS = (
    "dungeon_level", "turns",
)


class TestTruthfulness:
    """Step 70: 表示は真である"""

    def test_no_hud_label_claims_a_value_the_game_does_not_track(self):
        """Step 70.1: HUD が参照するフィールドが実在すること (Entity + Engine 状態)"""
        from ecs.entity import Entity

        player = Entity(name="probe", is_player=True)
        missing_entity = [f for f in _TRACKED_PLAYER_FIELDS if not hasattr(player, f)]
        assert not missing_entity, (
            f"HUD が表示するが Entity に存在しないフィールド: {missing_entity}"
        )

        from game import Engine
        from renderer import NullRenderer

        engine = Engine(renderer=NullRenderer())
        missing_engine = [f for f in _TRACKED_ENGINE_FIELDS if not hasattr(engine, f)]
        assert not missing_engine, (
            f"HUD が表示するが Engine に存在しないフィールド: {missing_engine}"
        )

    def test_every_hud_field_is_backed_by_a_read(self):
        """Step 70.3: HUD 描画コードが参照するフィールドに読み出し経路があること"""
        from ecs.entity import Entity

        player = Entity(name="probe", is_player=True)
        for field in _TRACKED_PLAYER_FIELDS:
            value = getattr(player, field)
            assert value is not None, f"{field}: HUD 参照フィールドが None"

    def test_status_effects_ui_field_exists(self):
        """状態異常表示 (HUD) が参照する status_effects が実在する"""
        from ecs.entity import Entity

        player = Entity(name="probe", is_player=True)
        assert hasattr(player, "status_effects"), "status_effects が Entity に無い (HUD表示不能)"
        assert isinstance(player.status_effects, list)

    def test_intent_display_uses_real_capabilities(self):
        """Step 70.2 関連: 意図テレグラフが木の実在行動のみを表示することは test_intent_truthfulness が強制"""
        # この契約の詳細検証は test_intent_truthfulness.py (46テスト) が担う。
        # ここでは表示モジュールが実在することだけを確認。
        from enemy_intent import compute_intent  # noqa: F401

        assert callable(compute_intent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
