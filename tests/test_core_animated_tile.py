"""core/animated_tile のテスト。

アニメーションタイル（水・溶岩・松明・ポータルなど）の生成、
フレーム取得、レジストリ登録をカバーする。
正常系・異常系・境界値を含め、パブリック API を網羅的にテストする。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.animated_tile import (
    ANIMATED_TILES,
    AnimatedTile,
    get_animated_tile,
    register_animated_tiles,
)


class TestAnimatedTile:
    """AnimatedTile クラスのテスト。"""

    def test_create_normal(self):
        """通常の初期化ができること。"""
        tile = AnimatedTile(tile_ids=["A", "B", "C"], fps=10, loop=True)
        assert tile.tile_ids == ["A", "B", "C"]
        assert tile.fps == 10
        assert tile.loop is True

    def test_loop_defaults_to_true(self):
        """loop は省略時に True であること。"""
        tile = AnimatedTile(tile_ids=["X"], fps=1)
        assert tile.loop is True

    def test_empty_tile_ids_raises(self):
        """tile_ids が空のとき ValueError を送出すること（異常系）。"""
        with pytest.raises(ValueError, match="at least one tile_id"):
            AnimatedTile(tile_ids=[], fps=5)

    def test_non_positive_fps_raises(self):
        """fps が 0 または負のとき ValueError を送出すること（異常系）。"""
        with pytest.raises(ValueError, match="fps must be positive"):
            AnimatedTile(tile_ids=["A"], fps=0)
        with pytest.raises(ValueError, match="fps must be positive"):
            AnimatedTile(tile_ids=["A"], fps=-3)

    def test_get_frame_wraps_around(self):
        """get_frame がインデックスを周回させて返すこと。"""
        tile = AnimatedTile(tile_ids=["A", "B", "C"], fps=5)
        assert tile.get_frame(0) == "A"
        assert tile.get_frame(1) == "B"
        assert tile.get_frame(2) == "C"
        assert tile.get_frame(3) == "A"  # 周回
        assert tile.get_frame(4) == "B"
        assert tile.get_frame(5) == "C"

    def test_get_frame_single_tile(self):
        """1 フレームの場合は常に同じタイルを返すこと（境界値）。"""
        tile = AnimatedTile(tile_ids=["ONLY"], fps=5)
        assert tile.get_frame(0) == "ONLY"
        assert tile.get_frame(100) == "ONLY"

    def test_get_frame_at_time(self):
        """get_frame_at_time が秒からフレームインデックスを算出すること。"""
        tile = AnimatedTile(tile_ids=["A", "B", "C", "D"], fps=4)
        # fps=4 なので 1 フレーム = 0.25 秒
        assert tile.get_frame_at_time(0.0) == "A"      # frame_index = 0
        assert tile.get_frame_at_time(0.25) == "B"     # frame_index = 1
        assert tile.get_frame_at_time(0.5) == "C"      # frame_index = 2
        assert tile.get_frame_at_time(1.0) == "A"      # frame_index = 4 -> 0

    def test_frame_count(self):
        """frame_count がタイル数を返すこと。"""
        tile = AnimatedTile(tile_ids=["A", "B", "C"], fps=5)
        assert tile.frame_count == 3

    def test_frame_duration(self):
        """frame_duration が 1/fps を返すこと。"""
        tile = AnimatedTile(tile_ids=["A"], fps=10)
        assert tile.frame_duration == 0.1


class TestAnimatedTilesRegistry:
    """ANIMATED_TILES 定義と get_animated_tile のテスト。"""

    def test_predefined_tiles_exist(self):
        """水・溶岩・松明・魔法ポータルが定義されていること。"""
        assert "water" in ANIMATED_TILES
        assert "lava" in ANIMATED_TILES
        assert "torch" in ANIMATED_TILES
        assert "magic_portal" in ANIMATED_TILES

    def test_get_animated_tile_known(self):
        """既知の名前で AnimatedTile を取得できること。"""
        tile = get_animated_tile("water")
        assert isinstance(tile, AnimatedTile)
        assert tile.fps == 5
        assert len(tile.tile_ids) == 3

    def test_get_animated_tile_unknown_returns_none(self):
        """未知の名前では None を返すこと。"""
        assert get_animated_tile("nonexistent") is None


class TestRegisterAnimatedTiles:
    """register_animated_tiles のテスト。"""

    def test_registers_when_feature_flag_enabled(self):
        """ENABLE_TINY_ROGUE_GFX が有効時にタイルアトラスへ登録すること。"""
        tile_atlas = SimpleNamespace()
        with patch("feature_flags.is_enabled", return_value=True):
            register_animated_tiles(tile_atlas)
        assert hasattr(tile_atlas, "animated_tiles")
        assert "water" in tile_atlas.animated_tiles
        assert "lava" in tile_atlas.animated_tiles

    def test_skips_when_feature_flag_disabled(self):
        """フラグが無効時は登録しないこと。"""
        tile_atlas = SimpleNamespace()
        with patch("feature_flags.is_enabled", return_value=False):
            register_animated_tiles(tile_atlas)
        assert not hasattr(tile_atlas, "animated_tiles")

    def test_handles_import_error_gracefully(self):
        """feature_flags のインポートに失敗しても登録にフォールスルーすること。"""
        import sys

        tile_atlas = SimpleNamespace()
        # sys.modules にキャッシュ済みだと __import__ が呼ばれないため除去する
        sys.modules.pop("feature_flags", None)

        def fake_import(name, *args, **kwargs):
            if name == "feature_flags":
                raise ImportError("no feature_flags")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            register_animated_tiles(tile_atlas)
        # インポート失敗時はフラグチェックをスキップして登録を行う
        assert hasattr(tile_atlas, "animated_tiles")
        assert "water" in tile_atlas.animated_tiles
