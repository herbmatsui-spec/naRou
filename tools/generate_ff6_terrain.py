"""
FF6風テラインタイル生成ツール (T11 案1: タイル刷新)

16色限定パレット + 1px暗輪郭 + 45度左上光源 + 2段陰影 + ハッチング/2色ディザ質感で
FF6風のドット絵タイルを生成し、独立アトラス (PNG) とアトラスメタデータ / タイル定義
フラグメント (JSON) を出力する。

出力:
  - assets/tiles/tileset_ff6_terrain_16x16.png
  - assets/tiles/tileset_ff6_terrain_16x16.json  (アトラスメタデータ)
  - assets/tiles/tileset_def_ff6_terrain.json    (tileset_def.json と同スキーマの断片)

使い方:
    python3 tools/generate_ff6_terrain.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

# 再現性確保のためシード固定 (FF6 = SNES ロム番号 6 にちなんだ定数)
SEED = 6606

TILE_SIZE = 16
ATLAS_SCALE = "ff6_16"

# ---------------------------------------------------------------- 16色限定パレット
# index 0 は透明。全タイルはこの 16 色のみで描画する (SNES 4bpp 相当)。
PALETTE: list[tuple[int, int, int, int]] = [
    (0, 0, 0, 0),  # 0: 透明
    (24, 20, 32, 255),  # 1: 輪郭 (暗紫黒)
    (236, 232, 224, 255),  # 2: ハイライト (白)
    (172, 176, 192, 255),  # 3: 石・明
    (116, 120, 140, 255),  # 4: 石・中
    (68, 72, 92, 255),  # 5: 石・暗
    (200, 144, 88, 255),  # 6: 錆・明
    (144, 92, 56, 255),  # 7: 錆・中
    (88, 54, 36, 255),  # 8: 錆・暗
    (124, 140, 204, 255),  # 9: 青石・明
    (80, 92, 156, 255),  # 10: 青石・中
    (46, 54, 104, 255),  # 11: 青石・暗
    (184, 148, 96, 255),  # 12: 木・明
    (128, 98, 58, 255),  # 13: 木・中
    (78, 58, 36, 255),  # 14: 木・暗
    (112, 168, 88, 255),  # 15: 草・緑
]

TRANSPARENT, OUTLINE, WHITE = 0, 1, 2
STONE_L, STONE_M, STONE_D = 3, 4, 5
RUST_L, RUST_M, RUST_D = 6, 7, 8
BLUE_L, BLUE_M, BLUE_D = 9, 10, 11
WOOD_L, WOOD_M, WOOD_D = 12, 13, 14
GREEN = 15

# ---------------------------------------------------------------- タイル構成定義
# (ファイルキー, 種別, コマ数[バリアント or フレーム], アニメか, fps)
TILE_GROUPS: list[tuple[str, str, int, bool, int]] = [
    ("FF6_WALL_STONE", "wall_stone", 16, False, 0),
    ("FF6_WALL_IRON", "wall_iron", 16, False, 0),
    ("FF6_WALL_BLUE", "wall_blue", 16, False, 0),
    ("FF6_FLOOR_COBBLE", "floor_cobble", 4, False, 0),
    ("FF6_FLOOR_MOSS", "floor_moss", 4, False, 0),
    ("FF6_FLOOR_WOOD", "floor_wood", 4, False, 0),
    ("FF6_WATER", "water", 4, True, 4),
    ("FF6_LAVA", "lava", 2, True, 3),
    ("FF6_DOOR_CLOSED", "door_closed", 1, False, 0),
    ("FF6_DOOR_OPEN", "door_open", 1, False, 0),
    ("FF6_GRASS", "grass", 1, False, 0),
    ("FF6_FLOWER", "flower", 1, False, 0),
]

# タイル定義フラグメント (tileset_def.json と同スキーマ)
TILE_DEFS: dict[str, dict] = {
    "TILE_FF6_WALL_STONE": {"file": "FF6_WALL_STONE", "variants": 16, "autotile": True},
    "TILE_FF6_WALL_IRON": {"file": "FF6_WALL_IRON", "variants": 16, "autotile": True},
    "TILE_FF6_WALL_BLUE": {"file": "FF6_WALL_BLUE", "variants": 16, "autotile": True},
    "TILE_FF6_FLOOR_COBBLE": {"file": "FF6_FLOOR_COBBLE", "variants": 4},
    "TILE_FF6_FLOOR_MOSS": {"file": "FF6_FLOOR_MOSS", "variants": 4},
    "TILE_FF6_FLOOR_WOOD": {"file": "FF6_FLOOR_WOOD", "variants": 4},
    "TILE_FF6_WATER": {"file": "FF6_WATER", "animated": True, "frames": 4, "fps": 4},
    "TILE_FF6_LAVA": {"file": "FF6_LAVA", "animated": True, "frames": 2, "fps": 3},
    "TILE_DOOR_CLOSED": {"file": "FF6_DOOR_CLOSED", "variants": 1},
    "TILE_DOOR_OPEN": {"file": "FF6_DOOR_OPEN", "variants": 1},
    "TILE_FF6_GRASS": {"file": "FF6_GRASS", "variants": 1},
    "TILE_FF6_FLOWER": {"file": "FF6_FLOWER", "variants": 1},
}


# ---------------------------------------------------------------- 描画プリミティブ
def _new_grid() -> list[list[int]]:
    """16x16 のパレットインデックスグリッドを生成する"""
    return [[TRANSPARENT] * TILE_SIZE for _ in range(TILE_SIZE)]


def _px(g: list[list[int]], x: int, y: int, color: int) -> None:
    """範囲内のみピクセルを置く"""
    if 0 <= x < TILE_SIZE and 0 <= y < TILE_SIZE:
        g[y][x] = color


def _fill(g: list[list[int]], color: int) -> None:
    """全体を塗る"""
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            g[y][x] = color


def _shade_45(g: list[list[int]], light: int, mid: int, dark: int) -> None:
    """45度左上光源 + 2段陰影 (明→中→暗の3バンド、境界は2色ディザ)"""
    span = (TILE_SIZE - 1) * 2  # x+y の最大値
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            t = (x + y) / span
            if t < 0.28:
                g[y][x] = light
            elif t < 0.36:
                g[y][x] = light if (x + y) % 2 == 0 else mid  # 明↔中 ディザ
            elif t < 0.62:
                g[y][x] = mid
            elif t < 0.72:
                g[y][x] = dark if (x + y) % 2 == 0 else mid  # 中↔暗 ディザ
            else:
                g[y][x] = dark


def _hatch(g: list[list[int]], color: int, step: int = 3, phase: int = 0) -> None:
    """45度ハッチング (左上→右下の斜線)"""
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            if (x - y + phase) % step == 0:
                g[y][x] = color


def _dither(g: list[list[int]], color: int, phase: int = 0) -> None:
    """2色ディザ (市松模様)"""
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            if (x + y + phase) % 2 == 0:
                g[y][x] = color


def _hline(g: list[list[int]], y: int, color: int, x0: int = 0, x1: int = TILE_SIZE - 1) -> None:
    for x in range(x0, x1 + 1):
        _px(g, x, y, color)


def _vline(g: list[list[int]], x: int, color: int, y0: int = 0, y1: int = TILE_SIZE - 1) -> None:
    for y in range(y0, y1 + 1):
        _px(g, x, y, color)


def _rect(g: list[list[int]], x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            _px(g, x, y, color)


def _outline(g: list[list[int]], color: int = OUTLINE) -> None:
    """1px暗輪郭 (外周)"""
    _hline(g, 0, color)
    _hline(g, TILE_SIZE - 1, color)
    _vline(g, 0, color)
    _vline(g, TILE_SIZE - 1, color)


def _grid_to_image(g: list[list[int]]) -> Image.Image:
    """パレットインデックスグリッドを RGBA Image へ変換する"""
    img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
    img.putdata([PALETTE[g[y][x]] for y in range(TILE_SIZE) for x in range(TILE_SIZE)])
    return img


# ---------------------------------------------------------------- 壁 (オートタイル16バリアント)
def _draw_wall(mask: int, material: str) -> Image.Image:
    """壁タイルを描画する。mask は N/E/S/W の4bit (bit0=北,1=東,2=南,3=西、隣接壁=1)。"""
    g = _new_grid()

    if material == "stone":
        light, mid, dark = STONE_L, STONE_M, STONE_D
    elif material == "iron":
        light, mid, dark = RUST_L, RUST_M, RUST_D
    else:  # blue
        light, mid, dark = BLUE_L, BLUE_M, BLUE_D

    _fill(g, mid)

    if material == "stone":
        # 石造: 障子積み (4px高・8px幅の石ブロック、目地は暗色)
        for row in range(4):
            y0 = row * 4
            _hline(g, y0, dark)
            offset = (row % 2) * 4
            for bx in range(offset - 8, TILE_SIZE + 8, 8):
                for y in range(y0 + 1, y0 + 4):
                    _px(g, bx, y, dark)
                # 石の左上を明るく (45度光源)
                for y in range(y0 + 1, y0 + 4):
                    _px(g, bx + 1, y, light)
                _hline(g, y0 + 1, light, max(0, bx + 1), min(TILE_SIZE - 1, bx + 6))
        # 質感: 一部の石にハッチング
        if mask % 3 == 0:
            _hatch(g, dark, step=4, phase=mask)
    elif material == "iron":
        # 錆鉄: 8x8 鋼板 + 隅のリベット + 錆の streak
        for py in (0, 8):
            _hline(g, py, dark)
            for px_ in range(0, TILE_SIZE, 8):
                _vline(g, px_, dark, py, py + 7)
                # リベット
                _px(g, px_ + 2, py + 2, dark)
                _px(g, px_ + 5, py + 2, dark)
                _px(g, px_ + 2, py + 5, dark)
                _px(g, px_ + 5, py + 5, dark)
        # 錆の縦 streak (ディザ質感)
        for i in range(3):
            sx = (mask * 5 + i * 6) % 14 + 1
            for y in range(1 + i * 3, TILE_SIZE - 1):
                _px(g, sx, y, RUST_D if (x_streak := y + sx) % 2 == 0 else RUST_M)
        _hatch(g, dark, step=6, phase=mask * 2)
    else:  # blue
        # 青石: 4x8 見切り石、ディザ多め
        for col in range(4):
            x0 = col * 4
            offset = (col % 2) * 4
            for by in range(offset - 8, TILE_SIZE + 8, 8):
                _vline(g, x0, dark)
                _hline(g, by, dark, x0, min(TILE_SIZE - 1, x0 + 3))
                _px(g, x0 + 1, by + 1, light)
        # 右下半分に2色ディザ (陰影)
        for y in range(TILE_SIZE):
            for x in range(TILE_SIZE):
                if x + y > 18 and (x + y) % 2 == 0:
                    g[y][x] = dark
        _hatch(g, BLUE_D, step=5, phase=mask)

    # オートタイル端処理: 隣接しない辺に照明/影の縁を付ける
    if not (mask & 1):  # 北が露出 → 上端ハイライト
        _hline(g, 1, light, 1, TILE_SIZE - 2)
    if not (mask & 8):  # 西が露出 → 左端ハイライト
        _vline(g, 1, light, 1, TILE_SIZE - 2)
    if not (mask & 4):  # 南が露出 → 下端シャドウ
        _hline(g, TILE_SIZE - 2, dark, 1, TILE_SIZE - 2)
    if not (mask & 2):  # 東が露出 → 右端シャドウ
        _vline(g, TILE_SIZE - 2, dark, 1, TILE_SIZE - 2)
    # 露出角は輪郭色で引き締める
    if not (mask & 1) and not (mask & 8):
        _px(g, 1, 1, OUTLINE)
    if not (mask & 1) and not (mask & 2):
        _px(g, TILE_SIZE - 2, 1, OUTLINE)
    if not (mask & 4) and not (mask & 8):
        _px(g, 1, TILE_SIZE - 2, OUTLINE)
    if not (mask & 4) and not (mask & 2):
        _px(g, TILE_SIZE - 2, TILE_SIZE - 2, OUTLINE)

    _outline(g)
    return _grid_to_image(g)


# ---------------------------------------------------------------- 床 (4バリアント)
def _draw_floor(kind: str, variant: int) -> Image.Image:
    g = _new_grid()

    if kind == "floor_cobble":
        # 石畳: 不揃いな丸石 (バリアントで配置ジッターを変える)
        rng = __import__("random").Random(SEED + variant * 17)
        _fill(g, STONE_D)
        for sy in range(4):
            for sx in range(4):
                cx = sx * 4 + (1 if (sy + variant) % 2 == 0 else 0)
                cy = sy * 4
                jx = rng.randint(0, 1)
                jy = rng.randint(0, 1)
                x0, y0 = cx + jx, cy + jy
                for y in range(y0, min(y0 + 3, TILE_SIZE)):
                    for x in range(x0, min(x0 + 3, TILE_SIZE)):
                        _px(g, x, y, STONE_M)
                _hline(g, y0, STONE_L, x0, min(x0 + 2, TILE_SIZE - 1))
                _px(g, x0, y0, STONE_L)
        _dither(g, STONE_D, phase=variant)
    elif kind == "floor_moss":
        # 苔床: 石畳の上に苔 (日陰側=右下に繁茂)
        base = _draw_floor("floor_cobble", variant)
        g = [[(0 if base.getpixel((x, y))[3] == 0 else _nearest_palette_index(base.getpixel((x, y)))) for x in range(TILE_SIZE)] for y in range(TILE_SIZE)]
        rng = __import__("random").Random(SEED + 101 + variant * 13)
        for _ in range(7):
            mx = rng.randint(1, TILE_SIZE - 3)
            my = rng.randint(1, TILE_SIZE - 3)
            # 右下ほど苔が太る (45度光源の陰に苔が生える)
            if mx + my < 12 and rng.random() < 0.5:
                continue
            size = 2 if mx + my > 16 else 1
            for y in range(my, my + size + 1):
                for x in range(mx, mx + size + 1):
                    if g[y][x] != OUTLINE and (x + y + variant) % 3 != 0:
                        _px(g, x, y, GREEN)
            _px(g, mx, my, WHITE if variant == 3 else GREEN)
    else:  # floor_wood
        # 木板: 縦板4枚 + 木目ハッチング + 釘
        _fill(g, WOOD_M)
        for px_ in range(0, TILE_SIZE, 4):
            _vline(g, px_, WOOD_D)
            for y in range(TILE_SIZE):
                if (y + px_ + variant * 2) % 4 == 0:
                    _px(g, px_ + 2, y, WOOD_D)
            _hline(g, 1, WOOD_L, px_ + 1, px_ + 3)
            _px(g, px_ + 2, 3 + variant, WOOD_D)  # 釘
        _hatch(g, WOOD_D, step=5, phase=variant * 3)

    _outline(g)
    return _grid_to_image(g)


def _nearest_palette_index(rgb: tuple[int, ...]) -> int:
    """ RGBA から最も近いパレット不透明色のインデックスを返す"""
    best, best_d = STONE_M, 1 << 30
    for i, p in enumerate(PALETTE):
        if p[3] == 0:
            continue
        d = sum((a - b) ** 2 for a, b in zip(rgb[:3], p[:3]))
        if d < best_d:
            best, best_d = i, d
    return best


# ---------------------------------------------------------------- 水・熔岩 (アニメ)
def _draw_water(frame: int) -> Image.Image:
    """水タイル: 斜めの光の走りがフレームごとに漂流する"""
    g = _new_grid()
    _fill(g, BLUE_M)
    # 深部: 左下に2色ディザ
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            if x + y > 20 and (x + y) % 2 == 0:
                g[y][x] = BLUE_D
    # 波頭: 斜めの明線 (フレームで位相シフト)
    for y in range(1, TILE_SIZE - 1):
        for x in range(1, TILE_SIZE - 1):
            if (x + frame * 2 + (y // 4) * 3) % 8 < 2:
                _px(g, x, y, BLUE_L)
    _outline(g)
    return _grid_to_image(g)


def _draw_lava(frame: int) -> Image.Image:
    """熔岩タイル: 暗い地殻のひび割れから明部が覗く (2フレームで沸騰)"""
    g = _new_grid()
    _fill(g, RUST_D)
    rng = __import__("random").Random(SEED + 77 + frame * 5)
    # 溶けた明部 (フレームごとに位置が変わる)
    for _ in range(4):
        cx = rng.randint(2, TILE_SIZE - 4)
        cy = rng.randint(2, TILE_SIZE - 4)
        r = rng.randint(1, 2)
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    _px(g, x, y, RUST_L)
        _px(g, cx, cy, WHITE)  # 白熱部
    # 地殻のひび割れ (ハッチング質感)
    _hatch(g, OUTLINE, step=5, phase=frame * 2)
    _outline(g)
    return _grid_to_image(g)


# ---------------------------------------------------------------- 扉・装飾
def _draw_door(opened: bool) -> Image.Image:
    g = _new_grid()
    if not opened:
        # 閉扉: 木の観音開き + 鉄帯 + 取っ手
        _fill(g, WOOD_M)
        for px_ in range(0, TILE_SIZE, 4):
            _vline(g, px_, WOOD_D)
            _hline(g, 1, WOOD_L, px_ + 1, px_ + 3)
        for y in (4, 11):
            _hline(g, y, RUST_M, 1, TILE_SIZE - 2)
            _hline(g, y + 1, RUST_D, 1, TILE_SIZE - 2)
            for x in (3, 12):
                _px(g, x, y, OUTLINE)  # 鉄帯のリベット
        _px(g, 12, 8, WHITE)  # 取っ手
        _px(g, 13, 8, WOOD_D)
    else:
        # 開扉: 暗い開口部 + 左に開いた扉板 + 敷居
        _fill(g, STONE_D)
        _dither(g, BLUE_D, phase=1)  # 奥の闇
        _rect(g, 2, 1, 4, TILE_SIZE - 2, WOOD_M)  # 開いた扉板
        _vline(g, 2, WOOD_L, 1, TILE_SIZE - 2)
        _vline(g, 4, WOOD_D, 1, TILE_SIZE - 2)
        _hline(g, TILE_SIZE - 2, STONE_M, 1, TILE_SIZE - 2)  # 敷居
    _outline(g)
    return _grid_to_image(g)


def _draw_grass_decor(flower: bool) -> Image.Image:
    """草・花装飾: 石畳床の上に草むら (通行可能な床タイルとして機能する)"""
    base = _draw_floor("floor_cobble", 0)
    g = [
        [
            _nearest_palette_index(base.getpixel((x, y)))
            if base.getpixel((x, y))[3] != 0
            else TRANSPARENT
            for x in range(TILE_SIZE)
        ]
        for y in range(TILE_SIZE)
    ]
    rng = __import__("random").Random(SEED + (211 if flower else 311))
    blades = rng.randint(5, 7)
    for _ in range(blades):
        gx = rng.randint(2, TILE_SIZE - 3)
        gy = rng.randint(4, TILE_SIZE - 3)
        h = rng.randint(2, 3)
        for i in range(h):
            _px(g, gx + (i % 2), gy - i, GREEN)
        _px(g, gx, gy - h, WHITE if flower and _ % 2 == 0 else GREEN)
    if flower:
        # 花を2輪 (白弁 + 錆色中心)
        for fx, fy in ((4, 6), (11, 10)):
            _px(g, fx, fy - 1, WHITE)
            _px(g, fx - 1, fy, WHITE)
            _px(g, fx + 1, fy, WHITE)
            _px(g, fx, fy + 1, WHITE)
            _px(g, fx, fy, RUST_L)
    _outline(g)
    return _grid_to_image(g)


# ---------------------------------------------------------------- アトラス構築
def build_atlas(out_dir: Path) -> dict:
    """全タイルを描画してアトラス PNG とメタデータ / 定義フラグメントを書き出す"""
    out_dir.mkdir(parents=True, exist_ok=True)

    max_w = max(count * TILE_SIZE for _, _, count, _, _ in TILE_GROUPS)
    atlas_h = len(TILE_GROUPS) * (TILE_SIZE + 1) - 1
    atlas = Image.new("RGBA", (max_w, atlas_h), PALETTE[TRANSPARENT])

    atlas_tiles: dict[str, dict] = {}
    for row, (file_key, kind, count, animated, fps) in enumerate(TILE_GROUPS):
        base_y = row * (TILE_SIZE + 1)
        for i in range(count):
            if kind.startswith("wall_"):
                img = _draw_wall(i, kind.removeprefix("wall_"))
            elif kind.startswith("floor_"):
                img = _draw_floor(kind, i)
            elif kind == "water":
                img = _draw_water(i)
            elif kind == "lava":
                img = _draw_lava(i)
            elif kind == "door_closed":
                img = _draw_door(False)
            elif kind == "door_open":
                img = _draw_door(True)
            elif kind == "grass":
                img = _draw_grass_decor(False)
            else:  # flower
                img = _draw_grass_decor(True)
            atlas.paste(img, (i * TILE_SIZE, base_y))

        atlas_tiles[file_key] = {
            "x": 0,
            "y": base_y,
            "width": TILE_SIZE,
            "height": TILE_SIZE,
            "variants": count if not animated else 1,
            "animated": animated,
            "frames": count if animated else 1,
            "fps": fps if animated else 1,
            "directions": 1,
        }

    png_path = out_dir / "tileset_ff6_terrain_16x16.png"
    atlas.save(png_path)

    atlas_meta = {
        "tile_size": TILE_SIZE,
        "atlas_width": atlas.width,
        "atlas_height": atlas.height,
        "tiles": atlas_tiles,
    }
    atlas_json_path = out_dir / "tileset_ff6_terrain_16x16.json"
    atlas_json_path.write_text(
        json.dumps(atlas_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def_entries: dict[str, dict] = {}
    for tile_id, spec in TILE_DEFS.items():
        entry: dict = {
            "file": spec["file"],
            "atlas_scale": ATLAS_SCALE,
            "frame_width": TILE_SIZE,
            "directions": 1,
            "states": ["idle"],
        }
        if spec.get("animated"):
            entry["animated"] = True
            entry["frames"] = spec["frames"]
            entry["fps"] = spec["fps"]
        else:
            entry["variants"] = spec["variants"]
            entry["variant_width"] = TILE_SIZE
            if spec.get("autotile"):
                entry["autotile"] = True
        def_entries[tile_id] = entry

    def_json_path = out_dir / "tileset_def_ff6_terrain.json"
    def_json_path.write_text(
        json.dumps(
            {"version": "1.0", "tile_size": TILE_SIZE, "tiles": def_entries},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "png": png_path,
        "atlas_json": atlas_json_path,
        "atlas_meta": atlas_meta,
        "def_json": def_json_path,
        "def_entries": def_entries,
    }


# ---------------------------------------------------------------- 自己チェック
def self_check(result: dict) -> list[str]:
    """生成物の整合性を検証する。問題があればエラーメッセージを返す。"""
    errors: list[str] = []
    atlas_meta = result["atlas_meta"]
    atlas_w, atlas_h = atlas_meta["atlas_width"], atlas_meta["atlas_height"]
    png = Image.open(result["png"])
    if png.size != (atlas_w, atlas_h):
        errors.append(f"PNGサイズ不一致: {png.size} != ({atlas_w}, {atlas_h})")

    for tile_id, entry in result["def_entries"].items():
        file_key = entry.get("file")
        if file_key not in atlas_meta["tiles"]:
            errors.append(f"{tile_id}: fileキー '{file_key}' がアトラスJSONに存在しない")
            continue
        meta = atlas_meta["tiles"][file_key]
        if entry.get("animated"):
            frames = entry.get("frames", 1)
        else:
            frames = entry.get("variants", 1)
        extent_x = meta["x"] + frames * entry.get("frame_width", TILE_SIZE)
        extent_y = meta["y"] + meta["height"]
        if extent_x > atlas_w:
            errors.append(f"{tile_id}: フレーム/バリアント幅がアトラス幅を超過 ({extent_x} > {atlas_w})")
        if extent_y > atlas_h:
            errors.append(f"{tile_id}: 高さがアトラス高を超過 ({extent_y} > {atlas_h})")

    # 16色制約の確認 (使われた色がパレット内に収まっているか)
    used = {png.getpixel((x, y)) for y in range(atlas_h) for x in range(atlas_w)}
    unknown = used - set(PALETTE)
    if unknown:
        errors.append(f"パレット外の色が使用されている: {sorted(unknown)[:4]} ...")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="FF6風テラインタイル生成ツール")
    parser.add_argument("--out-dir", default="assets/tiles", help="出力ディレクトリ")
    args = parser.parse_args()

    result = build_atlas(Path(args.out_dir))

    errors = self_check(result)
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    atlas_meta = result["atlas_meta"]
    print(f"[OK] {result['png']} ({atlas_meta['atlas_width']}x{atlas_meta['atlas_height']})")
    print(f"[OK] {result['atlas_json']} ({len(atlas_meta['tiles'])} file keys)")
    print(f"[OK] {result['def_json']} ({len(result['def_entries'])} TILE_IDs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
