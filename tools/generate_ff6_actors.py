#!/usr/bin/env python3
"""
FF6風アクタースプライト生成ツール (案2: 歩行スプライト / 案3: 大型ボス)。

Pillowのみでドット絵を生成する:
    - 16色限定パレット (スプライト毎に検証)
    - 1px暗輪郭 (自動アウトライン)
    - 45度左上光源 (上/左端ハイライト)
    - 2段陰影 (下/右端シャドウ)

生成物:
    assets/tiles/tileset_ff6_actors_16x16.png  独立アトラス画像
    assets/tiles/tileset_ff6_actors_16x16.json アトラスメタデータ
    assets/tiles/tileset_def_ff6_actors.json   TileDef断片 (マージはメインが実行)

Note:
    既存の tileset_16x16 / tileset_tiny_rogue_* / tileset_def.json は絶対に
    編集しない (競合回避ルール)。
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "tiles"

ATLAS_PNG_PATH = ASSETS_DIR / "tileset_ff6_actors_16x16.png"
ATLAS_JSON_PATH = ASSETS_DIR / "tileset_ff6_actors_16x16.json"
DEF_JSON_PATH = ASSETS_DIR / "tileset_def_ff6_actors.json"

UNIT = 16  # ベースグリッド単位 (16x16)
BOSS_SIZE = 64  # 大型ボス1フレーム辺り (案3: 画面1/4相当の大型グラフィック)

# 向きインデックス (core/tile_atlas.py の calculate_facing と同一)
DIR_DOWN, DIR_LEFT, DIR_RIGHT, DIR_UP = 0, 1, 2, 3
DIRECTION_COUNT = 4

TRANSPARENT = (0, 0, 0, 0)
OUTLINE_COLOR = (18, 14, 28)

# -------------------------------------------------------------
# ドット絵キャンバス
# -------------------------------------------------------------


class SpriteCanvas:
    """パレット色名でドットを打つための小型キャンバス。"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels: dict[tuple[int, int], str] = {}

    def px(self, x: int, y: int, color: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[(x, y)] = color

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: str) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, color)

    def ellipse(self, cx: int, cy: int, rx: int, ry: int, color: str) -> None:
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                dx = (x - cx) / rx
                dy = (y - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    self.px(x, y, color)

    def hline(self, x0: int, x1: int, y: int, color: str) -> None:
        for x in range(x0, x1 + 1):
            self.px(x, y, color)

    def vline(self, x: int, y0: int, y1: int, color: str) -> None:
        for y in range(y0, y1 + 1):
            self.px(x, y, color)

    def blit_map(self, rows: list[str], palette: dict[str, str]) -> None:
        """文字列ピクセルマップを転写 ('.'は透明)。

        Args:
            rows: 各行が正確に self.width 文字のリスト
            palette: マップ文字 → パレット色名
        """
        assert len(rows) == self.height, f"map rows={len(rows)} != {self.height}"
        for y, row in enumerate(rows):
            assert len(row) == self.width, f"row {y} len={len(row)} != {self.width}"
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                assert ch in palette, f"unknown map char: {ch}"
                self.px(x, y, palette[ch])

    def mirror_x(self) -> None:
        """左右反転 (左向き→右向き変換用)。"""
        self.pixels = {(self.width - 1 - x, y): c for (x, y), c in self.pixels.items()}

    def render(
        self,
        colors: dict[str, tuple[int, int, int]],
        shade: dict[str, str],
        light: dict[str, str],
        outline: tuple[int, int, int] = OUTLINE_COLOR,
    ) -> Image.Image:
        """輪郭＋陰影を施してRGBA画像化する。"""
        shaded: dict[tuple[int, int], str] = {}
        for (x, y), name in self.pixels.items():
            up = (x, y - 1) not in self.pixels
            left = (x - 1, y) not in self.pixels
            down = (x, y + 1) not in self.pixels
            right = (x + 1, y) not in self.pixels
            # 45度左上光源: 上or左が空なら明色
            if up or left:
                name = light.get(name, name)
            # 2段陰影: 下or右が空なら暗色 (右下優先)
            if down or right:
                name = shade.get(name, name)
            shaded[(x, y)] = name

        img = Image.new("RGBA", (self.width, self.height), TRANSPARENT)
        seen: set[tuple[int, int, int, int]] = set()
        for (x, y), name in shaded.items():
            rgba = (*colors[name], 255)
            img.putpixel((x, y), rgba)
            seen.add(rgba)
            # 1px暗輪郭: 隣接する透明ピクセルを埋める
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (nx, ny) in self.pixels:
                    continue
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if img.getpixel((nx, ny))[3] == 0:
                        outline_px = (*outline, 255)
                        img.putpixel((nx, ny), outline_px)
                        seen.add(outline_px)
        if len(seen) > 16:
            raise AssertionError(f"palette overflow: {len(seen)} > 16 colors")
        return img


# -------------------------------------------------------------
# パレット定義 (各16色以内)
# -------------------------------------------------------------

HERO_COLORS = {
    "OUTLINE": OUTLINE_COLOR,
    "HAIR": (122, 76, 42),
    "HAIR_S": (84, 50, 28),
    "BAND": (196, 60, 52),
    "SKIN": (252, 216, 168),
    "SKIN_S": (214, 158, 116),
    "PUPIL": (32, 34, 58),
    "TUNIC": (62, 112, 196),
    "TUNIC_L": (116, 168, 236),
    "TUNIC_S": (38, 72, 140),
    "PANTS": (128, 106, 74),
    "PANTS_S": (94, 76, 52),
    "BOOT": (72, 52, 36),
    "BELT": (214, 176, 80),
}
HERO_MAP = {
    ".": None, "H": "HAIR", "h": "HAIR_S", "R": "BAND", "S": "SKIN",
    "s": "SKIN_S", "k": "PUPIL", "T": "TUNIC", "L": "TUNIC_L", "t": "TUNIC_S",
    "P": "PANTS", "p": "PANTS_S", "B": "BOOT", "G": "BELT",
}
HERO_SHADE = {"HAIR": "HAIR_S", "SKIN": "SKIN_S", "TUNIC": "TUNIC_S", "PANTS": "PANTS_S"}
HERO_LIGHT = {"TUNIC": "TUNIC_L"}

# -------------------------------------------------------------
# プレイヤー歩行 (案2: 4方向×3フレーム)
# -------------------------------------------------------------

HERO_HEAD_DOWN = [
    "................",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...hRRRRRRRRh...",
    "...hSSSSSSSSh...",
    "...hSSkSSkSSh...",
    "....SSssssSS....",
]
HERO_HEAD_UP = [
    "................",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...hHHHRRHHHh...",
    "...hHHHHHHHHh...",
    "....HHhhhhHH....",
]
HERO_TORSO = [
    "....tTTTTTTt....",
    "...tTLTTTTLTt...",
    "...tTTTTTTTTt...",
    "...tTGGGGGGTt...",
    "....ttTTTTtt....",
]
HERO_LEGS_IDLE = [
    ".....PP..PP.....",
    ".....PP..PP.....",
    ".....BB..BB.....",
    ".....BB..BB.....",
]
HERO_LEGS_STEP_L = [
    "....PP...PP.....",
    "...PP....PP.....",
    "...BB....BB.....",
    "...BB...........",
]
HERO_LEGS_STEP_R = [
    ".....PP...PP....",
    ".....PP....PP...",
    ".....BB....BB...",
    "...........BB...",
]
HERO_TORSO_SIDE = [
    "....tTTTTTt.....",
    "....tTLTTTt.....",
    "....tTTTTTt.....",
    "....tGGGGt......",
    "....tttttt......",
]
HERO_LEGS_SIDE_IDLE = [
    ".....PPPPP......",
    ".....PPPPP......",
    ".....BBBBB......",
    ".....BBBBB......",
]
HERO_LEGS_SIDE_STEP_L = [
    "....PPP..PP.....",
    "....PPP..PP.....",
    "...BBB...BB.....",
    "...BB...........",
]
HERO_LEGS_SIDE_STEP_R = [
    ".....PP..PPP....",
    ".....PP..PPP....",
    "....BB....BBB...",
    "...........BB...",
]


def _hero_frame(head: list[str], torso: list[str], legs: list[str]) -> list[str]:
    """頭＋胴＋脚を結合して16x16マップ化する。"""
    rows = head + torso + legs
    assert len(rows) == 16
    return rows


def build_hero_frames() -> dict[int, list[Image.Image]]:
    """プレイヤー歩行フレーム {direction: [frame0, frame1, frame2]} を生成。"""
    down = [
        _hero_frame(HERO_HEAD_DOWN, HERO_TORSO, HERO_LEGS_IDLE),
        _hero_frame(HERO_HEAD_DOWN, HERO_TORSO, HERO_LEGS_STEP_L),
        _hero_frame(HERO_HEAD_DOWN, HERO_TORSO, HERO_LEGS_STEP_R),
    ]
    up = [
        _hero_frame(HERO_HEAD_UP, HERO_TORSO, HERO_LEGS_IDLE),
        _hero_frame(HERO_HEAD_UP, HERO_TORSO, HERO_LEGS_STEP_L),
        _hero_frame(HERO_HEAD_UP, HERO_TORSO, HERO_LEGS_STEP_R),
    ]
    profile_head = _hero_profile_head()
    left = [
        _hero_frame(profile_head, HERO_TORSO_SIDE, HERO_LEGS_SIDE_IDLE),
        _hero_frame(profile_head, HERO_TORSO_SIDE, HERO_LEGS_SIDE_STEP_L),
        _hero_frame(profile_head, HERO_TORSO_SIDE, HERO_LEGS_SIDE_STEP_R),
    ]
    right = []
    for rows in left:
        cv = SpriteCanvas(UNIT, UNIT)
        cv.blit_map(rows, HERO_MAP)
        cv.mirror_x()
        right.append(cv)
    result: dict[int, list[Image.Image]] = {DIR_DOWN: [], DIR_UP: [], DIR_LEFT: [], DIR_RIGHT: []}
    for frames, direction in ((down, DIR_DOWN), (up, DIR_UP), (left, DIR_LEFT)):
        for rows in frames:
            cv = SpriteCanvas(UNIT, UNIT)
            cv.blit_map(rows, HERO_MAP)
            result[direction].append(cv.render(HERO_COLORS, HERO_SHADE, HERO_LIGHT))
    for cv in right:
        result[DIR_RIGHT].append(cv.render(HERO_COLORS, HERO_SHADE, HERO_LIGHT))
    return result


def _hero_profile_head() -> list[str]:
    """左向きの頭部マップ。"""
    return [
        "................",
        "....HHHHHHH.....",
        "...HHHHHHHHH....",
        "...HRRRRRRHh....",
        "...hSSSSSShH....",
        "...hSkSSSShH....",
        "....SsssssH.....",
    ]


# -------------------------------------------------------------
# 敵4種 (案2: goblin / wolf / skeleton / bat ×2フレーム)
# -------------------------------------------------------------

GOBLIN_COLORS = {
    "OUTLINE": OUTLINE_COLOR,
    "SKIN": (96, 168, 72),
    "SKIN_S": (60, 116, 48),
    "SKIN_L": (148, 208, 108),
    "EYE": (220, 72, 64),
    "TOOTH": (232, 228, 208),
    "CLOTH": (150, 104, 60),
    "CLOTH_S": (104, 68, 40),
    "CLUB": (128, 88, 48),
    "CLUB_S": (88, 58, 32),
}
GOBLIN_MAP = {
    ".": None, "G": "SKIN", "g": "SKIN_S", "L": "SKIN_L", "E": "EYE",
    "W": "TOOTH", "C": "CLOTH", "c": "CLOTH_S", "M": "CLUB", "m": "CLUB_S",
}
GOBLIN_SHADE = {"SKIN": "SKIN_S", "CLOTH": "CLOTH_S", "CLUB": "CLUB_S"}
GOBLIN_LIGHT = {"SKIN": "SKIN_L"}

GOBLIN_HEAD_DOWN = [
    "................",
    "....gGGGGGGg....",
    "..G.GGGGGGGG.G..",
    ".GGGGGGGGGGGGGG.",
    ".GGGGGGGGGGGGGg.",
    "..GGEGGGGGGEGG..",
    "..gGGGGWWGGGGg..",
]
GOBLIN_HEAD_UP = [
    "................",
    "....gGGGGGGg....",
    "..G.GGGGGGGG.G..",
    ".GGGGGGGGGGGGGG.",
    ".GGGGGGGGGGGGGg.",
    "..GGGGGGGGGGGG..",
    "..gGGGGGGGGGGg..",
]
GOBLIN_BODY_DOWN = [
    "....CCGGGGCC....",
    "...GCCGGGGCCG...",
    "...gCCccccCCg...",
    "....ccCCCCcc....",
]
GOBLIN_LEGS_DOWN_F0 = [
    ".....Gg..Gg.....",
    ".....Gg..Gg.....",
    ".....Gg..Gg.....",
    ".....gg..gg.....",
    "....gg....gg....",
]
GOBLIN_LEGS_DOWN_F1 = [
    "....Gg...Gg.....",
    "....Gg....Gg....",
    "...Gg.....Gg....",
    "...gg.....gg....",
    "................",
]
GOBLIN_BODY_F1 = [
    "....CCGGGGCC....",
    "..MGCCGGGGCC....",
    "...gCCccccCCg...",
    "....ccCCCCcc....",
]
GOBLIN_HEAD_LEFT = [
    "................",
    "....gGGGGGg.....",
    "..G.GGGGGGG.....",
    ".GGGGGGGGGGG....",
    ".GGGGGGGGGGGg...",
    "..GGEGGGGGg.....",
    "..gGGGWWGGg.....",
]
GOBLIN_BODY_LEFT = [
    "....CCGGGc......",
    "...MCCGGGc......",
    "...mCCcccG......",
    "....ccCCC.......",
]
GOBLIN_LEGS_LEFT_F0 = [
    ".....GgGg.......",
    ".....GgGg.......",
    ".....GgGg.......",
    ".....gggg.......",
    "................",
]
GOBLIN_LEGS_LEFT_F1 = [
    "....Gg..Gg......",
    "....Gg...Gg.....",
    "...Gg.....Gg....",
    "...gg.....gg....",
    "................",
]


def build_goblin_frames() -> dict[int, list[Image.Image]]:
    """ゴブリン (2フレーム×4方向)。"""
    down = [
        GOBLIN_HEAD_DOWN + GOBLIN_BODY_DOWN + GOBLIN_LEGS_DOWN_F0,
        GOBLIN_HEAD_DOWN + GOBLIN_BODY_F1 + GOBLIN_LEGS_DOWN_F1,
    ]
    up = [
        GOBLIN_HEAD_UP + GOBLIN_BODY_DOWN + GOBLIN_LEGS_DOWN_F0,
        GOBLIN_HEAD_UP + GOBLIN_BODY_F1 + GOBLIN_LEGS_DOWN_F1,
    ]
    left = [
        GOBLIN_HEAD_LEFT + GOBLIN_BODY_LEFT + GOBLIN_LEGS_LEFT_F0,
        GOBLIN_HEAD_LEFT + GOBLIN_BODY_LEFT + GOBLIN_LEGS_LEFT_F1,
    ]
    return _mirror_quadruplet(down, up, left, GOBLIN_MAP, GOBLIN_COLORS, GOBLIN_SHADE, GOBLIN_LIGHT)


def _mirror_quadruplet(
    down: list[list[str]],
    up: list[list[str]],
    left: list[list[str]],
    mapping: dict[str, str | None],
    colors: dict[str, tuple[int, int, int]],
    shade: dict[str, str],
    light: dict[str, str],
) -> dict[int, list[Image.Image]]:
    """down/up/left の文字マップ群から4方向分の画像を生成 (right=left鏡像)。"""
    result: dict[int, list[Image.Image]] = {d: [] for d in range(DIRECTION_COUNT)}
    for rows_list, direction in ((down, DIR_DOWN), (up, DIR_UP), (left, DIR_LEFT)):
        for rows in rows_list:
            cv = SpriteCanvas(UNIT, UNIT)
            cv.blit_map(rows, mapping)
            result[direction].append(cv.render(colors, shade, light))
    for rows in left:
        cv = SpriteCanvas(UNIT, UNIT)
        cv.blit_map(rows, mapping)
        cv.mirror_x()
        result[DIR_RIGHT].append(cv.render(colors, shade, light))
    return result


WOLF_COLORS = {
    "OUTLINE": OUTLINE_COLOR,
    "FUR": (150, 148, 160),
    "FUR_S": (104, 102, 118),
    "FUR_L": (196, 196, 208),
    "BELLY": (224, 222, 214),
    "EYE": (255, 208, 64),
    "NOSE": (32, 30, 40),
}
WOLF_MAP = {
    ".": None, "F": "FUR", "f": "FUR_S", "L": "FUR_L", "W": "BELLY",
    "Y": "EYE", "N": "NOSE",
}
WOLF_SHADE = {"FUR": "FUR_S"}
WOLF_LIGHT = {"FUR": "FUR_L"}

WOLF_HEAD_FRONT = [
    "................",
    "................",
    "..FF......FF....",
    "..FFF....FFF....",
    "..FFFFFFFF......",
    "..FFFFFFFFF.....",
    "..FYFFFFYF......",
    "..FFWNNWFF......",
    "...FWWWWFF......",
]
WOLF_BODY_FRONT_F0 = [
    "..FFFFFFFFFF....",
    "...FFFFFFFF.....",
    "...FFffffFF.....",
    "...FF....FF.....",
    "...FF....FF.....",
    "...ff....ff.....",
    "................",
]
WOLF_BODY_FRONT_F1 = [
    "..FFFFFFFFFF....",
    "...FFFFFFFF.....",
    "...FFffffFF.....",
    "..FF......FF....",
    "..FF......FF....",
    "..ff......ff....",
    "................",
]
WOLF_BODY_BACK_F0 = [
    "..FFFFFFFFFF....",
    "..FFFFFFFFFf....",
    "..FFffffFF.Ff...",
    "...FF..FF..Ff...",
    "...FF..FF...f...",
    "...ff..ff.......",  # noqa: E501
    "................",
]
WOLF_SIDE_HEAD = [
    "................",
    "................",
    ".FF.............",
    ".FFF............",
    ".FFFF...........",
    ".FFFFF..........",
    ".FFYFF..........",
    "..FFFNFF.FFFF...",
]
WOLF_SIDE_BODY_F0 = [
    "...FFFFFFFFF....",
    "..FFFFFFFFFFFF..",
    "..FWWWWWWWFFF...",
    "...FFfFFfFFfF...",
    "...FF.FF.FF.F...",
    "...FF.FF.FF.F...",
    "...ff.ff.ff.ff..",
    "................",
]
WOLF_SIDE_BODY_F1 = [
    "...FFFFFFFFF....",
    "..FFFFFFFFFFFF..",
    "..FWWWWWWWFFF...",
    "...FFfFFfFFfF...",
    "..FF..FF..FF....",
    "..FF..FF..FF....",
    "..ff..ff..ff....",
    "................",
]


def build_wolf_frames() -> dict[int, list[Image.Image]]:
    """狼 (2フレーム×4方向: 左右は側面、上下は正面/背面)。"""
    left = [
        WOLF_SIDE_HEAD + WOLF_SIDE_BODY_F0,
        WOLF_SIDE_HEAD + WOLF_SIDE_BODY_F1,
    ]
    down = [
        WOLF_HEAD_FRONT + WOLF_BODY_FRONT_F0,
        WOLF_HEAD_FRONT + WOLF_BODY_FRONT_F1,
    ]
    up = [
        WOLF_HEAD_FRONT + WOLF_BODY_BACK_F0,
        WOLF_HEAD_FRONT + WOLF_BODY_BACK_F0,
    ]
    return _mirror_quadruplet(down, up, left, WOLF_MAP, WOLF_COLORS, WOLF_SHADE, WOLF_LIGHT)


SKELETON_COLORS = {
    "OUTLINE": OUTLINE_COLOR,
    "BONE": (232, 226, 204),
    "BONE_S": (176, 166, 140),
    "SOCKET": (30, 28, 40),
    "GLOW": (200, 80, 60),
    "RAG": (96, 84, 120),
    "RAG_S": (64, 56, 84),
}
SKELETON_MAP = {
    ".": None, "B": "BONE", "b": "BONE_S", "K": "SOCKET", "R": "GLOW",
    "C": "RAG", "c": "RAG_S",
}
SKELETON_SHADE = {"BONE": "BONE_S", "RAG": "RAG_S"}
SKELETON_LIGHT: dict[str, str] = {}

SKELETON_HEAD_DOWN = [
    "................",
    "....BBBBBBBB....",
    "...BBBBBBBBBB...",
    "...BKKBBBBKKB...",
    "...BKRBBBBRKB...",
    "...bBBBBBBBBb...",
    "....bBbBBbBb....",
]
SKELETON_TORSO_F0 = [
    ".....bBBBBb.....",
    "..B.BbBBBBbB.B..",
    "..B.BbBBBBbB.B..",
    "..B..bBBBBb..B..",
    "....CBBBBBBC....",
]
SKELETON_LEGS_F0 = [
    ".....bB..Bb.....",
    ".....bB..Bb.....",
    ".....bB..Bb.....",
    "....bb....bb....",
]
SKELETON_LEGS_F1 = [
    "....bB...Bb.....",
    "....bB...Bb.....",
    "...bB.....Bb....",
    "...bb.....bb....",
]
SKELETON_HEAD_UP = [
    "................",
    "....BBBBBBBB....",
    "...BBBBBBBBBB...",
    "...BBBBBBBBBB...",
    "...BBbBBBBbBB...",
    "...bBBBBBBBBb...",
    "....bBBBBBBb....",
]
SKELETON_HEAD_LEFT = [
    "................",
    "....BBBBBB......",
    "...BBBBBBBB.....",
    "...KKBBBBBB.....",
    "...RKBBBBBb.....",
    "...bBBBBBBb.....",
    "...bBbBbBbB.....",
]
SKELETON_TORSO_LEFT = [
    "....bBBBBb......",
    "....BbBBbB..B...",
    "....BbBBbB..B...",
    ".....bBBb...B...",
    "....CBBBBb......",
]
SKELETON_LEGS_LEFT_F0 = [
    ".....bBbB.......",
    ".....bBbB.......",
    ".....bBbB.......",
    "....bb..bb......",
]
SKELETON_LEGS_LEFT_F1 = [
    "....bB..bB......",
    "...bB....bB.....",
    "...bb....bb.....",
    "................",
]


def build_skeleton_frames() -> dict[int, list[Image.Image]]:
    """スケルトン (2フレーム×4方向)。"""
    down = [
        SKELETON_HEAD_DOWN + SKELETON_TORSO_F0 + SKELETON_LEGS_F0,
        SKELETON_HEAD_DOWN + SKELETON_TORSO_F0 + SKELETON_LEGS_F1,
    ]
    up = [
        SKELETON_HEAD_UP + SKELETON_TORSO_F0 + SKELETON_LEGS_F0,
        SKELETON_HEAD_UP + SKELETON_TORSO_F0 + SKELETON_LEGS_F1,
    ]
    left = [
        SKELETON_HEAD_LEFT + SKELETON_TORSO_LEFT + SKELETON_LEGS_LEFT_F0,
        SKELETON_HEAD_LEFT + SKELETON_TORSO_LEFT + SKELETON_LEGS_LEFT_F1,
    ]
    return _mirror_quadruplet(down, up, left, SKELETON_MAP, SKELETON_COLORS, SKELETON_SHADE, SKELETON_LIGHT)


BAT_COLORS = {
    "OUTLINE": OUTLINE_COLOR,
    "BODY": (120, 80, 180),
    "BODY_S": (84, 54, 132),
    "WING": (168, 120, 220),
    "MEMBRANE": (92, 60, 148),
    "EYE": (255, 232, 92),
    "FANG": (240, 240, 240),
}
BAT_MAP = {
    ".": None, "P": "BODY", "p": "BODY_S", "L": "WING", "M": "MEMBRANE",
    "Y": "EYE", "W": "FANG",
}
BAT_SHADE = {"BODY": "BODY_S", "WING": "MEMBRANE"}
BAT_LIGHT: dict[str, str] = {}

BAT_F0 = [
    "................",
    "................",
    ".M...........M..",
    ".MM.........MM..",
    "..MM..PPPP..MM..",
    "..MMM.PPPP.MMM..",
    "...MLLPpPLLM....",
    "...ML.PppP.LM...",
    "....M.PYpYP.M...",
    "......PWpWP.....",
    "......PPpPP.....",
    ".......pPPp.....",
    ".......PpP......",
    "................",
    "................",
    "................",
]
BAT_F1 = [
    "................",
    "................",
    "................",
    "................",
    "......PPPP......",
    ".MM..PPPPPP..MM.",
    ".MMM.PpYpYP.MMM.",
    "..MMM.PppP.MMM..",
    "..MML.PYpYPLMM..",  # noqa: E501
    "...ML.PWpWP.LM..",
    "....M.PPpPP.M...",
    ".......PpP......",
    ".......pPp......",
    "................",
    "................",
    "................",
]


def build_bat_frames() -> dict[int, list[Image.Image]]:
    """コウモリ (翼のはばたき2フレーム、対称形のため全方向同形)。"""
    frames = []
    for rows in (BAT_F0, BAT_F1):
        cv = SpriteCanvas(UNIT, UNIT)
        cv.blit_map(rows, BAT_MAP)
        frames.append(cv.render(BAT_COLORS, BAT_SHADE, BAT_LIGHT))
    return {d: list(frames) for d in range(DIRECTION_COUNT)}


# -------------------------------------------------------------
# 大型ボス (案3: 64x64×2フレーム, 金＋ラピスラズリ配色)
# -------------------------------------------------------------

BOSS_COLORS = {
    "OUTLINE": (12, 8, 22),
    "GOLD_L": (255, 232, 140),
    "GOLD": (232, 192, 72),
    "GOLD_S": (160, 112, 36),
    "LAPIS": (48, 80, 200),
    "LAPIS_L": (96, 140, 255),
    "LAPIS_S": (28, 48, 130),
    "CAPE": (44, 30, 78),
    "CAPE_S": (26, 16, 48),
    "GLOW": (255, 240, 170),
}
BOSS_SHADE = {"GOLD": "GOLD_S", "LAPIS": "LAPIS_S", "LAPIS_L": "LAPIS", "CAPE": "CAPE_S"}
BOSS_LIGHT = {"GOLD": "GOLD_L", "LAPIS": "LAPIS_L"}


class BossPainter:
    """対称鏡写しで64x64の大型ボスを描くペインター。"""

    def __init__(self, size: int):
        self.size = size
        self.cv = SpriteCanvas(size, size)

    def sym_rect(self, x0: int, y0: int, x1: int, y1: int, color: str) -> None:
        """左右対称の矩形ペア (指定矩形＋鏡像矩形を個別に描く)。"""
        w = self.size - 1
        self.cv.rect(x0, y0, x1, y1, color)
        if w - x1 != x0:
            self.cv.rect(w - x1, y0, w - x0, y1, color)

    def sym_px(self, x: int, y: int, color: str) -> None:
        self.cv.px(x, y, color)
        self.cv.px(self.size - 1 - x, y, color)


def _paint_boss_down(painter: BossPainter, frame: int) -> None:
    """正面 (dir=0)。frame0: 両臂下げ / frame1: 両臂上げ＋ Cape展開。"""
    cv = painter.cv
    arms_up = frame == 1

    # 背面ケープ (最下層、frame1で展開)
    flare = 3 if arms_up else 0
    for y in range(24, 59):
        spread = (y - 24) // 4 + flare
        x0 = 20 - spread
        x1 = 43 + spread
        cv.hline(x0, x0, y, "CAPE_S")
        cv.hline(x1, x1, y, "CAPE_S")
        cv.hline(x0 + 1, x1 - 1, y, "CAPE")

    # 角 (金の双角)
    for i in range(8):
        painter.sym_rect(25 - i, 8 - i, 26 - i, 9 - i, "GOLD")

    # 冠帯＋宝石
    painter.sym_rect(23, 9, 40, 12, "GOLD")
    painter.sym_rect(30, 10, 33, 11, "LAPIS_L")

    # 頭部兜
    painter.sym_rect(25, 13, 38, 21, "LAPIS_S")
    # 顔スリット＋灼眼
    painter.sym_rect(27, 16, 36, 18, "CAPE_S")
    if arms_up:
        painter.sym_rect(28, 16, 29, 17, "GLOW")
        painter.sym_rect(34, 16, 35, 17, "GLOW")
    else:
        painter.sym_px(28, 17, "GLOW")
        painter.sym_px(35, 17, "GLOW")

    # 肩甲 (金の大パールドン)
    painter.cv.ellipse(15, 27, 7, 5, "GOLD")
    painter.cv.ellipse(48, 27, 7, 5, "GOLD")
    painter.cv.ellipse(15, 26, 5, 3, "GOLD_L")
    painter.cv.ellipse(48, 26, 5, 3, "GOLD_L")

    # 腕＋篭手
    if arms_up:
        painter.sym_rect(9, 20, 14, 31, "LAPIS_S")
        painter.sym_rect(8, 13, 15, 20, "GOLD")
    else:
        painter.sym_rect(9, 29, 14, 39, "LAPIS_S")
        painter.sym_rect(8, 39, 15, 45, "GOLD")

    # 胴体鎧＋金縁
    painter.sym_rect(23, 22, 40, 40, "LAPIS")
    painter.sym_rect(31, 22, 32, 40, "GOLD")
    painter.sym_rect(29, 27, 34, 31, "LAPIS_L")
    painter.sym_px(31, 29, "GOLD")

    # 腰帯＋袴
    painter.sym_rect(22, 40, 41, 42, "GOLD_S")
    painter.sym_rect(21, 43, 42, 56, "LAPIS_S")
    painter.sym_rect(23, 45, 40, 54, "CAPE")
    painter.sym_rect(21, 55, 42, 56, "GOLD")

    # 浮遊感の輝点
    painter.sym_px(26, 59, "GOLD")
    painter.sym_px(30, 60, "GOLD_S")
    if arms_up:
        painter.sym_px(6, 10, "GOLD_L")
        painter.sym_px(4, 34, "GOLD_L")
        painter.sym_px(10, 54, "GOLD_L")


def _paint_boss_up(painter: BossPainter, frame: int) -> None:
    """背面 (dir=3): ケープ全面＋金の紋章。"""
    cv = painter.cv
    _paint_boss_down(painter, frame)
    # 背面は兜とケープで覆われる: 顔スリットを塞ぎ紋章を描く
    painter.sym_rect(27, 16, 36, 18, "CAPE_S")
    painter.sym_rect(28, 30, 35, 37, "GOLD")
    painter.sym_px(31, 33, "LAPIS_L")
    painter.sym_rect(24, 13, 39, 21, "LAPIS_S")
    painter.sym_rect(25, 9, 38, 12, "GOLD")
    # ケープ全体を背中で見せる
    for y in range(24, 59):
        spread = (y - 24) // 4
        cv.hline(19 - spread, 44 + spread, y, "CAPE" if frame == 0 else "CAPE_S")


def _paint_boss_left(painter: BossPainter, frame: int) -> None:
    """側面 (dir=1, 左向き): 片腕とケープの流れ。"""
    cv = painter.cv
    arms_up = frame == 1

    # ケープ (後方へ流れる)
    for y in range(24, 59):
        tail = (y - 24) // 3
        cv.hline(24, 44 + tail, y, "CAPE_S" if y < 26 else "CAPE")
    painter.cv.vline(44, 24, 58, "CAPE_S")

    # 角 (左寄り)
    for i in range(8):
        cv.rect(20 - i, 8 - i, 21 - i, 9 - i, "GOLD")
    cv.px(19, 1, "GOLD_L")

    # 冠＋兜
    cv.rect(22, 9, 39, 12, "GOLD")
    cv.rect(25, 13, 38, 21, "LAPIS_S")
    cv.rect(24, 16, 30, 18, "CAPE_S")
    cv.px(25, 17, "GLOW")
    cv.px(26, 17, "GLOW" if arms_up else "LAPIS_S")

    # 肩甲 (左に大きく)
    cv.ellipse(18, 27, 8, 5, "GOLD")
    cv.ellipse(18, 26, 6, 3, "GOLD_L")

    # 腕
    if arms_up:
        cv.rect(14, 20, 20, 31, "LAPIS_S")
        cv.rect(12, 13, 21, 20, "GOLD")
    else:
        cv.rect(14, 29, 20, 39, "LAPIS_S")
        cv.rect(12, 39, 21, 45, "GOLD")

    # 胴体
    cv.rect(24, 22, 40, 40, "LAPIS")
    cv.rect(24, 22, 26, 40, "GOLD")
    cv.rect(30, 27, 36, 31, "LAPIS_L")

    # 腰帯＋袴
    cv.rect(23, 40, 41, 42, "GOLD_S")
    cv.rect(22, 43, 41, 56, "LAPIS_S")
    cv.rect(24, 45, 39, 54, "CAPE")
    cv.rect(22, 55, 41, 56, "GOLD")
    painter.sym_px(26, 59, "GOLD")
    if arms_up:
        cv.px(9, 10, "GOLD_L")


def build_boss_frames() -> dict[int, list[Image.Image]]:
    """大型ボス (2フレーム×4方向、各64x64)。"""
    result: dict[int, list[Image.Image]] = {d: [] for d in range(DIRECTION_COUNT)}
    painters = {
        DIR_DOWN: _paint_boss_down,
        DIR_UP: _paint_boss_up,
        DIR_LEFT: _paint_boss_left,
    }
    left_frames: list[Image.Image] = []
    for direction, painter_fn in painters.items():
        for frame in range(2):
            painter = BossPainter(BOSS_SIZE)
            painter_fn(painter, frame)
            img = painter.cv.render(BOSS_COLORS, BOSS_SHADE, BOSS_LIGHT, outline=(12, 8, 22))
            result[direction].append(img)
            if direction == DIR_LEFT:
                left_frames.append(img)
    for img in left_frames:
        mirrored = img.transpose(Image.FLIP_LEFT_RIGHT)
        result[DIR_RIGHT].append(mirrored)
    return result


# -------------------------------------------------------------
# アトラス組み立て＋出力
# -------------------------------------------------------------

# (TileDef ID / file key, フレーム画像群, fps)
SPEC_FPS = {
    "FF6_HERO": 8,
    "FF6_GOBLIN": 6,
    "FF6_WOLF": 6,
    "FF6_SKELETON": 6,
    "FF6_BAT": 8,
    "FF6_BOSS": 4,
}


def build_atlas() -> tuple[Image.Image, dict]:
    """全アクターを1枚アトラスへ配置し (画像, メタデータ) を返す。"""
    families = {
        "FF6_HERO": build_hero_frames(),
        "FF6_GOBLIN": build_goblin_frames(),
        "FF6_WOLF": build_wolf_frames(),
        "FF6_SKELETON": build_skeleton_frames(),
        "FF6_BAT": build_bat_frames(),
        "FF6_BOSS": build_boss_frames(),
    }

    # 配置レイアウト: 1行目=歩行ヒーロー, 2行目=敵4種, 3行目以降=大型ボス
    placements: dict[str, tuple[int, int]] = {
        "FF6_HERO": (0, 0),
        "FF6_GOBLIN": (0, UNIT * DIRECTION_COUNT),
        "FF6_WOLF": (UNIT * 2, UNIT * DIRECTION_COUNT),
        "FF6_SKELETON": (UNIT * 4, UNIT * DIRECTION_COUNT),
        "FF6_BAT": (UNIT * 6, UNIT * DIRECTION_COUNT),
        "FF6_BOSS": (0, UNIT * 8),
    }

    atlas_w = UNIT * 8
    hero_row_h = UNIT * DIRECTION_COUNT
    boss_frames = families["FF6_BOSS"]
    boss_frame_w = boss_frames[DIR_DOWN][0].width
    boss_row_h = boss_frames[DIR_DOWN][0].height
    atlas_h = UNIT * 8 + boss_row_h * DIRECTION_COUNT

    img = Image.new("RGBA", (atlas_w, atlas_h), TRANSPARENT)
    meta_tiles: dict[str, dict] = {}
    for tile_id, frames_by_dir in families.items():
        x0, y0 = placements[tile_id]
        frame_w = frames_by_dir[DIR_DOWN][0].width
        frame_h = frames_by_dir[DIR_DOWN][0].height
        frame_count = len(frames_by_dir[DIR_DOWN])
        for direction, images in frames_by_dir.items():
            assert len(images) == frame_count, f"{tile_id} dir{direction} frame数不整合"
            for frame_idx, image in enumerate(images):
                img.paste(
                    image,
                    (x0 + frame_idx * frame_w, y0 + direction * frame_h),
                )
        meta_tiles[tile_id] = {
            "x": x0,
            "y": y0,
            "width": frame_w * frame_count,
            "height": frame_h * DIRECTION_COUNT,
            "variants": 1,
            "animated": True,
            "frames": frame_count,
            "fps": SPEC_FPS[tile_id],
            "directions": DIRECTION_COUNT,
        }

    meta = {
        "tile_size": UNIT,
        "atlas_width": atlas_w,
        "atlas_height": atlas_h,
        "tiles": meta_tiles,
    }
    return img, meta


def build_def_fragment(atlas_meta: dict) -> dict:
    """tileset_def.json と同スキーマのTileDef断片を組み立てる。"""
    tiles: dict[str, dict] = {}
    for tile_id, region in atlas_meta["tiles"].items():
        tiles[tile_id] = {
            "file": tile_id,
            "atlas_scale": "ff6_16",
            "variants": region["variants"],
            "variant_width": region["width"] // region["frames"],
            "animated": region["animated"],
            "frames": region["frames"],
            "fps": region["fps"],
            "frame_width": region["width"] // region["frames"],
            "directions": region["directions"],
            "states": ["idle", "walk", "attack"],
            "anchor_x": 0.5,
            "anchor_y": 1.0,
        }
    return {
        "version": "ff6-actors-1",
        "tile_size": UNIT,
        "tiles": tiles,
    }


# -------------------------------------------------------------
# 検証
# -------------------------------------------------------------


def validate(atlas_png: Image.Image, atlas_meta: dict, def_fragment: dict) -> list[str]:
    """生成物の整合性検証。違反があれば例外を送出する。

    検証項目:
        1. 全TileDefのfileキーがアトラスJSONに存在
        2. 全方向×全フレームのUVがアトラス範囲内 (特に64pxボス)
        3. アトラス領域の重複なし
        4. アトラス画像サイズとメタデータの一致
    """
    errors: list[str] = []
    atlas_w, atlas_h = atlas_png.size
    meta_tiles = atlas_meta["tiles"]

    for tile_id, td in def_fragment["tiles"].items():
        # 検証1: fileキー存在
        if td["file"] not in meta_tiles:
            errors.append(f"{tile_id}: file '{td['file']}' がアトラスJSONに存在しない")
            continue
        region = meta_tiles[td["file"]]
        frame_w = td["frame_width"]
        frame_h = region["height"] // region["directions"]

        # 検証2: UV範囲 (最大フレーム×最大方向)
        for frame in range(td["frames"]):
            for direction in range(td["directions"]):
                uv_x = region["x"] + frame * frame_w
                uv_y = region["y"] + direction * frame_h
                if uv_x + frame_w > atlas_w or uv_y + frame_h > atlas_h:
                    errors.append(
                        f"{tile_id}: UV範囲外 frame={frame} dir={direction} "
                        f"uv=({uv_x},{uv_y},{frame_w},{frame_h})"
                    )

        # 64pxボスの明示チェック (案3)
        if tile_id == "FF6_BOSS":
            if frame_w != BOSS_SIZE or frame_h != BOSS_SIZE:
                errors.append(f"FF6_BOSS: フレームサイズが{frame_w}x{frame_h} (期待: {BOSS_SIZE}x{BOSS_SIZE})")
            max_uv_x = region["x"] + (td["frames"] - 1) * frame_w + frame_w
            max_uv_y = region["y"] + (td["directions"] - 1) * frame_h + frame_h
            if max_uv_x > atlas_w or max_uv_y > atlas_h:
                errors.append(f"FF6_BOSS: 64px UV範囲外 max=({max_uv_x},{max_uv_y}) atlas=({atlas_w},{atlas_h})")

    # 検証3: 領域重複チェック
    regions = [(tid, r) for tid, r in meta_tiles.items()]
    for i, (tid_a, ra) in enumerate(regions):
        for tid_b, rb in regions[i + 1 :]:
            if (
                ra["x"] < rb["x"] + rb["width"]
                and rb["x"] < ra["x"] + ra["width"]
                and ra["y"] < rb["y"] + rb["height"]
                and rb["y"] < ra["y"] + ra["height"]
            ):
                errors.append(f"領域重複: {tid_a} と {tid_b}")

    # 検証4: 画像サイズ一致
    if (atlas_meta["atlas_width"], atlas_meta["atlas_height"]) != (atlas_w, atlas_h):
        errors.append(
            f"アトラスサイズ不一致: meta=({atlas_meta['atlas_width']},{atlas_meta['atlas_height']}) png=({atlas_w},{atlas_h})"
        )
    if atlas_png.getextrema()[3][0] != 0 and atlas_png.mode != "RGBA":
        errors.append("アトラスがRGBAでない")

    if errors:
        raise AssertionError("検証失敗:\n" + "\n".join(errors))
    return [
        f"検証OK: {len(def_fragment['tiles'])} TileDef / {len(meta_tiles)} file keys / "
        f"atlas {atlas_w}x{atlas_h} / 全UV範囲内 (64pxボス含む)"
    ]


def main() -> None:
    """生成エントリポイント。"""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    img, atlas_meta = build_atlas()
    def_fragment = build_def_fragment(atlas_meta)

    for line in validate(img, atlas_meta, def_fragment):
        print(line)

    img.save(ATLAS_PNG_PATH)
    ATLAS_JSON_PATH.write_text(json.dumps(atlas_meta, indent=2, ensure_ascii=False) + "\n")
    DEF_JSON_PATH.write_text(json.dumps(def_fragment, indent=2, ensure_ascii=False) + "\n")

    # JSON妥当性の再読込確認
    json.loads(ATLAS_JSON_PATH.read_text())
    json.loads(DEF_JSON_PATH.read_text())

    print(f"出力: {ATLAS_PNG_PATH.relative_to(PROJECT_ROOT)}")
    print(f"出力: {ATLAS_JSON_PATH.relative_to(PROJECT_ROOT)}")
    print(f"出力: {DEF_JSON_PATH.relative_to(PROJECT_ROOT)}")
    for tile_id, region in atlas_meta["tiles"].items():
        print(
            f"  {tile_id}: pos=({region['x']},{region['y']}) size={region['width']}x{region['height']} "
            f"frames={region['frames']} fps={region['fps']} directions={region['directions']}"
        )


if __name__ == "__main__":
    main()
