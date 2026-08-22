"""
Elona Roguelike Clone - Game Map & Generation (Phase 3)
Steps 21 to 30 implementation.
Vertical World Extension: Steps 13-18
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import json
import math
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from secret_area_system import SecretArea
    from world_map_manager import WorldMapManager

from constants import (
    TILE_FALSE_WALL,
    TILE_HIDDEN_DOOR,
    TILE_SECRET_FLOOR,
    TILE_STAIRS_DOWN,
    TILE_STAIRS_UP,
    TILE_VENT,
    TILE_WALL,
)
from feature_flags import is_enabled

# ワールドレイヤーシステムのインポート（オプション）
try:
    from world_layer import WorldLayer

    WORLD_LAYER_AVAILABLE = True
except ImportError:
    WORLD_LAYER_AVAILABLE = False
    WorldLayer = None  # type: ignore


class TileRegistry:
    """Loads tileset_def.json and provides tile ID → atlas UV mapping"""

    def __init__(self, def_path: str = "assets/tiles/tileset_def.json"):
        self.def_path = Path(def_path)
        self.defs: dict[str, Any] = {}
        self.atlas_16_meta: dict[str, Any] = {}
        self.atlas_32_meta: dict[str, Any] = {}
        self.atlas_tiny_rogue_meta: dict[str, Any] = {}
        self.tile_size: int = 16
        self._load_definitions()
        self._load_atlas_metadata()

    def _load_definitions(self) -> None:
        """Load tile definitions from JSON"""
        if self.def_path.exists():
            with open(self.def_path) as f:
                self.defs = json.load(f)
            self.tile_size = self.defs.get("tile_size", 16)
        else:
            # Fallback definitions if file doesn't exist
            self.defs = {
                "version": "1.0",
                "tile_size": 16,
                "tiles": {
                    "TILE_WALL": {"file": "terrain/wall_dungeon.png", "variants": 1},
                    "TILE_FLOOR": {"file": "terrain/floor_dungeon.png", "variants": 1},
                    "TILE_STAIRS_DOWN": {
                        "file": "terrain/stairs_down.png",
                        "variants": 1,
                    },
                    "TILE_STAIRS_UP": {"file": "terrain/stairs_up.png", "variants": 1},
                    "TILE_WATER": {"file": "terrain/water.png", "variants": 1},
                    "TILE_TRAP": {"file": "terrain/trap.png", "variants": 1},
                },
            }
            self.tile_size = 16

    def _load_atlas_metadata(self) -> None:
        """Load atlas metadata JSON files"""
        atlas_dir = self.def_path.parent

        def _safe_load(path) -> dict[str, Any]:
            if not path.exists():
                return {}
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                # 壊れた/競合マーカー付きのメタデータは無視して続行
                return {}

        # Load 16x16 metadata
        self.atlas_16_meta = _safe_load(atlas_dir / "tileset_16x16.json")

        # Load 32x32 metadata
        self.atlas_32_meta = _safe_load(atlas_dir / "tileset_32x32.json")

        # Load tiny_rogue_16 metadata
        self.atlas_tiny_rogue_meta = _safe_load(atlas_dir / "tileset_tiny_rogue_16x16.json")

    def get_uv(
        self, tile_id: str, variant: int = 0, scale: str = "16"
    ) -> tuple[int, int, int, int]:
        """
        Get UV coordinates for a tile in the atlas.

        Args:
            tile_id: The tile identifier (e.g., "TILE_WALL")
            variant: Variant index for tiles with multiple variants
            scale: Either "16", "32", or "tiny_rogue_16" for tile scale

        Returns:
            Tuple of (x, y, width, height) in atlas pixels
        """
        # Check feature flag for tiny_rogue_16
        if scale == "tiny_rogue_16":
            try:
                from feature_flags import is_enabled

                if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
                    scale = "16"  # Fall back to standard 16x16
            except ImportError:
                pass

        # Select appropriate atlas metadata
        if scale == "32":
            atlas_meta = self.atlas_32_meta
            tile_size = 32
        elif scale == "tiny_rogue_16":
            atlas_meta = self.atlas_tiny_rogue_meta
            tile_size = 16
        else:
            atlas_meta = self.atlas_16_meta
            tile_size = 16

        # If we don't have metadata, fall back to procedural generation
        if not atlas_meta:
            # Simple fallback: assume tiles are in a grid
            idx = hash(tile_id) % 256  # Simple hash to get consistent position
            cols = 16
            x = (idx % cols) * tile_size
            y = (idx // cols) * tile_size
            return (x, y, tile_size, tile_size)

        # Get tile definition
        if "tiles" not in self.defs or tile_id not in self.defs["tiles"]:
            # Fallback to first tile or a default
            tile_id = (
                next(iter(self.defs.get("tiles", {}).keys()))
                if self.defs.get("tiles")
                else "TILE_FLOOR"
            )

        tile_def = self.defs["tiles"][tile_id]

        # Get base position from metadata
        file_key = tile_def["file"]
        if "tiles" not in atlas_meta or file_key not in atlas_meta["tiles"]:
            # Fallback: calculate position based on hash
            idx = hash(tile_id + file_key) % 256
            cols = 16
            x = (idx % cols) * tile_size
            y = (idx // cols) * tile_size
            base_x, base_y, base_w, base_h = x, y, tile_size, tile_size
        else:
            meta = atlas_meta["tiles"][file_key]
            base_x, base_y = meta["x"], meta["y"]
            base_w, base_h = meta["width"], meta["height"]

        # Apply variant offset
        variant_width = tile_def.get("variant_width", base_w)
        variant_offset = variant * variant_width

        return (base_x + variant_offset, base_y, variant_width, base_h)

    def get_animation_frame(
        self, tile_id: str, frame: int, scale: str = "16"
    ) -> tuple[int, int, int, int]:
        """
        Get UV coordinates for a specific animation frame.

        Args:
            tile_id: The tile identifier
            frame: Frame index
            scale: Either "16" or "32" for tile scale

        Returns:
            Tuple of (x, y, width, height) in atlas pixels
        """
        tile_def = self.defs.get("tiles", {}).get(tile_id, {})
        if not tile_def.get("animated", False):
            # Not animated, return first frame
            return self.get_uv(tile_id, 0, scale)

        frame_count = tile_def.get("frames", 1)
        frame_index = frame % frame_count

        # Get base UV and add frame offset
        base_uv = self.get_uv(tile_id, 0, scale)
        frame_width = tile_def.get("frame_width", base_uv[2])

        return (
            base_uv[0] + frame_index * frame_width,
            base_uv[1],
            frame_width,
            base_uv[3],
        )


# Global tile registry instance
TILE_REGISTRY = TileRegistry()


class RectRoom:
    """マップ内の部屋を定義するクラス (ステップ21)"""

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)
        return center_x, center_y

    def intersects(self, other: RectRoom) -> bool:
        """他の部屋と重なっているかを判定"""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


class GameMap:
    """ダンジョンや街などのマップデータ管理 (ステップ21〜30)"""

    def __init__(
        self,
        width: int,
        height: int,
        map_type: str = "dungeon",
        floor_level: int = 1,
        world_layer: WorldLayer | None = None,
    ):
        self.width = width
        self.height = height
        self.map_type = map_type
        self.floor_level = floor_level
        self.world_layer = world_layer  # ワールドレイヤーへの参照（垂直ワールド拡張用）

        # タイル初期化: 全て壁 (タイルID文字列で格納)
        self.tiles = [["TILE_WALL" for _ in range(height)] for _ in range(width)]

        # ピクセルアートモードのフラグ (後で設定可能にする)
        self.use_pixel_art = False

        # アニメーションタイルの状態追跡
        self.tile_animations: dict[tuple[int, int], dict[str, Any]] = {}

        # タイルバリアント（オートタイル用）の追跡
        self.tile_variants: dict[tuple[int, int], int] = {}

        # Room decorations (TR_DECOR variants)
        self.decorations: dict[tuple[int, int], str] = {}

        # 松明（光源）位置 — ダイナミックライティング用 (Phase 2-A)
        self.torch_positions: list[tuple[int, int]] = []

        # 視界・探索済みフラグ (ステップ26, 27)
        self.visible = [[False for _ in range(height)] for _ in range(width)]
        self.explored = [[False for _ in range(height)] for _ in range(width)]

        # 部屋リスト
        self.rooms: list[RectRoom] = []

        # 階段・開始位置 (ステップ23)
        self.stairs_down_pos: tuple[int, int] | None = None
        self.stairs_up_pos: tuple[int, int] | None = None
        self.start_pos: tuple[int, int] = (int(width / 2), int(height / 2))

        # Proposal 8: 緻密なプロシージャル・ディテール (壁画・血文字・刻印・苔)
        self.micro_details: dict[tuple[int, int], dict[str, Any]] = {}

        # SkillEaterSecretAccess - 隠しタイル管理
        self.hidden_tiles: dict[tuple[int, int], dict[str, Any]] = {}

    def is_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        if not self.is_in_bounds(x, y):
            return False
        tile = self.tiles[x][y]
        # 隠し扉・偽の壁は発見済みなら通行可能
        if tile in (TILE_HIDDEN_DOOR, TILE_FALSE_WALL):
            return True
        # 床下通路・換気ダクトは常に通行可能（発見後）
        if tile in (TILE_SECRET_FLOOR, TILE_VENT):
            return True
        return tile not in (TILE_WALL,)

    def is_transparent(self, x: int, y: int) -> bool:
        """光を通すか（FOV計算用）"""
        if not self.is_in_bounds(x, y):
            return False
        tile = self.tiles[x][y]
        # 隠し扉・偽の壁は発見済みでも光を通さない（壁扱い）
        if tile in (TILE_HIDDEN_DOOR, TILE_FALSE_WALL):
            return False
        # 床下通路・換気ダクトは光を通す
        if tile in (TILE_SECRET_FLOOR, TILE_VENT):
            return True
        return tile != TILE_WALL

    def create_room(self, room: RectRoom) -> None:
        """部屋の内部を床にする (Tiny Rogue variants randomization)"""
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.tiles[x][y] = "TILE_FLOOR"
                # Random floor variant for visual variety (Tiny Rogue has 12 variants)
                if is_enabled("ENABLE_TINY_ROGUE_GFX"):
                    variant = random.randint(0, 11)
                    self.tile_variants[(x, y)] = variant
                else:
                    self.tile_variants[(x, y)] = 0

        # Place random decorations in room (10% chance per room)
        if is_enabled("ENABLE_TINY_ROGUE_GFX") and random.random() < 0.1:
            decor_x = random.randint(room.x1 + 1, room.x2 - 1)
            decor_y = random.randint(room.y1 + 1, room.y2 - 1)
            if self.tiles[decor_x][decor_y] == "TILE_FLOOR":
                # Pick a random decor variant from the 12 available
                decor_variant = random.randint(1, 12)
                self.decorations = getattr(self, "decorations", {})
                self.decorations[(decor_x, decor_y)] = f"TR_DECOR_{decor_variant:02d}"

    def create_h_tunnel(self, x1: int, x2: int, y: int) -> None:
        """水平方向の通路を作る (ステップ22)"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[x][y] = "TILE_FLOOR"
            if is_enabled("ENABLE_TINY_ROGUE_GFX"):
                self.tile_variants[(x, y)] = random.randint(0, 11)

    def create_v_tunnel(self, y1: int, y2: int, x: int) -> None:
        """垂直方向の通路を作る (ステップ22)"""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[x][y] = "TILE_FLOOR"
            if is_enabled("ENABLE_TINY_ROGUE_GFX"):
                self.tile_variants[(x, y)] = random.randint(0, 11)

    def generate_dungeon(
        self,
        max_rooms: int = 35,
        room_min_size: int = 6,
        room_max_size: int = 15,
    ) -> None:
        """ランダムダンジョン生成 (ステップ21, 22, 23)"""
        self.rooms = []
        for _ in range(max_rooms):
            w = random.randint(room_min_size, room_max_size)
            h = random.randint(room_min_size, room_max_size)
            x = random.randint(1, self.width - w - 2)
            y = random.randint(1, self.height - h - 2)

            new_room = RectRoom(x, y, w, h)
            if any(new_room.intersects(other) for other in self.rooms):
                continue

            self.create_room(new_room)
            (new_x, new_y) = new_room.center

            if len(self.rooms) == 0:
                # 最初の部屋を中心開始位置 & 上り階段に
                self.start_pos = (new_x, new_y)
                self.stairs_up_pos = (new_x, new_y)
                self.tiles[new_x][new_y] = "TILE_STAIRS_UP"
                # Initialize animation for upstairs
                self.tile_animations[(new_x, new_y)] = {
                    "tile_id": "TILE_STAIRS_UP",
                    "frame": 0,
                    "timer": 0.0,
                    "fps": 4,  # 4 FPS for stairs animation
                    "frames": 4,
                }
            else:
                # 前の部屋と通路で繋ぐ
                (prev_x, prev_y) = self.rooms[-1].center
                if random.randint(0, 1) == 1:
                    self.create_h_tunnel(prev_x, new_x, prev_y)
                    self.create_v_tunnel(prev_y, new_y, new_x)
                else:
                    self.create_v_tunnel(prev_y, new_y, prev_x)
                    self.create_h_tunnel(prev_x, new_x, new_y)

            self.rooms.append(new_room)

        # 最初の部屋を中心開始位置 & 上り階段に
        if len(self.rooms) == 1:
            first_x, first_y = self.rooms[0].center
            self.start_pos = (first_x, first_y)
            self.stairs_up_pos = (first_x, first_y)
            self.tiles[first_x][first_y] = "TILE_STAIRS_UP"
            # Initialize animation for upstairs
            self.tile_animations[(first_x, first_y)] = {
                "tile_id": "TILE_STAIRS_UP",
                "frame": 0,
                "timer": 0.0,
                "fps": 4,  # 4 FPS for stairs animation
                "frames": 4,
            }

        # 最後の部屋に下り階段を配置 (ステップ23)
        if self.rooms:
            last_x, last_y = self.rooms[-1].center
            self.stairs_down_pos = (last_x, last_y)
            self.tiles[last_x][last_y] = "TILE_STAIRS_DOWN"
            # Initialize animation for downstairs
            self.tile_animations[(last_x, last_y)] = {
                "tile_id": "TILE_STAIRS_DOWN",
                "frame": 0,
                "timer": 0.0,
                "fps": 4,  # 4 FPS for stairs animation
                "frames": 4,
            }

        # 特殊地形・水たまりや罠を配置 (ステップ28)
        for room in self.rooms[1:-1]:
            if random.random() < 0.3:
                rx = random.randint(room.x1 + 1, room.x2 - 1)
                ry = random.randint(room.y1 + 1, room.y2 - 1)
                if self.tiles[rx][ry] == "TILE_FLOOR":
                    tile_type = "TILE_WATER" if random.random() < 0.5 else "TILE_TRAP"
                    self.tiles[rx][ry] = tile_type
                    # Initialize animation for water/trap
                    if tile_type == "TILE_WATER":
                        self.tile_animations[(rx, ry)] = {
                            "tile_id": "TILE_WATER",
                            "frame": 0,
                            "timer": 0.0,
                            "fps": 8,  # 8 FPS for water animation
                            "frames": 8,
                        }
                    else:  # TILE_TRAP
                        self.tile_animations[(rx, ry)] = {
                            "tile_id": "TILE_TRAP",
                            "frame": 0,
                            "timer": 0.0,
                            "fps": 6,  # 6 FPS for trap animation
                            "frames": 3,
                        }

        # Proposal 8: 緻密なプロシージャル・ディテール (壁画・血文字・古代刻印の生成)
        blood_messages = [
            "『ここに眠る者、我が名を呼ぶなかれ…』",
            "『妹よ…すまない、塩を持ってくるのを忘れた…』",
            "『深層に潜む異形の神に目を合わせるな』",
            "『エーテル風が吹く夜、この壁に隠れよ』",
        ]
        mural_descriptions = [
            "古代人が巨大な螺旋を描いた退色した壁画",
            "神ジュアが冒険者に手を差し伸べる神聖な彫刻",
            "黒天使が弓を引く躍動感あるレリーフ",
            "狂気に堕ちた魔法使いの血染めの術式",
        ]
        for room in self.rooms:
            # 確率で壁または床にプロシージャルな詳細を刻む
            if random.random() < 0.4:
                detail_x = random.randint(room.x1, room.x2)
                detail_y = random.randint(room.y1, room.y2)
                is_wall = self.tiles[detail_x][detail_y] == "TILE_WALL"
                if is_wall:
                    self.micro_details[(detail_x, detail_y)] = {
                        "type": "mural",
                        "title": "古代の壁画・彫刻",
                        "description": random.choice(mural_descriptions),
                        "char": "📜",
                    }
                else:
                    self.micro_details[(detail_x, detail_y)] = {
                        "type": "bloodstain",
                        "title": "先人の血文字",
                        "description": random.choice(blood_messages),
                        "char": "🩸",
                    }

        # Calculate variants for autotiling
        self.calculate_all_variants()

        # 壁面に松明（光源）を配置 (Phase 2-A: ダイナミックライティング)
        self._place_torches(max_per_room=2, global_cap=40)

        # SkillEaterSecretAccess - 秘密エリア配置 (Steps 49-52)
        self._place_secret_areas()

    def _place_torches(self, max_per_room: int = 2, global_cap: int = 40) -> None:
        """壁でかつ床に接するタイルを松明（光源）として記録する。"""
        self.torch_positions = []
        seen: set = set()
        candidates: list[tuple[int, int]] = []
        for room in self.rooms:
            count = 0
            # 部屋を囲む外壁のうち、内側に床を持つものを松明にする
            border = []
            for x in range(room.x1, room.x2):
                border.append((x, room.y1))
                border.append((x, room.y2 - 1))
            for y in range(room.y1, room.y2):
                border.append((room.x1, y))
                border.append((room.x2 - 1, y))
            for tx, ty in border:
                if not self.is_in_bounds(tx, ty) or self.tiles[tx][ty] != "TILE_WALL":
                    continue
                # 隣接する床（明かりの届く先）があれば松明として成立
                has_floor = any(
                    self.is_in_bounds(nx, ny) and self.tiles[nx][ny] == "TILE_FLOOR"
                    for (nx, ny) in (
                        (tx + 1, ty),
                        (tx - 1, ty),
                        (tx, ty + 1),
                        (tx, ty - 1),
                    )
                )
                if has_floor and (tx, ty) not in seen:
                    seen.add((tx, ty))
                    candidates.append((tx, ty))
                    count += 1
                    if count >= max_per_room:
                        break
            if len(self.torch_positions) >= global_cap:
                break
        self.torch_positions = candidates[:global_cap]

    def _place_secret_areas(self) -> None:
        """秘密エリアをダンジョンに配置 (SkillEaterSecretAccess Steps 49-52)"""
        if not self.world_layer:
            return

        try:
            from secret_area_system import SECRET_REGISTRY

            SECRET_REGISTRY.load_from_yaml()

            layer_key = f"{self.world_layer.zone}:{self.world_layer.biome}:{self.world_layer.depth}:{self.world_layer.dimension}"
            areas = SECRET_REGISTRY.get_areas_in_layer(layer_key)

            if not areas:
                return

            # テーマからギミック密度を取得
            gimmicks = self.world_layer.theme_data.get("gimmicks", [])
            secret_door_chance = 0.15
            false_wall_chance = 0.1
            secret_floor_chance = 0.05
            vent_chance = 0.08

            for g in gimmicks:
                if "secret_doors:" in g:
                    secret_door_chance = float(g.split(":")[1])
                elif "false_walls:" in g:
                    false_wall_chance = float(g.split(":")[1])
                elif "secret_floors:" in g:
                    secret_floor_chance = float(g.split(":")[1])
                elif "vents:" in g:
                    vent_chance = float(g.split(":")[1])

            used_positions = set()
            # 階段位置は除外
            if self.stairs_up_pos:
                used_positions.add(self.stairs_up_pos)
            if self.stairs_down_pos:
                used_positions.add(self.stairs_down_pos)

            for area in areas:
                if area.position in used_positions:
                    # 指定位置が使えない場合、近くの適切な場所を探す
                    alt_pos = self._find_secret_position(area, used_positions)
                    if alt_pos:
                        area.position = alt_pos
                    else:
                        continue

                used_positions.add(area.position)
                x, y = area.position

                if not self.is_in_bounds(x, y):
                    continue

                # 元のタイルを記録
                original_tile = self.tiles[x][y]
                if not hasattr(self, "hidden_tiles"):
                    self.hidden_tiles = {}
                self.hidden_tiles[(x, y)] = {
                    "original_tile": original_tile,
                    "secret_type": area.secret_type,
                    "area_id": area.id,
                }

                # 秘密タイプに応じて壁タイルに見せかける
                if area.secret_type in ("hidden_door", "false_wall"):
                    self.tiles[x][y] = "TILE_WALL"
                elif area.secret_type in ("secret_floor", "vent"):
                    self.tiles[x][y] = "TILE_FLOOR"

                # ランダム配置の場合の確率判定（YAMLで指定位置がない場合）
                # ここではYAMLで指定された位置を優先的に使用
        except Exception:
            pass

    def _find_secret_position(
        self, area: SecretArea, used_positions: set
    ) -> tuple[int, int] | None:
        """秘密エリアの代替位置を探す"""
        # 部屋の境界壁を候補とする
        candidates = []
        for room in self.rooms:
            if area.secret_type in ("hidden_door", "false_wall"):
                # 部屋の境界壁
                for x in range(room.x1, room.x2):
                    for y in (room.y1, room.y2 - 1):
                        if (x, y) not in used_positions and self.is_in_bounds(x, y):
                            if self.tiles[x][y] == "TILE_WALL":
                                candidates.append((x, y))
                for y in range(room.y1, room.y2):
                    for x in (room.x1, room.x2 - 1):
                        if (x, y) not in used_positions and self.is_in_bounds(x, y):
                            if self.tiles[x][y] == "TILE_WALL":
                                candidates.append((x, y))
            elif area.secret_type in ("secret_floor", "vent"):
                # 部屋の内部床
                for x in range(room.x1 + 1, room.x2 - 1):
                    for y in range(room.y1 + 1, room.y2 - 1):
                        if (x, y) not in used_positions and self.is_in_bounds(x, y):
                            if self.tiles[x][y] == "TILE_FLOOR":
                                candidates.append((x, y))

        if candidates:
            return random.choice(candidates)
        return None

    def generate_town(self) -> None:
        """街マップ生成（ステップ25）"""
        self.map_type = "town"
        # 外壁以外をすべて床にする
        for x in range(self.width):
            for y in range(self.height):
                if x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1:
                    self.tiles[x][y] = "TILE_WALL"
                else:
                    self.tiles[x][y] = "TILE_FLOOR"

        # 建物（店舗など）を数棟配置
        houses = [
            RectRoom(10, 10, 12, 8),
            RectRoom(30, 10, 14, 10),
            RectRoom(15, 25, 16, 8),
        ]
        for h in houses:
            for x in range(h.x1, h.x2):
                for y in range(h.y1, h.y2):
                    if x == h.x1 or x == h.x2 - 1 or y == h.y1 or y == h.y2 - 1:
                        self.tiles[x][y] = "TILE_WALL"
                    else:
                        self.tiles[x][y] = "TILE_FLOOR"
            # 扉を作る
            self.tiles[int((h.x1 + h.x2) / 2)][h.y2 - 1] = "TILE_FLOOR"

        self.start_pos = (25, 20)

        # Calculate variants for autotiling
        self.calculate_all_variants()

        # 街の建物外壁にも松明を配置 (Phase 2-A)
        self._place_torches(max_per_room=1, global_cap=20)

    def compute_fov(self, center_x: int, center_y: int, radius: int = 8) -> None:
        """Raycasting による視界(FOV)計算 (ステップ26, 27)"""
        # 視界をリセット
        for x in range(self.width):
            for y in range(self.height):
                self.visible[x][y] = False

        self.visible[center_x][center_y] = True
        self.explored[center_x][center_y] = True

        # 360度にレイを飛ばす
        for angle in range(0, 360, 2):
            rad = math.radians(angle)
            dx = math.cos(rad)
            dy = math.sin(rad)

            ox = center_x + 0.5
            oy = center_y + 0.5

            for r in range(radius):
                ox += dx
                oy += dy
                ix, iy = int(ox), int(oy)

                if not self.is_in_bounds(ix, iy):
                    break

                self.visible[ix][iy] = True
                self.explored[ix][iy] = True

                if not self.is_transparent(ix, iy):
                    break

    def get_faction_tile_color(
        self, base_color: tuple[int, int, int], faction_id: str | None
    ) -> tuple[int, int, int]:
        """派閥色に応じたタイルのカラーブレンディング (Steps 59, 60)"""
        if not faction_id:
            return base_color
        try:
            from faction_war_system import REGISTRY as FW_REG

            FW_REG.load()
            fw = FW_REG.get(faction_id)
            if fw and fw.color:
                # 派閥色を20%ブレンド
                fc = fw.color
                r = int(base_color[0] * 0.8 + fc[0] * 0.2)
                g = int(base_color[1] * 0.8 + fc[1] * 0.2)
                b = int(base_color[2] * 0.8 + fc[2] * 0.2)
                return (min(255, r), min(255, g), min(255, b))
        except Exception:
            logger.exception("Unhandled exception")
            # If faction lookup fails, just return the base color
            pass
        return base_color

    def select_dungeon_for_reincarnation(self, player_reinc_count: int) -> str | None:
        """転生ダンジョン選択ロジック (Steps 50, 51)"""
        # TODO: Reincarnation dungeon
        from reincarnation_dungeon_system import REGISTRY as RD_REG
        from reincarnation_dungeon_system import ReincarnationDungeonManager

        RD_REG.load()
        mgr = ReincarnationDungeonManager(RD_REG)
        avail = mgr.get_available_dungeons(player_reinc_count)
        if avail:
            return avail[0].id
        return None

    def update_animations(self, delta_time: float) -> None:
        """Update all animated tiles"""
        for (x, y), anim in list(self.tile_animations.items()):
            anim["timer"] += delta_time
            if anim["timer"] >= 1.0 / anim["fps"]:
                anim["timer"] = 0
                anim["frame"] = (anim["frame"] + 1) % anim["frames"]
                # If animation has finished and shouldn't loop, remove it
                tile_def = TILE_REGISTRY.defs.get("tiles", {}).get(anim["tile_id"], {})
                if not tile_def.get("loop", True) and anim["frame"] == 0:
                    del self.tile_animations[(x, y)]

        # SkillEaterSecretAccess - 隠し扉アニメーション (Step 39)
        self._update_hidden_door_animations(delta_time)

    def _update_hidden_door_animations(self, delta_time: float) -> None:
        """隠し扉の開閉アニメーション更新"""
        if not hasattr(self, "hidden_tiles"):
            return

        for (x, y), hidden_info in list(self.hidden_tiles.items()):
            if hidden_info["secret_type"] != "hidden_door":
                continue

            area_id = hidden_info.get("area_id")
            if not area_id:
                continue

            from secret_area_system import SECRET_REGISTRY

            area = SECRET_REGISTRY.get_secret_area(area_id)
            if not area or not area.is_unlocked:
                continue

            # 解放済みの隠し扉を開くアニメーション
            anim_key = f"hidden_door_{x}_{y}"
            if anim_key not in self.tile_animations:
                self.tile_animations[anim_key] = {
                    "tile_id": "TILE_HIDDEN_DOOR",
                    "frame": 0,
                    "timer": 0.0,
                    "fps": 6,  # 6 FPS
                    "frames": 4,  # 4フレームで開く
                    "target_tile": "TILE_FLOOR",
                    "pos": (x, y),
                }

            anim = self.tile_animations[anim_key]
            anim["timer"] += delta_time
            if anim["timer"] >= 1.0 / anim["fps"]:
                anim["timer"] = 0
                anim["frame"] = min(anim["frame"] + 1, anim["frames"] - 1)
                if anim["frame"] == anim["frames"] - 1:
                    # アニメーション完了: 床タイルに変更
                    self.tiles[x][y] = anim["target_tile"]
                    del self.tile_animations[anim_key]

    def calculate_wall_variant(self, x: int, y: int) -> int:
        """Calculate wall variant based on neighboring tiles (autotiling)"""
        if not self.is_in_bounds(x, y) or self.tiles[x][y] != "TILE_WALL":
            return 0

        # Check neighbors: N, E, S, W
        mask = 0
        if self.is_in_bounds(x, y - 1) and self.tiles[x][y - 1] == "TILE_WALL":
            mask |= 1  # North
        if self.is_in_bounds(x + 1, y) and self.tiles[x + 1][y] == "TILE_WALL":
            mask |= 2  # East
        if self.is_in_bounds(x, y + 1) and self.tiles[x][y + 1] == "TILE_WALL":
            mask |= 4  # South
        if self.is_in_bounds(x - 1, y) and self.tiles[x - 1][y] == "TILE_WALL":
            mask |= 8  # West

        # Simple 4-bit to 4-bit mapping (can be expanded to 47-tile set later)
        # For now, just return the mask as the variant index
        return mask

    def calculate_floor_variant(self, x: int, y: int) -> int:
        """Calculate floor variant based on neighboring tiles (for variation)"""
        if not self.is_in_bounds(x, y) or self.tiles[x][y] != "TILE_FLOOR":
            return 0

        # For floor tiles, we can use a simple random variant based on position
        # to break up repetition, or use more complex autotiling if desired
        # Using position-based hash for deterministic variation
        return ((x * 73856093) ^ (y * 19349663)) % 8  # 8 variants for floor

    def calculate_all_variants(self) -> None:
        """Calculate variants for all tiles on the map"""
        self.tile_variants.clear()
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[x][y] == "TILE_WALL":
                    self.tile_variants[(x, y)] = self.calculate_wall_variant(x, y)
                elif self.tiles[x][y] == "TILE_FLOOR":
                    self.tile_variants[(x, y)] = self.calculate_floor_variant(x, y)
                # Other tile types don't need variants for now

    def is_stairs_down_available(self) -> bool:
        """下り階段が次の層へ続くかチェック（垂直ワールド拡張用）"""
        if not self.world_layer or not self.stairs_down_pos:
            return False

        # 基本的には常に利用可能だが、特殊条件がある場合はここでチェック
        # 例: 特定のアイテムが必要、クエスト完了が必要等
        return True

    def is_stairs_up_available(self) -> bool:
        """上り階段が前の層へ続くかチェック（垂直ワールド拡張用）"""
        return not (not self.world_layer or not self.stairs_up_pos)

    # SkillEaterSecretAccess - ミニマップ・探索済みフラグ統合 (Step 58)
    def get_secret_minimap_data(self) -> dict:
        """ミニマップ用の秘密エリアデータを取得"""
        discovered_secrets = {}
        locked_secrets = {}

        if hasattr(self, "hidden_tiles"):
            for (x, y), info in self.hidden_tiles.items():
                area_id = info.get("area_id")
                secret_type = info.get("secret_type")

                from secret_area_system import SECRET_REGISTRY

                area = SECRET_REGISTRY.get_secret_area(area_id) if area_id else None

                if area and area.is_discovered:
                    if area.is_unlocked:
                        discovered_secrets[(x, y)] = {
                            "type": secret_type,
                            "name": area.name,
                            "icon": "🔓",
                        }
                    else:
                        locked_secrets[(x, y)] = {
                            "type": secret_type,
                            "name": area.name,
                            "icon": "🔒",
                            "hint": area.get_hint_text() if area else "",
                        }

        return {
            "discovered": discovered_secrets,
            "locked": locked_secrets,
        }

    # SkillEaterSecretAccess - ロックされた秘密のヒント (Step 59)
    def get_secret_hint_at(self, x: int, y: int) -> str | None:
        """指定座標の秘密エリアのヒントを取得"""
        if not hasattr(self, "hidden_tiles"):
            return None

        info = self.hidden_tiles.get((x, y))
        if not info:
            return None

        area_id = info.get("area_id")
        if not area_id:
            return None

        from secret_area_system import SECRET_REGISTRY

        area = SECRET_REGISTRY.get_secret_area(area_id)
        if not area:
            return None

        if area.is_unlocked:
            return f"【{area.name}】は既に解放済みです。"
        elif area.is_discovered:
            return f"【{area.name}】解除条件: {area.get_hint_text()}"
        else:
            return "この壁には何か秘密がありそうだ…"

    def get_layer_transition_info(self) -> dict[str, Any]:
        """階層間移動に必要な情報を取得（垂直ワールド拡張用）"""
        if not self.world_layer:
            return {}

        return {
            "current_layer": {
                "zone": self.world_layer.zone,
                "biome": self.world_layer.biome,
                "depth": self.world_layer.depth,
                "dimension": self.world_layer.dimension,
            },
            "can_go_down": self.is_stairs_down_available(),
            "can_go_up": self.is_stairs_up_available(),
            "stairs_down_pos": self.stairs_down_pos,
            "stairs_up_pos": self.stairs_up_pos,
        }

    def handle_stairs_interaction(
        self, player_x: int, player_y: int, world_manager: WorldMapManager
    ) -> tuple[int, int, str] | None:
        """
        階段との相互作用を処理し、必要なら層移動を返す
        返り値: (new_x, new_y, target_layer_key) または None（移動なし）
        target_layer_key format: "zone:biome:depth:dimension"
        """
        if not self.world_layer:
            return None

        # 下り階段に立っているかチェック
        if self.tiles[player_x][player_y] == TILE_STAIRS_DOWN:
            if self.is_stairs_down_available():
                # 次の層を決定
                target_layer = self._calculate_target_layer_down(world_manager)
                if target_layer:
                    # 次の層の入口座標を計算（通常は上り階段の位置またはデフォルト位置）
                    entrance_pos = target_layer.get_entrance_position()
                    layer_key = f"{target_layer.zone}:{target_layer.biome}:{target_layer.depth}:{target_layer.dimension}"
                    return (entrance_pos[0], entrance_pos[1], layer_key)

        # 上り階段に立っているかチェック
        elif self.tiles[player_x][player_y] == TILE_STAIRS_UP:
            if self.is_stairs_up_available():
                # 前の層を決定
                target_layer = self._calculate_target_layer_up(world_manager)
                if target_layer:
                    # 前の層の入口座標を計算（通常は下り階段の位置またはデフォルト位置）
                    entrance_pos = target_layer.get_entrance_position()
                    layer_key = f"{target_layer.zone}:{target_layer.biome}:{target_layer.depth}:{target_layer.dimension}"
                    return (entrance_pos[0], entrance_pos[1], layer_key)

        return None

    def _calculate_target_layer_down(self, world_manager: WorldMapManager) -> WorldLayer | None:
        """下り階段でのターゲットレイヤーを計算"""
        if not self.world_layer:
            return None

        current_zone = self.world_layer.zone
        current_biome = self.world_layer.biome
        current_depth = self.world_layer.depth
        current_dimension = self.world_layer.dimension

        # 同じゾーン内での深度増加が基本
        new_depth = current_depth + 1

        # ゾーン境界チェック
        if current_zone == "surface" and new_depth > 10:
            # 地上界の上限を超えたら地下界へ
            new_zone = "underground"
            new_depth = max(11, new_depth)  # 地下界は11階から開始
        elif current_zone == "underground" and new_depth > 50:
            # 地下界の上限を超えたら異界へ
            new_zone = "otherworld"
            new_depth = max(51, new_depth)  # 異界は51階から開始
        elif current_zone == "otherworld" and new_depth > 100:
            # 異界の上限を超えたら天界へ
            new_zone = "heaven"
            new_depth = max(101, new_depth)  # 天界は101階から開始
        else:
            # 同じゾーン内での移動
            new_zone = current_zone

        # 深度上限チェック
        if new_depth > 200:
            return None

        return world_manager.get_or_create_layer(
            new_zone, current_biome, new_depth, current_dimension
        )

    def _calculate_target_layer_up(self, world_manager: WorldMapManager) -> WorldLayer | None:
        """上り階段でのターゲットレイヤーを計算"""
        if not self.world_layer:
            return None

        current_zone = self.world_layer.zone
        current_biome = self.world_layer.biome
        current_depth = self.world_layer.depth
        current_dimension = self.world_layer.dimension

        # 同じゾーン内での深度減少が基本
        new_depth = current_depth - 1

        # 深度下限チェック
        if new_depth < 0:
            return None

        # ゾーン境界チェック（逆方向）
        if current_zone == "underground" and new_depth < 11:
            # 地下界の下限を下回ったら地上界へ
            new_zone = "surface"
            new_depth = min(10, new_depth)  # 地上界は0-10階
        elif current_zone == "otherworld" and new_depth < 51:
            # 異界の下限を下回ったら地下界へ
            new_zone = "underground"
            new_depth = max(11, new_depth)  # 地下界は11階から開始
        elif current_zone == "heaven" and new_depth < 101:
            # 天界の下限を下回ったら異界へ
            new_zone = "otherworld"
            new_depth = max(51, new_depth)  # 異界は51階から開始
        else:
            # 同じゾーン内での移動
            new_zone = current_zone

        return world_manager.get_or_create_layer(
            new_zone, current_biome, new_depth, current_dimension
        )
