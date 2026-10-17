"""
ワールドマップマネージャー (Vertical World Extension)
ステップ14: WorldMapManagerクラス実装
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass
from typing import Any

from map_engine import GameMap
from world_layer import WorldLayer


@dataclass
class LayerPriority:
    """レイヤーの優先度管理（LRUキャッシュ用）"""

    layer_key: tuple[str, str, int, str]
    last_accessed: float
    priority_score: float

    def __lt__(self, other):
        return self.priority_score < other.priority_score


class WorldMapManager:
    """マルチレイヤーワールドを管理するクラス"""

    def __init__(self, max_loaded_layers: int = 8):
        # 全レイヤーのメタデータ（実際のゲームマップはロード時のみ保持）
        self.layer_templates: dict[tuple[str, str, int, str], WorldLayer] = {}
        # 現在ロードされているレイヤー（メモリ使用中）
        self.loaded_layers: dict[tuple[str, str, int, str], WorldLayer] = {}
        # LRUキャッシュのための優先度キュー
        self.layer_priority_queue: list[LayerPriority] = []
        self.max_loaded_layers = max_loaded_layers

        # プレイヤーの位置情報（レイヤーごと）
        self.player_positions: dict[tuple[str, str, int, str], tuple[int, int]] = {}
        # プレイヤーの現在位置
        self.current_player_layer: tuple[str, str, int, str] | None = None
        self.current_player_pos: tuple[int, int] | None = None

        # 統計情報
        self.layer_load_count = 0
        self.layer_unload_count = 0

    def get_or_create_layer(self, zone: str, biome: str, depth: int, dimension: str) -> WorldLayer:
        """指定された層を取得または作成"""
        layer_key = (zone, biome, depth, dimension)

        if layer_key not in self.layer_templates:
            # 新しいレイヤーテンプレートを作成
            self.layer_templates[layer_key] = WorldLayer(zone, biome, depth, dimension)

        return self.layer_templates[layer_key]

    def load_layer(self, zone: str, biome: str, depth: int, dimension: str) -> GameMap | None:
        """層をロードしてGameMapを返す。メモリ制限がある場合は古い層をアンロード"""
        layer_key = (zone, biome, depth, dimension)

        # 既にロードされている場合はアクセス時間を更新
        if layer_key in self.loaded_layers:
            layer = self.loaded_layers[layer_key]
            layer.last_accessed = time.time()
            self._update_layer_priority(layer_key)
            return layer.game_map

        # メモリ制限チェックと必要ならアンロード
        if len(self.loaded_layers) >= self.max_loaded_layers:
            self._unload_least_recently_used_layer()

        # レイヤーを作成・ロード
        layer = self.get_or_create_layer(zone, biome, depth, dimension)
        game_map = layer.generate_map(
            width=120,  # constants.pyから取得するべきだが、ここではハードコード
            height=80,
        )

        self.loaded_layers[layer_key] = layer
        self._update_layer_priority(layer_key)
        self.layer_load_count += 1

        return game_map

    def unload_layer(self, zone: str, biome: str, depth: int, dimension: str) -> bool:
        """指定された層をアンロード"""
        layer_key = (zone, biome, depth, dimension)

        if layer_key in self.loaded_layers:
            del self.loaded_layers[layer_key]
            # 優先度キューからも削除（実際には Lazy削除）
            self.layer_unload_count += 1
            return True
        return False

    def _unload_least_recently_used_layer(self) -> None:
        """最も最近使われていないレイヤーをアンロード"""
        if not self.loaded_layers:
            return

        # 優先度キューをクリーンアップ（古いエントリを除去）
        valid_entries = []
        for entry in self.layer_priority_queue:
            if (
                entry.layer_key in self.loaded_layers
                and abs(entry.last_accessed - self.loaded_layers[entry.layer_key].last_accessed)
                < 1.0
            ):
                valid_entries.append(entry)

        self.layer_priority_queue = valid_entries

        if not self.layer_priority_queue:
            # キューが空なら最初のレイヤーをアンロード
            if self.loaded_layers:
                key_to_remove = next(iter(self.loaded_layers))
                self.unload_layer(*key_to_remove)
            return

        # 最も優度の低い（最も古い）レイヤーを見つける
        oldest_entry = min(self.layer_priority_queue, key=lambda x: x.priority_score)
        self.unload_layer(*oldest_entry.layer_key)

    def _update_layer_priority(self, layer_key: tuple[str, str, int, str]) -> None:
        """レイヤーの優先度を更新"""
        if layer_key in self.loaded_layers:
            layer = self.loaded_layers[layer_key]
            # 優先度スコア: 最近アクセスされたほど高い（負の値なので、より最近のほど小さい）
            priority_score = -layer.last_accessed
            heapq.heappush(
                self.layer_priority_queue,
                LayerPriority(
                    layer_key=layer_key,
                    last_accessed=layer.last_accessed,
                    priority_score=priority_score,
                ),
            )

    def get_adjacent_layers(
        self, zone: str, biome: str, depth: int, dimension: str
    ) -> list[WorldLayer]:
        """移動可能な隣接層を取得"""
        adjacent = []

        # 同じゾーン・バイオーム・次元での深度移動（上下）
        for delta_depth in [-1, 1]:
            new_depth = depth + delta_depth
            if 0 <= new_depth <= 200:  # 有効な深度範囲
                layer = self.get_or_create_layer(zone, biome, new_depth, dimension)
                adjacent.append(layer)

        # 同じ深度でのゾーン境界移動（例: 地下50階 <-> 異界0階のポータル）
        zone_transitions = self._get_zone_transitions(zone, depth)
        for target_zone, target_depth in zone_transitions:
            layer = self.get_or_create_layer(target_zone, biome, target_depth, dimension)
            adjacent.append(layer)

        # 同じ深度・ゾーンでの次元移動（ポータル・儀式）
        dimension_transitions = self._get_dimension_transitions(dimension)
        for target_dimension in dimension_transitions:
            layer = self.get_or_create_layer(zone, biome, depth, target_dimension)
            adjacent.append(layer)

        return adjacent

    def _get_zone_transitions(self, current_zone: str, current_depth: int) -> list[tuple[str, int]]:
        """ゾーン間の移動可能な境界を取得"""
        transitions = []

        # 地上界 <-> 地下界 (深度0-10の境界付近)
        if current_zone == "surface" and current_depth <= 5:
            transitions.append(("underground", max(1, current_depth)))  # 地下に降りる
        elif current_zone == "underground" and current_depth <= 10:
            transitions.append(("surface", max(0, current_depth - 1)))  # 地上に上がる

        # 地下界 <-> 異界 (深度40-60の境界付近)
        if current_zone == "underground" and 40 <= current_depth <= 60:
            transitions.append(("otherworld", current_depth))
        elif current_zone == "otherworld" and 40 <= current_depth <= 60:
            transitions.append(("underground", current_depth))

        # 異界 <-> 天界 (深度90-110の境界付近)
        if current_zone == "otherworld" and 90 <= current_depth <= 110:
            transitions.append(("heaven", current_depth))
        elif current_zone == "heaven" and 90 <= current_depth <= 110:
            transitions.append(("otherworld", current_depth))

        return transitions

    def get_adjacent_layers_with_secrets(
        self,
        zone: str,
        biome: str,
        depth: int,
        dimension: str,
        player_unlocked_secrets: set[str] | None = None,
    ) -> list[WorldLayer]:
        """秘密通路を含む隣接層を取得 (Step 42)"""
        adjacent = self.get_adjacent_layers(zone, biome, depth, dimension)

        # 秘密通路による層間移動を追加
        if player_unlocked_secrets:
            try:
                from secret_area_system import SECRET_REGISTRY

                SECRET_REGISTRY.load_from_yaml()

                current_layer_key = f"{zone}:{biome}:{depth}:{dimension}"
                areas = SECRET_REGISTRY.get_areas_in_layer(current_layer_key)

                for area in areas:
                    if area.id not in player_unlocked_secrets:
                        continue
                    if area.secret_type not in ("secret_floor", "vent"):
                        continue

                    connections = SECRET_REGISTRY.get_connections_from(area.id)
                    for conn in connections:
                        if conn.connection_type not in ("tunnel", "floor", "vent"):
                            continue
                        target_area = SECRET_REGISTRY.get_secret_area(conn.to_area)
                        if target_area:
                            target_layer = self.get_or_create_layer(
                                *target_area.layer_key.split(":")
                            )
                            if target_layer not in adjacent:
                                adjacent.append(target_layer)
            except Exception:
                pass

        return adjacent

    def _get_dimension_transitions(self, current_dimension: str) -> list[str]:
        """次元間の移動可能な遷移を取得"""
        # 基本的には同じ次元内での移動がメイン
        # 特殊な場所（儀式場・ポータル）でのみ次元間移動可能
        transitions = {
            "material": ["ethereal"],  # 物質次元から精神次元へ（特殊条件下）
            "ethereal": ["material", "void"],  # 精神次元は物質・虚無間を行き来可能
            "void": ["ethereal"],  # 虚無次元から精神次元へ
        }
        return transitions.get(current_dimension, [])

    def set_player_position(
        self, zone: str, biome: str, depth: int, dimension: str, x: int, y: int
    ) -> None:
        """プレイヤーの位置を設定"""
        layer_key = (zone, biome, depth, dimension)
        self.player_positions[layer_key] = (x, y)
        self.current_player_layer = layer_key
        self.current_player_pos = (x, y)

        # 該当レイヤーへのアクセス時間を更新
        if layer_key in self.loaded_layers:
            self.loaded_layers[layer_key].last_accessed = time.time()
            self._update_layer_priority(layer_key)

    def get_player_position(
        self,
    ) -> tuple[tuple[str, str, int, str] | None, tuple[int, int] | None]:
        """プレイヤーの現在位置を取得"""
        return self.current_player_layer, self.current_player_pos

    def get_player_position_in_layer(
        self, zone: str, biome: str, depth: int, dimension: str
    ) -> tuple[int, int] | None:
        """特定の層におけるプレイヤーの位置を取得"""
        layer_key = (zone, biome, depth, dimension)
        return self.player_positions.get(layer_key)

    def get_loaded_layers_count(self) -> int:
        """現在ロードされているレイヤー数を取得"""
        return len(self.loaded_layers)

    def get_total_layers_count(self) -> int:
        """既知のレイヤー総数を取得"""
        return len(self.layer_templates)

    def get_statistics(self) -> dict[str, Any]:
        """統計情報を取得"""
        return {
            "loaded_layers": len(self.loaded_layers),
            "total_layers": len(self.layer_templates),
            "max_loaded_layers": self.max_loaded_layers,
            "layer_load_count": self.layer_load_count,
            "layer_unload_count": self.layer_unload_count,
            "memory_usage_estimate": len(self.loaded_layers) * 0.5,  # MB単位の概算
        }
