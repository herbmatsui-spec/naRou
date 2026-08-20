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
                vertical_world = themes.get("dungeon_themes", {}).get(
                    "vertical_world", {}
                )
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
        return self.theme_data.get(
            "resources", {"common": [], "uncommon": [], "rare": []}
        )

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
                (self.game_map.width // 2, self.game_map.height // 2)
                if self.game_map
                else (10, 10)
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
