"""
ワールドレイヤーシステム (Vertical World Extension)
ステップ13: WorldLayerクラス実装
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from map_engine import GameMap

# T24 案4: tile_palette 値 → FF6風の主床タイル対応表
# (map_renderer._FF6_PALETTE_FLOORS と同じ dungeon_themes.yaml のパレットキーに対応)
_FF6_FLOOR_BY_PALETTE: dict[str, str] = {
    "stone": "TILE_FF6_FLOOR_COBBLE",
    "rust": "TILE_FF6_FLOOR_COBBLE",
    "blue_stone": "TILE_FF6_FLOOR_COBBLE",
    "lava": "TILE_FF6_FLOOR_MOSS",
}

# T24 案4: dungeon_level → テーマ名解決の既定値 (dungeon_themes.yaml の SkillEater 深度帯)
_DEFAULT_THEME_ID = "industrial_ruins"

# T24 案4: dungeon_themes.yaml の depth_range 解析結果キャッシュ
# (Web API からの高頻度参照に備え、プロセス内で 1 度だけ読み込む)
_theme_depth_ranges: list[tuple[int, int, str]] | None = None


def resolve_theme_id_for_level(level: int) -> str:
    """dungeon_level を dungeon_themes.yaml のテーマ名 (theme_id) へ解決する (T24 案4)

    depth_range を持つテーマ (SkillEater 深度帯) のうち階層を含む帯を返す。
    どの帯にも含まれない階層は最も近い深度帯へクランプする。
    """
    global _theme_depth_ranges
    level = max(0, int(level))

    if _theme_depth_ranges is None:
        _theme_depth_ranges = []
        try:
            theme_path = "data/dungeon_themes.yaml"
            if os.path.exists(theme_path):
                with open(theme_path, encoding="utf-8") as f:
                    themes = yaml.safe_load(f) or {}
                for theme_id, data in (themes.get("dungeon_themes") or {}).items():
                    if not isinstance(data, dict):
                        continue
                    depth_range = data.get("depth_range")
                    if isinstance(depth_range, (list, tuple)) and len(depth_range) == 2:
                        _theme_depth_ranges.append(
                            (int(depth_range[0]), int(depth_range[1]), str(theme_id))
                        )
                _theme_depth_ranges.sort()
        except Exception as e:
            logger.exception("Unhandled exception")
            print(f"テーマ深度帯の解析エラー: {e}")
            _theme_depth_ranges = []

    if not _theme_depth_ranges:
        return _DEFAULT_THEME_ID
    for min_depth, max_depth, theme_id in _theme_depth_ranges:
        if min_depth <= level <= max_depth:
            return theme_id
    if level < _theme_depth_ranges[0][0]:
        return _theme_depth_ranges[0][2]
    return _theme_depth_ranges[-1][2]


@dataclass
class WorldLayer:
    """単一のワールド層を表すクラス"""

    zone: str  # surface, underground, otherworld, heaven
    biome: str  # plains, forest, mountains, swamp, desert, tundra, volcanic, ruins
    depth: int  # 0-200 (実際の深度レベル)
    dimension: str  # material, ethereal, void

    # 実行時データ
    game_map: GameMap | None = None
    theme_data: dict[str, Any] = field(default_factory=dict)
    is_loaded: bool = False
    last_accessed: float = field(default_factory=lambda: 0.0)

    def __post_init__(self):
        """初期化後の処理"""
        self.load_theme()

    def load_theme(self) -> None:
        """dungeon_themes.yaml からテーマデータをロード"""
        try:
            theme_path = "data/dungeon_themes.yaml"
            if os.path.exists(theme_path):
                with open(theme_path, encoding="utf-8") as f:
                    themes = yaml.safe_load(f)

                # 新しい垂直ワールド構造からテーマを取得: vertical_world.zone.biome.depth_range.dimension
                vertical_world = themes.get("dungeon_themes", {}).get("vertical_world", {})
                zone_data = vertical_world.get(self.zone, {})
                biome_data = zone_data.get(self.biome, {})

                # 深度レンジを見つける
                depth_data = None
                for depth_key, depth_value in biome_data.items():
                    if depth_key.startswith("depth_"):
                        # depth_0_5, depth_6_10 などの形式をパース
                        try:
                            range_part = depth_key.split("_", 1)[1]  # "0_5" など
                            min_depth, max_depth = map(int, range_part.split("_"))
                            if min_depth <= self.depth <= max_depth:
                                depth_data = depth_value
                                break
                        except ValueError:
                            continue

                if depth_data:
                    self.theme_data = depth_data.get(self.dimension, {})
                else:
                    # フォールバック: デフォルトテーマ
                    self.theme_data = self._get_default_theme()
            else:
                self.theme_data = self._get_default_theme()
        except Exception as e:
            logger.exception("Unhandled exception")
            print(
                f"テーマロードエラー ({self.zone}:{self.biome}:{self.depth}:{self.dimension}): {e}"
            )
            self.theme_data = self._get_default_theme()

    def _get_default_theme(self) -> dict[str, Any]:
        """デフォルトテーマデータを返す"""
        return {
            "theme_id": f"{self.zone}_{self.biome}_{self.depth}_{self.dimension}",
            "name": f"{self.zone} {self.biome} Depth {self.depth} ({self.dimension})",
            "base_layout": "cavern" if self.zone == "underground" else "open",
            "difficulty_modifier": 1.0,
            "enemy_pools": {
                "common": ["slime"],
                "uncommon": ["goblin"],
                "rare": [],
                "unique_boss": None,
            },
            "environmental_hazards": [],
            "special_rooms": [],
            "story_hooks": [],
            "resources": {"common": [], "uncommon": [], "rare": []},
            "gimmicks": [],
        }

    def generate_map(self, width: int, height: int) -> GameMap:
        """テーマに基づいてマップを生成"""
        self.game_map = GameMap(width, height, "dungeon", self.depth)
        self.game_map.world_layer = self  # ワールドレイヤーへの参照を設定

        # テーマベースのマップ生成ロジック
        self._apply_theme_to_map()

        self.is_loaded = True
        self.last_accessed = __import__("time").time()
        return self.game_map

    def _apply_theme_to_map(self) -> None:
        """テーマデータをマップに適用"""
        if not self.game_map:
            return

        # 基本的なダンジョン生成（後でカスタマイズ）
        self.game_map.generate_dungeon(
            max_rooms=20 + (self.depth // 10),  # 深度が増えるほど部屋数増加
            room_min_size=4 + (self.depth // 20),
            room_max_size=10 + (self.depth // 15),
        )

        # テーマ固有の修正を適用
        # TODO: difficulty_modifier をトラップ配置へ適用する
        # ここで難易度に基づくトラップ配置等を行う

        # T11 案4: テーマ別タイルパレット (FF6風テライン) を MapRenderer へ渡す
        # (dungeon_themes.yaml の tile_palette キー: stone / rust / blue_stone / lava)
        self.game_map.tile_palette = self.theme_data.get("tile_palette", "stone")

        # T24 案4: 床タイルのテーマ別variant選択
        # 生成済みの汎用床 (TILE_FLOOR) の一部をテーマ別の FF6 風タイルへ置換する。
        # 残りの床は MapRenderer._resolve_themed_tile が tile_palette 経由で変換し、
        # テーマ床が石畳などに混ざる自然な斑模様になる。
        floor_tile = self._resolve_ff6_floor_tile()
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                if self.game_map.tiles[x][y] != "TILE_FLOOR":
                    continue
                # 位置ハッシュで決定論的に置換 (乱数を使わず再生成結果を安定させる)
                if ((x * 73856093) ^ (y * 19349663)) % 100 < 60:
                    self.game_map.tiles[x][y] = floor_tile

    def _resolve_ff6_floor_tile(self) -> str:
        """テーマに応じた FF6 風の主床タイル ID を決定する (T24 案4)

        tile_palette が未定義の垂直ワールド構造 (vertical_world) は
        biome / レイアウトから選ぶ: 森系 = 苔床 / 地上・天界の開けた層 = 木床 /
        それ以外 (洞窟・下水道・塔など) = 石畳。
        """
        palette = self.theme_data.get("tile_palette")
        if palette in _FF6_FLOOR_BY_PALETTE:
            return _FF6_FLOOR_BY_PALETTE[palette]
        if self.biome == "forest" or self.theme_data.get("base_layout") == "forest":
            return "TILE_FF6_FLOOR_MOSS"
        if self.zone in ("surface", "heaven"):
            return "TILE_FF6_FLOOR_WOOD"
        return "TILE_FF6_FLOOR_COBBLE"

    def get_monster_pool(self) -> dict[str, list[str]]:
        """現在の層に基づくモンスタープールを取得"""
        return self.theme_data.get(
            "enemy_pools",
            {
                "common": ["slime"],
                "uncommon": ["goblin"],
                "rare": [],
                "unique_boss": None,
            },
        )

    def get_resources(self) -> dict[str, list[str]]:
        """資源・アイテムテーブルを取得"""
        return self.theme_data.get("resources", {"common": [], "uncommon": [], "rare": []})

    def get_gimmicks(self) -> list[str]:
        """特別なギミック・イベントを取得"""
        return self.theme_data.get("gimmicks", [])

    def get_unique_boss(self) -> str | None:
        """固有ボスを取得"""
        pools = self.get_monster_pool()
        return pools.get("unique_boss")

    def get_entrance_position(self) -> tuple[int, int]:
        """層の入口位置を取得（階層移動用）"""
        if not self.game_map or not self.game_map.rooms:
            # デフォルト: マップ中央
            return (
                (self.game_map.width // 2, self.game_map.height // 2) if self.game_map else (10, 10)
            )

        # 最初の部屋の中心を入口とする
        first_room = self.game_map.rooms[0]
        return first_room.center

    def get_spawn_density(self) -> float:
        """モンスタースポーン密度を取得"""
        base_density = 0.02  # 基本2%
        # 深度が増えるほどスポーン密度増加（ただし上限あり）
        depth_factor = min(1.0 + (self.depth * 0.005), 2.0)  # 最大2倍
        # ゾーン別修正
        zone_modifiers = {
            "surface": 0.8,
            "underground": 1.0,
            "otherworld": 1.2,
            "heaven": 0.6,  # 天界は敵少なめ
        }
        zone_mod = zone_modifiers.get(self.zone, 1.0)

        return base_density * depth_factor * zone_mod

    def is_theme_valid(self) -> bool:
        """テーマデータが有効かチェック"""
        return bool(self.theme_data and self.theme_data.get("theme_id"))
