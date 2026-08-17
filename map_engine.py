"""
Elona Roguelike Clone - Game Map & Generation (Phase 3)
Steps 21 to 30 implementation.
"""

from __future__ import annotations
import random
from typing import List, Tuple, Optional, Set
import math

from constants import (
    TILE_WALL, TILE_FLOOR, TILE_STAIRS_DOWN, TILE_STAIRS_UP, TILE_WATER, TILE_TRAP
)


class RectRoom:
    """マップ内の部屋を定義するクラス (ステップ21)"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
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
    def __init__(self, width: int, height: int, map_type: str = "dungeon", floor_level: int = 1):
        self.width = width
        self.height = height
        self.map_type = map_type
        self.floor_level = floor_level

        # タイル初期化: 全て壁
        self.tiles = [[TILE_WALL for _ in range(height)] for _ in range(width)]

        # 視界・探索済みフラグ (ステップ26, 27)
        self.visible = [[False for _ in range(height)] for _ in range(width)]
        self.explored = [[False for _ in range(height)] for _ in range(width)]

        # 部屋リスト
        self.rooms: List[RectRoom] = []

        # 階段・開始位置 (ステップ23)
        self.stairs_down_pos: Optional[Tuple[int, int]] = None
        self.stairs_up_pos: Optional[Tuple[int, int]] = None
        self.start_pos: Tuple[int, int] = (int(width / 2), int(height / 2))

        # Proposal 8: 緻密なプロシージャル・ディテール (壁画・血文字・刻印・苔)
        self.micro_details: Dict[Tuple[int, int], Dict[str, Any]] = {}

    def is_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        if not self.is_in_bounds(x, y):
            return False
        tile = self.tiles[x][y]
        return tile not in (TILE_WALL,)

    def is_transparent(self, x: int, y: int) -> bool:
        """光を通すか（FOV計算用）"""
        if not self.is_in_bounds(x, y):
            return False
        return self.tiles[x][y] != TILE_WALL

    def create_room(self, room: RectRoom) -> None:
        """部屋の内部を床にする"""
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.tiles[x][y] = TILE_FLOOR

    def create_h_tunnel(self, x1: int, x2: int, y: int) -> None:
        """水平方向の通路を作る (ステップ22)"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[x][y] = TILE_FLOOR

    def create_v_tunnel(self, y1: int, y2: int, x: int) -> None:
        """垂直方向の通路を作る (ステップ22)"""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[x][y] = TILE_FLOOR

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
                self.tiles[new_x][new_y] = TILE_STAIRS_UP
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

        # 最後の部屋に下り階段を配置 (ステップ23)
        if self.rooms:
            last_x, last_y = self.rooms[-1].center
            self.stairs_down_pos = (last_x, last_y)
            self.tiles[last_x][last_y] = TILE_STAIRS_DOWN

        # 特殊地形・水たまりや罠を配置 (ステップ28)
        for room in self.rooms[1:-1]:
            if random.random() < 0.3:
                rx = random.randint(room.x1 + 1, room.x2 - 1)
                ry = random.randint(room.y1 + 1, room.y2 - 1)
                if self.tiles[rx][ry] == TILE_FLOOR:
                    self.tiles[rx][ry] = TILE_WATER if random.random() < 0.5 else TILE_TRAP

        # Proposal 8: 緻密なプロシージャル・ディテール (壁画・血文字・古代刻印の生成)
        blood_messages = [
            "『ここに眠る者、我が名を呼ぶなかれ…』",
            "『妹よ…すまない、塩を持ってくるのを忘れた…』",
            "『深層に潜む異形の神に目を合わせるな』",
            "『エーテル風が吹く夜、この壁に隠れよ』"
        ]
        mural_descriptions = [
            "古代人が巨大な螺旋を描いた退色した壁画",
            "神ジュアが冒険者に手を差し伸べる神聖な彫刻",
            "黒天使が弓を引く躍動感あるレリーフ",
            "狂気に堕ちた魔法使いの血染めの術式"
        ]
        for room in self.rooms:
            # 確率で壁または床にプロシージャルな詳細を刻む
            if random.random() < 0.4:
                detail_x = random.randint(room.x1, room.x2)
                detail_y = random.randint(room.y1, room.y2)
                is_wall = (self.tiles[detail_x][detail_y] == TILE_WALL)
                if is_wall:
                    self.micro_details[(detail_x, detail_y)] = {
                        "type": "mural",
                        "title": "古代の壁画・彫刻",
                        "description": random.choice(mural_descriptions),
                        "char": "📜"
                    }
                else:
                    self.micro_details[(detail_x, detail_y)] = {
                        "type": "bloodstain",
                        "title": "先人の血文字",
                        "description": random.choice(blood_messages),
                        "char": "🩸"
                    }

    def generate_town(self) -> None:
        """街マップ生成（ステップ25）"""
        self.map_type = "town"
        # 外壁以外をすべて床にする
        for x in range(self.width):
            for y in range(self.height):
                if x == 0 or x == self.width - 1 or y == 0 or y == self.height - 1:
                    self.tiles[x][y] = TILE_WALL
                else:
                    self.tiles[x][y] = TILE_FLOOR

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
                        self.tiles[x][y] = TILE_WALL
                    else:
                        self.tiles[x][y] = TILE_FLOOR
            # 扉を作る
            self.tiles[int((h.x1 + h.x2) / 2)][h.y2 - 1] = TILE_FLOOR

        self.start_pos = (25, 20)

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

    def get_faction_tile_color(self, base_color: Tuple[int, int, int], faction_id: Optional[str]) -> Tuple[int, int, int]:
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
            pass
        return base_color

    def select_dungeon_for_reincarnation(self, player_reinc_count: int) -> Optional[str]:
        """転生ダンジョン選択ロジック (Steps 50, 51)"""
        # TODO: Reincarnation dungeon
        from reincarnation_dungeon_system import REGISTRY as RD_REG, ReincarnationDungeonManager
        RD_REG.load()
        mgr = ReincarnationDungeonManager(RD_REG)
        avail = mgr.get_available_dungeons(player_reinc_count)
        if avail:
            return avail[0].id
        return None


