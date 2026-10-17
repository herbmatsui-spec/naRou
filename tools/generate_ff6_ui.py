"""
FF6風UIウィンドウ枠生成ツール (T16 案1: UIウィンドウ枠 + ATB風ゲージ)

Pillow で FF6 風 9-slice ウィンドウ枠画像 (48x48) を生成する。
構成: 青グラデ中央 (fill) + 銀の飾り縁 + 角の装飾。
9-slice 境界は 16px (CSS 側: border-image: url(...) 16 fill / 16px stretch)。

出力 (通常 / ホバー / 無効の 3 バリエーション):
  - assets/tiles/ff6_ui_frame.png           (通常)
  - assets/tiles/ff6_ui_frame_hover.png     (ホバー: 銀縁を明るく強調)
  - assets/tiles/ff6_ui_frame_disabled.png  (無効: 低彩度・沈んだ色)

使い方:
    python3 tools/generate_ff6_ui.py [--out-dir OUT_DIR]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image

# 再現性確保のためシード固定 (generate_ff6_terrain.py と同じ定数)
SEED = 6606

FRAME_SIZE = 48
SLICE = 16  # 9-slice 境界幅 (CSS border-image-slice と一致させる)

# ---------------------------------------------------------------- 16色限定パレット
# index 0 は透明。FF6 = SNES 4bpp 相当の 16 色のみで描画する。
PALETTE: list[tuple[int, int, int, int]] = [
    (0, 0, 0, 0),  # 0: 透明 (枠は不透明のため未使用)
    (24, 20, 32, 255),  # 1: 輪郭 (暗紫黒)
    (238, 240, 246, 255),  # 2: 銀ハイライト (白寄り)
    (184, 192, 208, 255),  # 3: 銀・明
    (124, 134, 160, 255),  # 4: 銀・中
    (72, 80, 104, 255),  # 5: 銀・暗
    (212, 175, 55, 255),  # 6: 金 (角装飾ポイント)
    (140, 108, 32, 255),  # 7: 金・暗
    (10, 16, 48, 255),  # 8: 青グラデ・暗
    (18, 32, 80, 255),  # 9: 青グラデ・中暗
    (28, 52, 104, 255),  # 10: 青グラデ・中
    (44, 78, 148, 255),  # 11: 青グラデ・明
    (74, 120, 200, 255),  # 12: 青・ハイライト
    (136, 184, 240, 255),  # 13: 水色・ハイライト
    (32, 24, 48, 255),  # 14: 影紫 (内側陰影)
    (244, 248, 252, 255),  # 15: 白 ( sparkle )
]

TRANSPARENT, OUTLINE = 0, 1
SILVER_HI, SILVER_L, SILVER_M, SILVER_D = 2, 3, 4, 5
GOLD, GOLD_D = 6, 7
BLUE_D, BLUE_MD, BLUE_M, BLUE_L, BLUE_HL, BLUE_CYAN = 8, 9, 10, 11, 12, 13
SHADOW, WHITE = 14, 15

# ---------------------------------------------------------------- バリエーション定義
# 通常パレットインデックス → バリエーション上のインデックスのリマップ。
COLOR_REMAPS: dict[str, dict[int, int]] = {
    "normal": {},
    # ホバー: 銀縁を 1 段階明るくし、金の輝きを強調
    "hover": {
        SILVER_D: SILVER_M,
        SILVER_M: SILVER_L,
        SILVER_L: SILVER_HI,
        GOLD: SILVER_HI,
        GOLD_D: GOLD,
        BLUE_HL: BLUE_CYAN,
    },
    # 無効: 彩度を落とし、銀→暗グレー・金→暗金・青→沈んだ青
    "disabled": {
        SILVER_HI: SILVER_M,
        SILVER_L: SILVER_M,
        SILVER_M: SILVER_D,
        SILVER_D: SHADOW,
        GOLD: GOLD_D,
        GOLD_D: OUTLINE,
        BLUE_HL: BLUE_M,
        BLUE_CYAN: BLUE_M,
        BLUE_L: BLUE_MD,
    },
}


def _nearest_palette_index(color: tuple[int, int, int]) -> int:
    """RGB 値に最も近いパレットのインデックスを返す (グラデの量子化用)。"""
    r, g, b = color
    best, best_dist = 1, 1 << 30
    for i in range(1, len(PALETTE)):
        pr, pg, pb, _ = PALETTE[i]
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < best_dist:
            best, best_dist = i, dist
    return best


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """2 色を線形補間する。"""
    return (
        round(c1[0] + (c2[0] - c1[0]) * t),
        round(c1[1] + (c2[1] - c1[1]) * t),
        round(c1[2] + (c2[2] - c1[2]) * t),
    )


def _draw_background(px, remap: dict[int, int]) -> None:
    """中央の青グラデ (fill 領域) を描画し、枠内側に 2 段陰影を敷く。"""
    blue_grad = [PALETTE[i][:3] for i in (BLUE_HL, BLUE_L, BLUE_M, BLUE_MD, BLUE_D)]
    for y in range(FRAME_SIZE):
        # 上 → 下へ緩やかに暗くなる縦グラデ (FF6 のメニューウィンドウ風)
        t = y / (FRAME_SIZE - 1)
        # t: 0..1 → blue_grad 上の連続色へ
        seg = t * (len(blue_grad) - 1)
        i = min(int(seg), len(blue_grad) - 2)
        color = _mix(blue_grad[i], blue_grad[i + 1], seg - i)
        idx = _nearest_palette_index(color)
        idx = remap.get(idx, idx)
        for x in range(FRAME_SIZE):
            px[x, y] = PALETTE[idx]


def _draw_silver_edge(px, remap: dict[int, int]) -> None:
    """外周の銀の飾り縁を描画する (光源は 45 度左上)。"""
    # (リング番号, 上左時の色, 下右時の色) — 45 度左上光源で面を出す
    rings = [
        (0, OUTLINE, OUTLINE),
        (1, SILVER_HI, SILVER_D),
        (2, SILVER_HI, SILVER_D),
        (3, SILVER_L, SILVER_M),
        (4, SILVER_L, SILVER_M),
        (5, SILVER_M, SILVER_D),
        (6, SILVER_M, SILVER_D),
        (7, SHADOW, SHADOW),  # 枠と青面の境界の暗ライン
        (8, BLUE_D, BLUE_D),  # 内側陰影 1 段目
        (9, BLUE_MD, BLUE_MD),  # 内側陰影 2 段目
    ]
    for ring, c_tl, c_br in rings:
        idx_tl = remap.get(c_tl, c_tl)
        idx_br = remap.get(c_br, c_br)
        for i in range(ring, FRAME_SIZE - ring):
            # 上辺・左辺は明、下辺・右辺は暗
            px[i, ring] = PALETTE[idx_tl]
            px[ring, i] = PALETTE[idx_tl]
            px[i, FRAME_SIZE - 1 - ring] = PALETTE[idx_br]
            px[FRAME_SIZE - 1 - ring, i] = PALETTE[idx_br]


def _draw_corner_ornament(px, remap: dict[int, int], ox: int, oy: int, flip_x: bool, flip_y: bool) -> None:
    """1 つのコーナー (16x16) に斜め銀装飾と金のポイントを描く。

    (ox, oy) はコーナーの原点。flip で対角方向を反転させる。
    """
    def local(x: int, y: int) -> tuple[int, int]:
        """コーナー内座標 → フレーム全体座標 (flip 適用)。"""
        lx = x if not flip_x else (SLICE - 1 - x)
        ly = y if not flip_y else (SLICE - 1 - y)
        return ox + lx, oy + ly

    def put(x: int, y: int, idx: int) -> None:
        fx, fy = local(x, y)
        px[fx, fy] = PALETTE[remap.get(idx, idx)]

    # 斜め装飾ライン (銀): 外周輪郭 (リング 0-1) を避け、コーナー内側に階段状に描く
    silver_hi = remap.get(SILVER_HI, SILVER_HI)
    for i in range(4, SLICE - 2):
        put(i, i, SILVER_L if (i % 2 == 0) else SILVER_M)
        if i + 1 < SLICE - 2:
            put(i + 1, i, SILVER_M)
            put(i, i + 1, SILVER_D)
    # 斜め装飾の外側に金の 1 ピクセルをアクセントとして散らす
    for i in (6, 9, 12):
        put(i + 2, i, remap.get(GOLD, GOLD))
        put(i, i + 2, remap.get(GOLD_D, GOLD_D))
    # コーナー先端に銀ハイライトの小菱形
    for dx, dy in ((6, 5), (5, 6), (7, 6), (6, 7)):
        put(dx, dy, silver_hi)
    put(6, 6, remap.get(WHITE, WHITE))


def _draw_corner_noise(px, remap: dict[int, int], rng: random.Random) -> None:
    """4 つのコーナーの銀縁にハイライト / シャドウのドットノイズを散らす。"""
    corners = [(0, 0, False, False), (FRAME_SIZE - SLICE, 0, True, False),
               (0, FRAME_SIZE - SLICE, False, True), (FRAME_SIZE - SLICE, FRAME_SIZE - SLICE, True, True)]
    for ox, oy, flip_x, flip_y in corners:
        # 外周輪郭 (リング 0-1) は壊さず、銀縁の内側のみにノイズを散らす
        for _ in range(10):
            x = ox + rng.randrange(2, SLICE - 2)
            y = oy + rng.randrange(2, SLICE - 2)
            if rng.random() < 0.5:
                px[x, y] = PALETTE[remap.get(SILVER_HI, SILVER_HI)]
            else:
                px[x, y] = PALETTE[remap.get(SILVER_D, SILVER_D)]


def build_frame(variant: str = "normal", seed: int = SEED) -> Image.Image:
    """FF6 風 9-slice ウィンドウ枠画像 (48x48) を生成する。

    @param variant - normal / hover / disabled のいずれか
    @param seed - 装飾ノイズ用の乱数シード
    @return RGBA 画像 (48x48)
    """
    remap = COLOR_REMAPS.get(variant, {})
    image = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), PALETTE[TRANSPARENT])
    px = image.load()

    rng = random.Random(f"{seed}:{variant}")

    _draw_background(px, remap)
    _draw_silver_edge(px, remap)
    # ノイズを先に敷き、装飾ライン / 菱形が上書きされないよう後に描く
    _draw_corner_noise(px, remap, rng)
    _draw_corner_ornament(px, remap, 0, 0, False, False)
    _draw_corner_ornament(px, remap, FRAME_SIZE - SLICE, 0, True, False)
    _draw_corner_ornament(px, remap, 0, FRAME_SIZE - SLICE, False, True)
    _draw_corner_ornament(px, remap, FRAME_SIZE - SLICE, FRAME_SIZE - SLICE, True, True)

    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="FF6風UIウィンドウ枠生成ツール")
    parser.add_argument("--out-dir", default="assets/tiles", help="出力ディレクトリ")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "normal": "ff6_ui_frame.png",
        "hover": "ff6_ui_frame_hover.png",
        "disabled": "ff6_ui_frame_disabled.png",
    }
    for variant, filename in outputs.items():
        image = build_frame(variant)
        path = out_dir / filename
        image.save(path)
        print(f"[generate_ff6_ui] {variant}: {path} ({image.width}x{image.height})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
