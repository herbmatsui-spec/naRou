"""core/tiny_rogue_tiles モジュールのテスト。

Tiny Rogue タイルIDマッピングユーティリティの正常系・異常系・境界値をカバーする。
feature_flags の ENABLE_TINY_ROGUE_GFX フラグをモックして制御する。
"""

from __future__ import annotations

from unittest.mock import patch

from core import tiny_rogue_tiles


def _reset_cache() -> None:
    """モジュールレベルのマッピングキャッシュをリセットする。"""
    tiny_rogue_tiles._MAPPINGS_CACHE = None  # noqa: SLF001


def test_load_tiny_rogue_mappings_returns_dict():
    """YAML マッピングが辞書として読み込まれることを確認する。"""
    _reset_cache()
    mappings = tiny_rogue_tiles.load_tiny_rogue_mappings()
    assert isinstance(mappings, dict)
    assert "standard_to_tiny_rogue" in mappings
    assert "items" in mappings
    assert "decorations" in mappings
    assert "effects" in mappings
    assert "ui" in mappings
    assert "terrain" in mappings


def test_load_tiny_rogue_mappings_cached():
    """2回目以降はキャッシュが返されることを確認する。"""
    _reset_cache()
    first = tiny_rogue_tiles.load_tiny_rogue_mappings()
    second = tiny_rogue_tiles.load_tiny_rogue_mappings()
    assert first is second


# --- get_tiny_rogue_tile_id --------------------------------------------------

def test_get_tiny_rogue_tile_id_mapped_flag_on():
    """フラグ有効時に標準タイルIDがTiny Rogue IDに変換される。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_tiny_rogue_tile_id("TILE_FLOOR") == "TR_FLOOR_01"
        assert tiny_rogue_tiles.get_tiny_rogue_tile_id("TILE_WALL") == "TR_WALL_01"


def test_get_tiny_rogue_tile_id_unknown_returns_standard():
    """マッピングにないIDは標準IDをそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_tiny_rogue_tile_id("TILE_UNKNOWN") == "TILE_UNKNOWN"


def test_get_tiny_rogue_tile_id_fallback():
    """マッピングにないIDにフォールバック値が指定された場合はそれを返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert (
            tiny_rogue_tiles.get_tiny_rogue_tile_id("TILE_UNKNOWN", fallback="FALLBACK")
            == "FALLBACK"
        )


def test_get_tiny_rogue_tile_id_flag_off_returns_standard():
    """フラグ無効時は標準IDをそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_tiny_rogue_tile_id("TILE_FLOOR") == "TILE_FLOOR"


# --- get_item_tile_id --------------------------------------------------------

def test_get_item_tile_id_known_category():
    """既知のアイテムカテゴリは対応するTiny Rogue IDを返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_item_tile_id("potion") == "TR_ITEM_01"
        assert tiny_rogue_tiles.get_item_tile_id("weapon") == "TR_ITEM_04"


def test_get_item_tile_id_unknown_returns_default():
    """未知のカテゴリはデフォルトの TR_ITEM_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_item_tile_id("unknown_category") == "TR_ITEM_12"


def test_get_item_tile_id_flag_off():
    """フラグ無効時は TR_ITEM_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_item_tile_id("potion") == "TR_ITEM_12"


# --- get_decoration_tile_id --------------------------------------------------

def test_get_decoration_tile_id_known():
    """既知の装飾タイプは対応するTiny Rogue IDを返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_decoration_tile_id("torch") == "TR_DECOR_01"
        assert tiny_rogue_tiles.get_decoration_tile_id("chest") == "TR_DECOR_02"


def test_get_decoration_tile_id_unknown_returns_input():
    """未知の装飾タイプは入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_decoration_tile_id("unknown_decor") == "unknown_decor"


def test_get_decoration_tile_id_flag_off():
    """フラグ無効時は入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_decoration_tile_id("torch") == "torch"


# --- get_effect_tile_id ------------------------------------------------------

def test_get_effect_tile_id_known():
    """既知のエフェクトタイプは対応するTiny Rogue IDを返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_effect_tile_id("fire") == "TR_EFFECT_02"
        assert tiny_rogue_tiles.get_effect_tile_id("heal") == "TR_EFFECT_06"


def test_get_effect_tile_id_falls_back_to_decorations():
    """エフェクトになくデコレーションにある場合はデコレーション側を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        # "blood" は effects にはなく decorations にある
        assert tiny_rogue_tiles.get_effect_tile_id("blood") == "TR_DECOR_10"


def test_get_effect_tile_id_unknown_returns_input():
    """どちらにもない場合は入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_effect_tile_id("unknown_effect") == "unknown_effect"


def test_get_effect_tile_id_flag_off():
    """フラグ無効時は入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_effect_tile_id("fire") == "fire"


# --- get_ui_tile_id ----------------------------------------------------------

def test_get_ui_tile_id_known():
    """既知のUIタイプは対応するTiny Rogue IDを返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_ui_tile_id("heart") == "TR_UI_01"
        assert tiny_rogue_tiles.get_ui_tile_id("coin") == "TR_UI_07"


def test_get_ui_tile_id_unknown_returns_input():
    """未知のUIタイプは入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_ui_tile_id("unknown_ui") == "unknown_ui"


def test_get_ui_tile_id_flag_off():
    """フラグ無効時は入力値をそのまま返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_ui_tile_id("heart") == "heart"


# --- get_terrain_config ------------------------------------------------------

def test_get_terrain_config_returns_dict():
    """terrain 設定が辞書として返される。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        config = tiny_rogue_tiles.get_terrain_config()
        assert isinstance(config, dict)
        assert config.get("floor_base") == "TR_FLOOR"
        assert config.get("wall_base") == "TR_WALL"


# --- get_dungeon_tile_id -----------------------------------------------------

def test_get_dungeon_tile_id_floor():
    """ダンジョンタイプ "floor" は TR_FLOOR_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("floor") == "TR_FLOOR_01"


def test_get_dungeon_tile_id_wall():
    """ダンジョンタイプ "wall" は TR_WALL_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("wall") == "TR_WALL_01"


def test_get_dungeon_tile_id_stairs_up():
    """ダンジョンタイプ "stairs_up" は TR_DECOR_08 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("stairs_up") == "TR_DECOR_08"


def test_get_dungeon_tile_id_stairs_down():
    """ダンジョンタイプ "stairs_down" は TR_DECOR_07 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("stairs_down") == "TR_DECOR_07"


def test_get_dungeon_tile_id_water():
    """ダンジョンタイプ "water" は TR_EFFECT_02 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("water") == "TR_EFFECT_02"


def test_get_dungeon_tile_id_trap():
    """ダンジョンタイプ "trap" は TR_DECOR_09 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("trap") == "TR_DECOR_09"


def test_get_dungeon_tile_id_wall_variant():
    """ダンジョンタイプ "wall_variant" は TR_WALL_VAR_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("wall_variant") == "TR_WALL_VAR_01"


def test_get_dungeon_tile_id_unknown_type():
    """未知のタイプは標準IDをそのまま返す（マッピングにない場合）。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_dungeon_tile_id("lava") == "lava"


# --- get_extra_floor_id ------------------------------------------------------

def test_get_extra_floor_id_variant_0():
    """バリアント0 は TR_FLOOR_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_floor_id(0) == "TR_FLOOR_01"


def test_get_extra_floor_id_variant_11():
    """バリアント11 は TR_FLOOR_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_floor_id(11) == "TR_FLOOR_12"


def test_get_extra_floor_id_default():
    """デフォルト引数は TR_FLOOR_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_floor_id() == "TR_FLOOR_01"


def test_get_extra_floor_id_negative_clamped():
    """負のバリアントは0にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_floor_id(-1) == "TR_FLOOR_01"
        assert tiny_rogue_tiles.get_extra_floor_id(-999) == "TR_FLOOR_01"


def test_get_extra_floor_id_overflow_clamped():
    """11を超えるバリアントは11にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_floor_id(12) == "TR_FLOOR_12"
        assert tiny_rogue_tiles.get_extra_floor_id(999) == "TR_FLOOR_12"


def test_get_extra_floor_id_flag_off():
    """フラグ無効時は TILE_FLOOR を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_extra_floor_id(5) == "TILE_FLOOR"


# --- get_extra_wall_id -------------------------------------------------------

def test_get_extra_wall_id_variant_0():
    """バリアント0 は TR_WALL_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_wall_id(0) == "TR_WALL_01"


def test_get_extra_wall_id_variant_11():
    """バリアント11 は TR_WALL_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_wall_id(11) == "TR_WALL_12"


def test_get_extra_wall_id_negative_clamped():
    """負のバリアントは0にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_wall_id(-5) == "TR_WALL_01"


def test_get_extra_wall_id_overflow_clamped():
    """11を超えるバリアントは11にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_wall_id(100) == "TR_WALL_12"


def test_get_extra_wall_id_flag_off():
    """フラグ無効時は TILE_WALL を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_extra_wall_id(5) == "TILE_WALL"


# --- get_extra_decor_id ------------------------------------------------------

def test_get_extra_decor_id_variant_0():
    """バリアント0 は TR_DECOR_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_decor_id(0) == "TR_DECOR_01"


def test_get_extra_decor_id_variant_11():
    """バリアント11 は TR_DECOR_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_decor_id(11) == "TR_DECOR_12"


def test_get_extra_decor_id_negative_clamped():
    """負のバリアントは0にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_decor_id(-1) == "TR_DECOR_01"


def test_get_extra_decor_id_overflow_clamped():
    """11を超えるバリアントは11にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_extra_decor_id(999) == "TR_DECOR_12"


def test_get_extra_decor_id_flag_off():
    """フラグ無効時は DECOR_TORCH を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_extra_decor_id(5) == "DECOR_TORCH"


# --- get_monster_tile_id -----------------------------------------------------

def test_get_monster_tile_id_slime():
    """slime は base_idx=0 なので TR_MONSTER_01 (variant=0) を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("slime", 0) == "TR_MONSTER_01"


def test_get_monster_tile_id_snail():
    """snail は base_idx=1 なので variant=0 で TR_MONSTER_04 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("snail", 0) == "TR_MONSTER_04"


def test_get_monster_tile_id_goblin():
    """goblin は base_idx=0 なので variant=0 で TR_MONSTER_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("goblin", 0) == "TR_MONSTER_01"


def test_get_monster_tile_id_unknown_type_defaults_to_slime():
    """未知のモンスタータイプは base_idx=0 (slime) として扱われる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("unknown_monster", 0) == "TR_MONSTER_01"


def test_get_monster_tile_id_variant_max():
    """バリアント11 は base_idx*3 + 11 + 1 のインデックスになる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        # slime: base_idx=0, variant=11 → 0*3+11+1 = 12 → TR_MONSTER_12
        assert tiny_rogue_tiles.get_monster_tile_id("slime", 11) == "TR_MONSTER_12"


def test_get_monster_tile_id_variant_negative_clamped():
    """負のバリアントは0にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("slime", -1) == "TR_MONSTER_01"


def test_get_monster_tile_id_variant_overflow_clamped():
    """11を超えるバリアントは11にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_monster_tile_id("slime", 100) == "TR_MONSTER_12"


def test_get_monster_tile_id_flag_off():
    """フラグ無効時は ENEMY_<TYPE_UPPER> を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_monster_tile_id("slime") == "ENEMY_SLIME"
        assert tiny_rogue_tiles.get_monster_tile_id("goblin") == "ENEMY_GOBLIN"


# --- get_player_tile_id ------------------------------------------------------

def test_get_player_tile_id_variant_0():
    """バリアント0 は TR_PLAYER_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_player_tile_id(0) == "TR_PLAYER_01"


def test_get_player_tile_id_variant_11():
    """バリアント11 は TR_PLAYER_12 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_player_tile_id(11) == "TR_PLAYER_12"


def test_get_player_tile_id_default():
    """デフォルト引数は TR_PLAYER_01 を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_player_tile_id() == "TR_PLAYER_01"


def test_get_player_tile_id_negative_clamped():
    """負のバリアントは0にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_player_tile_id(-5) == "TR_PLAYER_01"


def test_get_player_tile_id_overflow_clamped():
    """11を超えるバリアントは11にクランプされる。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=True):
        assert tiny_rogue_tiles.get_player_tile_id(100) == "TR_PLAYER_12"


def test_get_player_tile_id_flag_off():
    """フラグ無効時は PLAYER を返す。"""
    _reset_cache()
    with patch("feature_flags.is_enabled", return_value=False):
        assert tiny_rogue_tiles.get_player_tile_id(5) == "PLAYER"
