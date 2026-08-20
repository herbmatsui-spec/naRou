"""
generate_rich_gifs.py
Aの世界（スキル喰い）用の高品質なGIFアニメーション生成スクリプト
Pillow (PIL) を確実に読み込み、フレームアニメーションを生成する基盤
"""

import math
import sys
from pathlib import Path

# 本物のPillowのパスを最優先に設定（ローカルのPILスタブを除外）
sys.path = [p for p in sys.path if p not in ("", ".", "e:\\narou2", "E:\\narou2")]
sys.path.insert(0, r"C:\Users\keide\AppData\Roaming\Python\Python314\site-packages")
sys.path.insert(0, r"C:\Python314\Lib\site-packages")

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError as e:
    print(f"Error importing Pillow: {e}")
    sys.exit(1)

# --- 定数定義 ---
WIDTH = 640
HEIGHT = 360
FPS = 30
FRAME_DURATION_MS = int(1000 / FPS)  # 約33ms

EMOTE_DIR = Path("e:/narou2/emote/PNG/Vector/Style 1")
import json


def get_font(size: int = 14):
    """フォントオブジェクトをロード"""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


ATLAS_IMG_PATH = Path("e:/narou2/assets/tiles/tiny_rogue_atlas_16x16.png")
ATLAS_JSON_PATH = Path("e:/narou2/assets/tiles/tiny_rogue_atlas_16x16.json")


class TileAtlas:
    def __init__(self, img_path: Path, json_path: Path):
        self.img_path = img_path
        self.json_path = json_path
        self.image = None
        self.data = None
        self._tile_cache = {}
        self.load()

    def load(self):
        if self.img_path.exists() and self.json_path.exists():
            self.image = Image.open(self.img_path).convert("RGBA")
            with open(self.json_path, encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            print(f"Warning: Atlas files not found: {self.img_path} / {self.json_path}")

    def get_tile(self, tile_key: str, scale: int = 1) -> Image.Image:
        """指定したキーのタイル画像を取得（必要ならスケーリング）"""
        cache_key = (tile_key, scale)
        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        if not self.image or not self.data or "tiles" not in self.data:
            # フォールバック
            img = Image.new("RGBA", (16 * scale, 16 * scale), (80, 80, 80, 255))
            return img

        info = self.data["tiles"].get(tile_key)
        if not info:
            # キーが見つからない場合のフォールバック（灰色四角）
            img = Image.new("RGBA", (16 * scale, 16 * scale), (100, 100, 100, 255))
            self._tile_cache[cache_key] = img
            return img

        x = info["x"]
        y = info["y"]
        w = info.get("width", 16)
        h = info.get("height", 16)
        crop_box = (x, y, x + w, y + h)
        tile_img = self.image.crop(crop_box)

        if scale != 1:
            tile_img = tile_img.resize((w * scale, h * scale), Image.Resampling.NEAREST)

        self._tile_cache[cache_key] = tile_img
        return tile_img


class EmoteManager:
    def __init__(self, emote_dir: Path):
        self.emote_dir = emote_dir
        self._cache = {}

    def get_emote(self, name: str, size: int = 32) -> Image.Image:
        """指定したEmote名 (例: emote_heart) とサイズで画像を取得"""
        if not name.endswith(".png"):
            name = f"{name}.png"

        cache_key = (name, size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.emote_dir / name
        if not path.exists():
            # フォールバック
            img = Image.new("RGBA", (size, size), (255, 0, 0, 0))
            self._cache[cache_key] = img
            return img

        try:
            img = Image.open(path).convert("RGBA")
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            self._cache[cache_key] = img
            return img
        except Exception as e:
            print(f"Error loading emote {name}: {e}")
            img = Image.new("RGBA", (size, size), (255, 0, 0, 0))
            return img


emote_mgr = EmoteManager(EMOTE_DIR)
atlas = TileAtlas(ATLAS_IMG_PATH, ATLAS_JSON_PATH)


def draw_sprite(
    canvas: Image.Image,
    tile_key: str,
    x: int,
    y: int,
    scale: int = 2,
    anchor: str = "nw",
):
    """指定座標にタイル/スプライトを描画"""
    sprite = atlas.get_tile(tile_key, scale=scale)
    w, h = sprite.size

    if anchor == "center":
        draw_x = x - w // 2
        draw_y = y - h // 2
    else:  # nw
        draw_x = x
        draw_y = y

    canvas.paste(sprite, (int(draw_x), int(draw_y)), sprite)


def draw_emote(
    canvas: Image.Image,
    emote_name: str,
    x: int,
    y: int,
    size: int = 32,
    anchor: str = "center",
):
    """指定座標にEmoteを描画"""
    emote_img = emote_mgr.get_emote(emote_name, size=size)
    w, h = emote_img.size

    if anchor == "center":
        draw_x = x - w // 2
        draw_y = y - h // 2
    else:
        draw_x = x
        draw_y = y

    canvas.paste(emote_img, (int(draw_x), int(draw_y)), emote_img)


# --- イージング関数群 (t は 0.0 ~ 1.0) ---
def ease_linear(t: float) -> float:
    return max(0.0, min(1.0, t))


def ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


def ease_out_bounce(t: float) -> float:
    t = max(0.0, min(1.0, t))
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


import random


class EffectManager:
    """画面エフェクト（画面揺れ、フラッシュ、オーバーレイ）を管理"""

    def __init__(self):
        self.shake_intensity = 0.0
        self.shake_decay = 0.9
        self.flash_color = None
        self.flash_alpha = 0.0

    def trigger_shake(self, intensity: float = 6.0):
        self.shake_intensity = max(self.shake_intensity, intensity)

    def trigger_flash(self, color=(255, 255, 255), duration_frames: int = 5):
        self.flash_color = color
        self.flash_alpha = 1.0
        self.flash_decay = 1.0 / max(1, duration_frames)

    def update(self):
        # 減衰
        if self.shake_intensity > 0.1:
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_intensity = 0.0

        if self.flash_alpha > 0.0:
            self.flash_alpha = max(
                0.0, self.flash_alpha - getattr(self, "flash_decay", 0.2)
            )

    def get_shake_offset(self):
        if self.shake_intensity <= 0.1:
            return (0, 0)
        ox = random.uniform(-self.shake_intensity, self.shake_intensity)
        oy = random.uniform(-self.shake_intensity, self.shake_intensity)
        return (int(ox), int(oy))

    def apply_flash(self, canvas: Image.Image) -> Image.Image:
        if self.flash_alpha <= 0.01 or not self.flash_color:
            return canvas
        overlay = Image.new(
            "RGBA", canvas.size, (*self.flash_color, int(255 * self.flash_alpha))
        )
        return Image.alpha_composite(canvas, overlay)


effect_mgr = EffectManager()


def save_gif(frames: list, output_path: Path, fps: int = FPS, loop: int = 0):
    """フレームリストからGIFアニメーションを生成保存"""
    if not frames:
        print("Warning: No frames to save.")
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rgb_frames = []
    for f in frames:
        if f.mode == "RGBA":
            # 透明背景を黒バックで合成してRGB化
            bg = Image.new("RGB", f.size, (15, 15, 20))
            bg.paste(f, mask=f.split()[3])
            rgb_frames.append(bg)
        else:
            rgb_frames.append(f.convert("RGB"))

    duration_ms = int(1000 / fps)
    rgb_frames[0].save(
        output_path,
        save_all=True,
        append_images=rgb_frames[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
    )
    print(f"GIF saved: {output_path} ({len(frames)} frames, ~{len(frames) / fps:.1f}s)")


def draw_dungeon_background(
    canvas: Image.Image, floor_tile: str = "TR_FLOOR_01", wall_tile: str = "TR_WALL_01"
):
    """ダンジョンの床と壁タイルを敷き詰めてダークな背景を作成"""
    tw = 32  # 16x16 を scale 2 で描画
    th = 32
    cols = WIDTH // tw + 1
    rows = HEIGHT // th + 1

    # 床
    for r in range(rows):
        for c in range(cols):
            draw_sprite(canvas, floor_tile, c * tw, r * th, scale=2, anchor="nw")

    # 上部・下部・左右に壁や影をつける
    for c in range(cols):
        draw_sprite(canvas, wall_tile, c * tw, 0, scale=2, anchor="nw")

    # 半透明のダークグラデーション/ビネット効果を重ねる
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (10, 10, 15, 120))
    canvas.paste(Image.alpha_composite(canvas, overlay), (0, 0))


def draw_health_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    cur_hp: float,
    max_hp: float,
    fill_color=(231, 76, 60),
    label="",
):
    """HPバーおよびステータスバーの描画"""
    ratio = max(0.0, min(1.0, cur_hp / max_hp))
    # 背景
    draw.rectangle(
        [x, y, x + w, y + h], fill=(30, 30, 35, 200), outline=(80, 80, 90, 255), width=1
    )
    # バー本体
    if ratio > 0:
        bar_w = int((w - 2) * ratio)
        draw.rectangle([x + 1, y + 1, x + 1 + bar_w, y + h - 1], fill=fill_color)
    if label:
        f = get_font(11)
        draw.text((x + 4, y - 14), label, font=f, fill=(240, 240, 240, 255))


def draw_hud(
    canvas: Image.Image,
    hp: int,
    max_hp: int,
    mp: int,
    max_mp: int,
    title: str = "A-World: Skill Eater",
):
    """画面上部のステータスバーとヘッダーUI"""
    draw = ImageDraw.Draw(canvas)
    # 上部ヘッダー枠
    draw.rectangle([0, 0, WIDTH, 36], fill=(15, 15, 20, 230))
    draw.line([(0, 36), (WIDTH, 36)], fill=(70, 70, 90, 255), width=2)

    # タイトル
    f_title = get_font(15)
    draw.text((16, 8), title, font=f_title, fill=(0, 230, 255, 255))

    # HPバー
    draw_health_bar(
        draw, 320, 10, 120, 16, hp, max_hp, fill_color=(230, 60, 60), label=""
    )
    f_stat = get_font(11)
    draw.text((295, 11), "HP", font=f_stat, fill=(255, 100, 100))
    draw.text((350, 12), f"{hp}/{max_hp}", font=f_stat, fill=(255, 255, 255))

    # MPバー
    draw_health_bar(
        draw, 490, 10, 120, 16, mp, max_mp, fill_color=(60, 140, 240), label=""
    )
    draw.text((465, 11), "MP", font=f_stat, fill=(100, 180, 255))
    draw.text((520, 12), f"{mp}/{max_mp}", font=f_stat, fill=(255, 255, 255))


def draw_scan_effect(
    canvas: Image.Image, target_x: int, target_y: int, progress: float
):
    """敵の深度解析（Scan）アニメーションエフェクト"""
    draw = ImageDraw.Draw(canvas)

    # 走査範囲（敵周辺）
    box_w, box_h = 100, 100
    bx = target_x - box_w // 2
    by = target_y - box_h // 2

    # スキャン枠
    draw.rectangle(
        [bx, by, bx + box_w, by + box_h], outline=(0, 255, 200, 180), width=1
    )

    # 上から下へ動くレーザー走査線
    scan_line_y = int(by + box_h * progress)
    draw.line(
        [(bx, scan_line_y), (bx + box_w, scan_line_y)],
        fill=(50, 255, 255, 255),
        width=2,
    )

    # 解析中テキスト & Emote
    f = get_font(12)
    draw.text(
        (bx, by - 18),
        f">> SCANNING... {int(progress * 100)}%",
        font=f,
        fill=(0, 255, 220, 255),
    )
    draw_emote(canvas, "emote_dots3", target_x, target_y - 65, size=24, anchor="center")


def draw_devour_particles(
    canvas: Image.Image, src_x: int, src_y: int, dst_x: int, dst_y: int, progress: float
):
    """《喰らい》発動時の紫のスキル核・パーティクル吸収アニメーション"""
    draw = ImageDraw.Draw(canvas)

    # 進行度に応じて敵から主人公へ移動
    cur_x = lerp(src_x, dst_x, ease_in_out_quad(progress))
    # 弓なりのカーブ軌道
    arc_y = -math.sin(progress * math.pi) * 60
    cur_y = lerp(src_y, dst_y, progress) + arc_y

    # パーティクル尾部（残像）
    for i in range(1, 6):
        tail_p = max(0.0, progress - i * 0.05)
        tx = lerp(src_x, dst_x, ease_in_out_quad(tail_p))
        ty = lerp(src_y, dst_y, tail_p) - math.sin(tail_p * math.pi) * 60
        alpha = int(200 * (1.0 - i * 0.18))
        r = int(8 * (1.0 - i * 0.15))
        draw.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(180, 50, 240, alpha))

    # 核本体（光球）
    r = 12
    draw.ellipse(
        [cur_x - r, cur_y - r, cur_x + r, cur_y + r],
        fill=(220, 100, 255, 255),
        outline=(255, 255, 255, 255),
        width=2,
    )
    # 中心コア
    draw.ellipse(
        [cur_x - 5, cur_y - 5, cur_x + 5, cur_y + 5], fill=(255, 255, 255, 255)
    )

    # 主人公側の捕食エフェクト
    f = get_font(13)
    draw.text(
        (dst_x - 40, dst_y - 65), "DEVOURING...", font=f, fill=(220, 80, 255, 255)
    )


def draw_devour_burst(
    canvas: Image.Image, hero_x: int, hero_y: int, skill_name: str = "Inferno Breath"
):
    """捕食成功時のフラッシュと星エフェクト、獲得ポップアップ"""
    draw = ImageDraw.Draw(canvas)

    # 周囲に散らばる星
    star_offsets = [(-35, -45), (35, -50), (-45, 10), (45, 15), (0, -65)]
    for ox, oy in star_offsets:
        draw_emote(
            canvas, "emote_star", hero_x + ox, hero_y + oy, size=20, anchor="center"
        )

    # 中央の大きなスター
    draw_emote(canvas, "emote_stars", hero_x, hero_y - 40, size=36, anchor="center")

    # 獲得スキルバナー
    banner_w, banner_h = 240, 36
    bx = hero_x - banner_w // 2
    by = hero_y - 110
    draw.rectangle(
        [bx, by, bx + banner_w, by + banner_h],
        fill=(40, 10, 60, 230),
        outline=(220, 100, 255, 255),
        width=2,
    )
    f = get_font(13)
    draw.text(
        (bx + 12, by + 8), f"ACQUIRED: {skill_name}", font=f, fill=(255, 220, 100, 255)
    )


def draw_synergy_explosion(
    canvas: Image.Image,
    target_x: int,
    target_y: int,
    progress: float,
    synergy_name: str = "THERMAL EXPLOSION",
):
    """属性シナジー発動時の爆風・炎リング演出"""
    draw = ImageDraw.Draw(canvas)

    # 拡大する同心円爆風
    max_radius = 80
    r1 = int(max_radius * ease_out_quad(progress))
    alpha1 = int(220 * (1.0 - progress))
    if r1 > 0:
        draw.ellipse(
            [target_x - r1, target_y - r1, target_x + r1, target_y + r1],
            outline=(255, 120, 0, alpha1),
            width=4,
        )

    r2 = int(max_radius * 0.6 * ease_out_quad(progress))
    if r2 > 0:
        draw.ellipse(
            [target_x - r2, target_y - r2, target_x + r2, target_y + r2],
            fill=(255, 60, 0, int(alpha1 * 0.5)),
        )

    # 爆発の中心に Emote
    if progress < 0.7:
        draw_emote(
            canvas, "emote_anger", target_x, target_y - 20, size=32, anchor="center"
        )

    # シナジー名ポップアップ
    f = get_font(13)
    draw.text(
        (target_x - 70, target_y - 85),
        f"🔥 {synergy_name}! 🔥",
        font=f,
        fill=(255, 200, 50, 255),
    )


def draw_damage_number(
    canvas: Image.Image,
    x: int,
    y: int,
    damage: int,
    progress: float,
    is_crit: bool = False,
):
    """跳ねるダメージ数値ポップアップ"""
    draw = ImageDraw.Draw(canvas)

    # 上に跳ね上がる放物線
    jump_y = -math.sin(progress * math.pi) * 35 - progress * 15
    cur_y = y + jump_y

    # 拡大と透明度
    alpha = int(255 * (1.0 - progress * 0.7))
    color = (255, 60, 60, alpha) if not is_crit else (255, 230, 40, alpha)
    f = get_font(18 if is_crit else 14)

    txt = f"-{damage}!" if is_crit else f"-{damage}"
    # 縁取り付き描画
    draw.text((x - 1, cur_y), txt, font=f, fill=(0, 0, 0, alpha))
    draw.text((x + 1, cur_y), txt, font=f, fill=(0, 0, 0, alpha))
    draw.text((x, cur_y - 1), txt, font=f, fill=(0, 0, 0, alpha))
    draw.text((x, cur_y + 1), txt, font=f, fill=(0, 0, 0, alpha))
    draw.text((x, cur_y), txt, font=f, fill=color)


def generate_combat_devour_gif(output_path: Path):
    """戦闘・捕食・シナジー爆発を描画するGIF1を生成"""
    frames = []

    # タイムライン設計 (30fps)
    # 0.0s - 1.0s (30F): 敵と対峙・スキャン解析
    # 1.0s - 2.0s (30F): 主人公の斬撃 ＆ 炎シナジー爆発 ＆ ダメージ表示
    # 2.0s - 3.5s (45F): 《喰らい》発動、光球吸収アニメーション
    # 3.5s - 4.5s (30F): 捕食完了フラッシュ ＆ 獲得スキルバナー

    hero_x, hero_y = 160, 200
    enemy_x, enemy_y = 480, 200

    # フェーズ1: 対峙 & スキャン (30フレーム)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c, hp=100, max_hp=100, mp=50, max_mp=50, title="Phase 1: Deep Scan & Combat"
        )

        # 呼吸アニメーション (わずかにY座標が上下)
        hy = hero_y + int(math.sin(i * 0.2) * 3)
        ey = enemy_y + int(math.sin(i * 0.2 + 1) * 3)

        draw_sprite(c, "TR_HERO_IDLE_01", hero_x, hy, scale=4, anchor="center")
        draw_sprite(c, "TR_MONSTER_01", enemy_x, ey, scale=4, anchor="center")

        # 敵HPバー
        draw_health_bar(
            ImageDraw.Draw(c),
            enemy_x - 40,
            ey - 50,
            80,
            8,
            120,
            120,
            label="Abyssal Drake",
        )

        # スキャンエフェクト
        draw_scan_effect(c, enemy_x, ey, i / 30.0)
        frames.append(c)

    # フェーズ2: 攻撃 & シナジー爆発 (30フレーム)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=40,
            max_mp=50,
            title="Phase 1: Thermal Synergy Triggered!",
        )

        p = i / 30.0
        # 主人公の踏み込み
        dash_x = hero_x + (int(math.sin(p * math.pi) * 80) if p < 0.5 else 0)
        draw_sprite(c, "TR_HERO_IDLE_01", dash_x, hero_y, scale=4, anchor="center")

        # 敵の被弾リアクション（点滅・シェイク）
        enemy_shake = int(math.sin(i * 1.5) * 6) if i < 15 else 0
        enemy_hp = max(10, int(120 - (i / 15.0) * 110))

        draw_sprite(
            c, "TR_MONSTER_01", enemy_x + enemy_shake, hero_y, scale=4, anchor="center"
        )
        draw_health_bar(
            ImageDraw.Draw(c),
            enemy_x - 40,
            hero_y - 50,
            80,
            8,
            enemy_hp,
            120,
            label="Abyssal Drake",
        )

        # シナジー爆発
        draw_synergy_explosion(c, enemy_x, hero_y, p, synergy_name="THERMAL EXPLOSION")
        # ダメージ数値
        if i >= 5:
            draw_damage_number(
                c, enemy_x + 10, hero_y - 30, 280, (i - 5) / 25.0, is_crit=True
            )

        frames.append(c)

    # フェーズ3: 《喰らい》吸収 (45フレーム)
    for i in range(45):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=30,
            max_mp=50,
            title="Phase 1: Devouring Core Skill...",
        )

        p = i / 45.0
        draw_sprite(c, "TR_HERO_IDLE_01", hero_x, hero_y, scale=4, anchor="center")

        # 敵は衰弱（暗く・縮小気味）
        draw_sprite(c, "TR_MONSTER_01", enemy_x, hero_y, scale=3, anchor="center")
        draw_health_bar(
            ImageDraw.Draw(c),
            enemy_x - 40,
            hero_y - 50,
            80,
            8,
            0,
            120,
            label="Drake Husk",
        )

        # 捕食パーティクル
        draw_devour_particles(c, enemy_x, hero_y, hero_x, hero_y, p)
        frames.append(c)

    # フェーズ4: 捕食成功＆バナー (35フレーム)
    for i in range(35):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=120,
            max_hp=120,
            mp=60,
            max_mp=60,
            title="Phase 1: Devour Complete! (Stats Up)",
        )

        draw_sprite(c, "TR_HERO_IDLE_01", hero_x, hero_y, scale=4, anchor="center")

        # 一瞬画面フラッシュ
        if i < 4:
            flash = Image.new("RGBA", (WIDTH, HEIGHT), (160, 40, 220, 120))
            c = Image.alpha_composite(c, flash)

        draw_devour_burst(c, hero_x, hero_y, skill_name="Inferno Breath Lv.1")
        frames.append(c)

    save_gif(frames, output_path, fps=30)


def draw_alchemy_station(
    canvas: Image.Image,
    center_x: int,
    center_y: int,
    skill_a_name: str,
    skill_b_name: str,
    slot_offset_x: int = 120,
):
    """錬金・合成炉と2つの素材スキル枠を描画"""
    draw = ImageDraw.Draw(canvas)

    # 中央の大釜 / 炉
    draw_sprite(
        canvas, "TR_CHEST_01", center_x, center_y + 10, scale=4, anchor="center"
    )

    # 素材スキルA（左側）
    slot_a_x = center_x - slot_offset_x
    draw.rectangle(
        [slot_a_x - 60, center_y - 25, slot_a_x + 60, center_y + 25],
        fill=(30, 30, 45, 220),
        outline=(0, 200, 255, 255),
        width=2,
    )
    f = get_font(12)
    draw.text(
        (slot_a_x - 50, center_y - 8), skill_a_name, font=f, fill=(200, 240, 255, 255)
    )

    # 素材スキルB（右側）
    slot_b_x = center_x + slot_offset_x
    draw.rectangle(
        [slot_b_x - 60, center_y - 25, slot_b_x + 60, center_y + 25],
        fill=(45, 30, 30, 220),
        outline=(255, 100, 50, 255),
        width=2,
    )
    draw.text(
        (slot_b_x - 50, center_y - 8), skill_b_name, font=f, fill=(255, 220, 200, 255)
    )


def draw_synthesis_merging(
    canvas: Image.Image,
    center_x: int,
    center_y: int,
    skill_a_name: str,
    skill_b_name: str,
    progress: float,
):
    """2つのスキルが中央の炉へ吸い込まれるアニメーション"""
    draw = ImageDraw.Draw(canvas)

    # 距離の縮まり
    max_offset = 120
    cur_offset = int(lerp(max_offset, 0, ease_in_out_quad(progress)))

    # スキルAスロット
    slot_a_x = center_x - cur_offset
    alpha = int(255 * (1.0 - progress * 0.4))
    draw.rectangle(
        [slot_a_x - 50, center_y - 20, slot_a_x + 50, center_y + 20],
        fill=(30, 30, 45, alpha),
        outline=(0, 200, 255, alpha),
        width=2,
    )
    f = get_font(11)
    draw.text(
        (slot_a_x - 42, center_y - 7), skill_a_name, font=f, fill=(200, 240, 255, alpha)
    )

    # スキルBスロット
    slot_b_x = center_x + cur_offset
    draw.rectangle(
        [slot_b_x - 50, center_y - 20, slot_b_x + 50, center_y + 20],
        fill=(45, 30, 30, alpha),
        outline=(255, 100, 50, alpha),
        width=2,
    )
    draw.text(
        (slot_b_x - 42, center_y - 7), skill_b_name, font=f, fill=(255, 220, 200, alpha)
    )

    # 炉
    draw_sprite(
        canvas, "TR_CHEST_01", center_x, center_y + 10, scale=4, anchor="center"
    )


def draw_alchemy_circle(
    canvas: Image.Image, center_x: int, center_y: int, progress: float
):
    """合成時の回転魔法陣と輝きエフェクト"""
    draw = ImageDraw.Draw(canvas)

    # 魔法陣の外枠円
    r = 65
    draw.ellipse(
        [center_x - r, center_y - r, center_x + r, center_y + r],
        outline=(100, 200, 255, 200),
        width=2,
    )
    draw.ellipse(
        [center_x - r + 8, center_y - r + 8, center_x + r - 8, center_y + r - 8],
        outline=(150, 100, 255, 180),
        width=1,
    )

    # 回転する幾何学ポリゴン（六角形）
    angle_offset = progress * math.pi * 2
    points = []
    for i in range(6):
        a = angle_offset + i * (math.pi / 3)
        px = center_x + int(math.cos(a) * (r - 12))
        py = center_y + int(math.sin(a) * (r - 12))
        points.append((px, py))
    draw.polygon(points, outline=(200, 150, 255, 220))

    # 炉中央のEmote
    draw_emote(canvas, "emote_dots2", center_x, center_y - 45, size=24, anchor="center")


def draw_synthesis_success(
    canvas: Image.Image,
    center_x: int,
    center_y: int,
    new_skill_name: str = "Inferno Storm Slash",
):
    """融合成功時の稲妻・新スキル誕生バナー演出"""
    draw = ImageDraw.Draw(canvas)

    # 炉の上で輝くキメラスキルアイコン枠
    slot_w, slot_h = 220, 48
    draw.rectangle(
        [
            center_x - slot_w // 2,
            center_y - 60,
            center_x + slot_w // 2,
            center_y - 60 + slot_h,
        ],
        fill=(60, 20, 80, 240),
        outline=(255, 215, 0, 255),
        width=3,
    )

    f_title = get_font(13)
    draw.text(
        (center_x - 90, center_y - 52),
        "★ CHIMERA SYNTHESIS ★",
        font=f_title,
        fill=(255, 230, 100, 255),
    )
    f_name = get_font(12)
    draw.text(
        (center_x - 80, center_y - 32),
        new_skill_name,
        font=f_name,
        fill=(100, 255, 230, 255),
    )

    # スターエフェクト
    draw_emote(canvas, "emote_stars", center_x, center_y - 95, size=40, anchor="center")
    draw_emote(
        canvas, "emote_star", center_x - 120, center_y - 60, size=24, anchor="center"
    )
    draw_emote(
        canvas, "emote_star", center_x + 120, center_y - 60, size=24, anchor="center"
    )

    # 炉
    draw_sprite(
        canvas, "TR_CHEST_01", center_x, center_y + 10, scale=4, anchor="center"
    )


def draw_wipe_transition(canvas: Image.Image, progress: float):
    """場面転換用のダーク水平ワイプエフェクト"""
    draw = ImageDraw.Draw(canvas)
    wipe_w = int(WIDTH * progress)
    draw.rectangle([0, 0, wipe_w, HEIGHT], fill=(10, 10, 15, 255))


def draw_black_market_scene(canvas: Image.Image):
    """闇市場（怪しい取引所）の背景と密売ディーラーの描画"""
    draw = ImageDraw.Draw(canvas)
    # 暗いダンジョン背景
    draw_dungeon_background(canvas, floor_tile="TR_FLOOR_02", wall_tile="TR_WALL_01")

    # 闇ディーラー（NPCスプライト）と主人公
    draw_sprite(canvas, "TR_HERO_IDLE_01", 180, 200, scale=4, anchor="center")
    draw_sprite(canvas, "TR_MONSTER_01", 460, 200, scale=4, anchor="center")

    # 取引カウンター / 宝箱
    draw_sprite(canvas, "TR_CHEST_01", 320, 210, scale=3, anchor="center")

    # ネオン看板
    draw.rectangle(
        [220, 50, 420, 85], fill=(20, 15, 30, 240), outline=(255, 50, 120, 255), width=2
    )
    f = get_font(13)
    draw.text((235, 60), "☠ UNDERGROUND MARKET ☠", font=f, fill=(255, 80, 150, 255))


def draw_black_market_deal(
    canvas: Image.Image,
    center_x: int,
    center_y: int,
    progress: float,
    earned_gold: int = 2400,
):
    """密売成立時のコイン散乱とゴールド獲得演出"""
    draw = ImageDraw.Draw(canvas)

    # 飛び散るコイン (emote_cash)
    cash_offsets = [
        (-50, -40),
        (50, -50),
        (-80, 10),
        (80, 0),
        (0, -70),
        (-30, 40),
        (40, 50),
    ]
    for idx, (ox, oy) in enumerate(cash_offsets):
        # 個別に跳ねるアニメーション
        p = min(1.0, progress * 1.5 + idx * 0.05)
        fly_x = center_x + int(ox * p)
        fly_y = center_y + int(oy * p - math.sin(p * math.pi) * 30)
        draw_emote(canvas, "emote_cash", fly_x, fly_y, size=24, anchor="center")

    # 取引メッセージ
    deal_box_w = 260
    draw.rectangle(
        [
            center_x - deal_box_w // 2,
            center_y - 100,
            center_x + deal_box_w // 2,
            center_y - 60,
        ],
        fill=(20, 30, 20, 240),
        outline=(50, 255, 100, 255),
        width=2,
    )
    f = get_font(13)
    draw.text(
        (center_x - 110, center_y - 92),
        f"CONTRABAND SOLD: +{earned_gold} G",
        font=f,
        fill=(255, 235, 80, 255),
    )


def draw_inquisition_raid(canvas: Image.Image, progress: float):
    """異端審問官レイド発生時の赤色ストロボ警報演出"""
    draw = ImageDraw.Draw(canvas)

    # 画面全体の赤色明滅
    alpha = int(120 * abs(math.sin(progress * math.pi * 3)))
    overlay = Image.new("RGBA", canvas.size, (255, 0, 0, alpha))
    canvas.paste(Image.alpha_composite(canvas, overlay), (0, 0))

    # 警告バナー
    draw.rectangle(
        [0, HEIGHT // 2 - 35, WIDTH, HEIGHT // 2 + 35],
        fill=(40, 5, 5, 230),
        outline=(255, 40, 40, 255),
        width=2,
    )
    f_warn = get_font(16)
    draw.text(
        (WIDTH // 2 - 140, HEIGHT // 2 - 24),
        "⚠ INQUISITION RAID DETECTED! ⚠",
        font=f_warn,
        fill=(255, 80, 80, 255),
    )
    f_sub = get_font(12)
    draw.text(
        (WIDTH // 2 - 110, HEIGHT // 2 + 6),
        "Audit Level Critical: Contraband Confiscation Imminent",
        font=f_sub,
        fill=(255, 200, 200, 255),
    )

    # 左右に警報アイコン
    draw_emote(canvas, "emote_alert", 100, HEIGHT // 2, size=36, anchor="center")
    draw_emote(
        canvas, "emote_alert", WIDTH - 100, HEIGHT // 2, size=36, anchor="center"
    )


def generate_synthesis_economy_gif(output_path: Path):
    """合成＆経済（闇市場・レイド）を描画するGIF2を生成"""
    frames = []

    # タイムライン (30fps)
    # 0.0s - 1.0s (30F): 2つのスキルを炉へセット
    # 1.0s - 2.0s (30F): スキル合体＆魔法陣回転
    # 2.0s - 3.2s (35F): キメラスキル完成バナー
    # 3.2s - 3.5s (10F): ワイプで場面転換
    # 3.5s - 4.5s (30F): 闇市場での密売＆コイン散乱
    # 4.5s - 5.5s (30F): 監査官レイド警報

    cx, cy = 320, 190

    # パート1: 炉とスキル配置 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c, hp=100, max_hp=100, mp=50, max_mp=50, title="Phase 2: Chimera Synthesis"
        )
        p = i / 30.0
        offset = int(lerp(180, 120, ease_out_quad(p)))
        draw_alchemy_station(
            c, cx, cy, "Flame Strike", "Gale Slash", slot_offset_x=offset
        )
        frames.append(c)

    # パート2: 吸い込み＆魔法陣回転 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            title="Phase 2: Transmuting Elements...",
        )
        p = i / 30.0
        draw_synthesis_merging(c, cx, cy, "Flame Strike", "Gale Slash", p)
        draw_alchemy_circle(c, cx, cy, p)
        frames.append(c)

    # パート3: キメラスキル完成 (35F)
    for i in range(35):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c, hp=100, max_hp=100, mp=50, max_mp=50, title="Phase 2: Fusion Complete!"
        )
        if i < 4:
            flash = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 200, 150))
            c = Image.alpha_composite(c, flash)
        draw_synthesis_success(c, cx, cy, "Inferno Storm Slash")
        frames.append(c)

    # パート4: ワイプ場面転換 (10F)
    for i in range(10):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_black_market_scene(c)
        draw_wipe_transition(c, 1.0 - (i / 10.0))
        frames.append(c)

    # パート5: 闇市場密売 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_black_market_scene(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            title="Phase 2: Black Market Contraband",
        )
        p = i / 30.0
        draw_black_market_deal(c, 320, 200, p, earned_gold=3600)
        frames.append(c)

    # パート6: 監査官レイド警報 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_black_market_scene(c)
        draw_hud(
            c, hp=100, max_hp=100, mp=50, max_mp=50, title="Phase 2: RAID ALERT LEVEL 5"
        )
        p = i / 30.0
        draw_inquisition_raid(c, p)
        frames.append(c)

    save_gif(frames, output_path, fps=30)


def draw_cyber_terminal(canvas: Image.Image, progress: float):
    """ROOTハック時のサイバーコンソールとログストリーム描画"""
    draw = ImageDraw.Draw(canvas)

    # 背景をダークシアン/ブラックに
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(5, 12, 18, 255))

    # グリッド線
    for y in range(0, HEIGHT, 20):
        draw.line([(0, y), (WIDTH, y)], fill=(10, 30, 40, 100), width=1)
    for x in range(0, WIDTH, 30):
        draw.line([(x, 0), (x, HEIGHT)], fill=(10, 30, 40, 100), width=1)

    # コンソールログ
    logs = [
        "[*] INITIATING ROOT PRIVILEGE ESCALATION...",
        "[*] CONNECTING TO SYSTEM CORE INTERFACE 0x7FFF...",
        "[*] BYPASSING SANCTUARY FIREWALL [SUCCESS]",
        "[*] INJECTING KERNEL OVERRIDE: SYS_PARAM_MODIFIER",
        "[*] MEMORY CONSUMPTION: 84.2% (HEURISTIC STABLE)",
        "[+] ROOT ACCESS GRANTED. ENTERING LAWS OVERRIDE MODE...",
    ]

    f_log = get_font(12)
    max_lines = int(progress * (len(logs) + 1))
    for i in range(min(len(logs), max_lines)):
        draw.text((30, 45 + i * 22), logs[i], font=f_log, fill=(0, 255, 180, 255))


def apply_crt_glitch(canvas: Image.Image, intensity: float = 0.5) -> Image.Image:
    """CRTモニター風の走査線とサイバーグリッチ（横ズレ）効果"""
    res = canvas.copy()
    draw = ImageDraw.Draw(res)

    # 走査線（スキャンライン）
    for y in range(0, HEIGHT, 4):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, 80), width=1)

    # 水平スライスズレ
    num_glitches = int(6 * intensity)
    for _ in range(num_glitches):
        gy = random.randint(10, HEIGHT - 30)
        gh = random.randint(4, 20)
        shift = random.randint(-15, 15)

        # 切り出してずらして貼り付け
        slice_box = (0, gy, WIDTH, gy + gh)
        glitch_slice = canvas.crop(slice_box)
        res.paste(glitch_slice, (shift, gy))

    return res


def draw_laws_override_ui(
    canvas: Image.Image,
    rule_text: str = "GLOBAL DAMAGE MULTIPLIER: 1.0x -> 2.5x",
    cost_text: str = "COST: MAX HP -25%",
):
    """世界法則書き換え（ROOT OVERRIDE）ダイアログとアイデア閃き"""
    draw = ImageDraw.Draw(canvas)

    # 中央のサイバーウィンドウ
    win_w, win_h = 440, 120
    wx = WIDTH // 2 - win_w // 2
    wy = HEIGHT // 2 - win_h // 2

    draw.rectangle(
        [wx, wy, wx + win_w, wy + win_h],
        fill=(10, 20, 30, 245),
        outline=(0, 255, 230, 255),
        width=2,
    )
    # タイトルバー
    draw.rectangle([wx, wy, wx + win_w, wy + 26], fill=(0, 100, 120, 255))
    f_bar = get_font(12)
    draw.text(
        (wx + 10, wy + 6),
        "[!] SYSTEM LAW OVERRIDE APPLIED",
        font=f_bar,
        fill=(255, 255, 255, 255),
    )

    # 本文
    f_main = get_font(13)
    draw.text((wx + 20, wy + 42), rule_text, font=f_main, fill=(0, 255, 200, 255))
    draw.text((wx + 20, wy + 72), cost_text, font=f_main, fill=(255, 100, 100, 255))

    # 閃きアイコン
    draw_emote(
        canvas, "emote_idea", WIDTH // 2 + 180, wy + 10, size=32, anchor="center"
    )


def draw_corruption_penalty(canvas: Image.Image, progress: float):
    """代償支払いによるHP最大値減少演出"""
    draw = ImageDraw.Draw(canvas)

    # ゲージが削られるアニメーション
    cur_max = int(lerp(100, 75, ease_out_quad(progress)))
    draw_hud(
        canvas,
        hp=cur_max,
        max_hp=cur_max,
        mp=50,
        max_mp=50,
        title="Phase 3: Sanity Erosion & Law Binding",
    )

    # 侵食警告
    draw.rectangle(
        [WIDTH // 2 - 120, 50, WIDTH // 2 + 120, 85],
        fill=(50, 10, 20, 220),
        outline=(255, 60, 60, 255),
        width=2,
    )
    f = get_font(12)
    draw.text(
        (WIDTH // 2 - 100, 60),
        "SANITY EROSION: +25% [CORRUPTED]",
        font=f,
        fill=(255, 120, 120, 255),
    )
    draw_emote(canvas, "emote_drop", WIDTH // 2 + 100, 68, size=20, anchor="center")


def draw_reincarnation_collapse(canvas: Image.Image, progress: float):
    """輪廻転生時の世界崩壊・中心からのブラックアウト演出"""
    draw = ImageDraw.Draw(canvas)

    # 中心から広がる黒の暗黒球
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_diag = int(math.sqrt(cx * cx + cy * cy) * 1.2)
    cur_r = int(max_diag * ease_in_out_quad(progress))

    if cur_r > 0:
        draw.ellipse(
            [cx - cur_r, cy - cur_r, cx + cur_r, cy + cur_r],
            fill=(5, 5, 10, 255),
            outline=(120, 50, 200, 255),
            width=3,
        )

    # 吸い込まれる歪みエフェクトアイコン
    if progress < 0.7:
        draw_emote(
            canvas,
            "emote_swirl",
            cx,
            cy,
            size=int(48 * (1.0 + progress)),
            anchor="center",
        )


def draw_karma_settlement(canvas: Image.Image, progress: float):
    """前世のカルマ清算ログ画面（ブラックアウト中）"""
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(5, 5, 8, 255))

    f_title = get_font(15)
    draw.text(
        (WIDTH // 2 - 120, 50),
        "=== CYCLE SETTLEMENT ===",
        font=f_title,
        fill=(255, 215, 0, 255),
    )

    k_logs = [
        "TOTAL SKILLS DEVOUR: 42 (+840 KARMA)",
        "ROOT OVERRIDES EXECUTED: 3 (+600 KARMA)",
        "CORRUPTION LEVEL AT COLLAPSE: 89%",
        "HEREDITARY GENES UNLOCKED: [Void Core Lv.2]",
    ]

    f_log = get_font(13)
    max_k = int(progress * (len(k_logs) + 1))
    for i in range(min(len(k_logs), max_k)):
        draw.text(
            (WIDTH // 2 - 160, 100 + i * 28),
            f"> {k_logs[i]}",
            font=f_log,
            fill=(200, 240, 255, 255),
        )


def draw_reborn_intro(canvas: Image.Image, progress: float):
    """輪廻転生後の新世界・新生主人公のフェードイン演出"""
    draw_dungeon_background(canvas, floor_tile="TR_FLOOR_03", wall_tile="TR_WALL_01")
    draw_hud(
        canvas,
        hp=120,
        max_hp=120,
        mp=60,
        max_mp=60,
        title="Cycle #2: Reborn with Inherited Skills",
    )

    # 主人公スプライト
    draw_sprite(
        canvas,
        "TR_HERO_IDLE_01",
        WIDTH // 2,
        HEIGHT // 2 + 20,
        scale=4,
        anchor="center",
    )

    # 新生ハートエフェクト
    draw_emote(
        canvas, "emote_heart", WIDTH // 2, HEIGHT // 2 - 35, size=32, anchor="center"
    )

    # 新生バナー
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [WIDTH // 2 - 150, 60, WIDTH // 2 + 150, 95],
        fill=(20, 40, 30, 230),
        outline=(0, 255, 180, 255),
        width=2,
    )
    f = get_font(13)
    draw.text(
        (WIDTH // 2 - 130, 70),
        "NEW INCARNATION INITIATED",
        font=f,
        fill=(100, 255, 200, 255),
    )

    # フェードイン用ブラックマスク
    alpha = int(255 * (1.0 - progress))
    if alpha > 0:
        mask = Image.new("RGBA", canvas.size, (0, 0, 0, alpha))
        canvas.paste(Image.alpha_composite(canvas, mask), (0, 0))


def generate_meta_reincarnation_gif(output_path: Path):
    """メタハック＆輪廻転生を描画するGIF3を生成"""
    frames = []

    # タイムライン (30fps)
    # 0.0s - 1.2s (35F): サイバーターミナルハックログ
    # 1.2s - 2.2s (30F): 世界法則書き換えUI & グリッチ
    # 2.2s - 3.0s (25F): 精神侵食・HP削れ代償
    # 3.0s - 4.0s (30F): 暗黒球・世界崩壊
    # 4.0s - 5.0s (30F): カルマ清算ログ
    # 5.0s - 6.0s (30F): 新生フェードイン

    # パート1: サイバーログ (35F)
    for i in range(35):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        p = i / 35.0
        draw_cyber_terminal(c, p)
        if i > 25:
            c = apply_crt_glitch(c, intensity=0.3)
        frames.append(c)

    # パート2: 法則書き換えUI (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_cyber_terminal(c, 1.0)
        draw_laws_override_ui(c)
        if i % 8 == 0:
            c = apply_crt_glitch(c, intensity=0.6)
        frames.append(c)

    # パート3: 代償・侵食 (25F)
    for i in range(25):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_cyber_terminal(c, 1.0)
        draw_laws_override_ui(c)
        draw_corruption_penalty(c, i / 25.0)
        frames.append(c)

    # パート4: 世界崩壊 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_cyber_terminal(c, 1.0)
        draw_reincarnation_collapse(c, i / 30.0)
        frames.append(c)

    # パート5: カルマ清算 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_karma_settlement(c, i / 30.0)
        frames.append(c)

    # パート6: 新生フェードイン (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_reborn_intro(c, i / 30.0)
        frames.append(c)

    save_gif(frames, output_path, fps=30)


def draw_husk_sprite(
    canvas: Image.Image, tile_key: str, x: int, y: int, scale: int = 4
):
    """抜け殻（Husk）状態の暗く色あせた敵スプライト"""
    sprite = atlas.get_tile(tile_key, scale=scale).copy()
    # グレースケール化＆暗色化
    gray = sprite.convert("L").point(lambda p: int(p * 0.45))
    husk_img = Image.merge("RGBA", (gray, gray, gray, sprite.split()[3]))

    w, h = husk_img.size
    canvas.paste(husk_img, (x - w // 2, y - h // 2), husk_img)


def draw_skill_implantation(
    canvas: Image.Image,
    hero_x: int,
    hero_y: int,
    husk_x: int,
    husk_y: int,
    progress: float,
):
    """主人公からHuskへの魔力回路・スキル移植ビーム演出"""
    draw = ImageDraw.Draw(canvas)

    # 進行ビーム先端
    cur_x = lerp(hero_x, husk_x, progress)
    cur_y = lerp(hero_y, husk_y, progress)

    # メインビーム
    draw.line([(hero_x, hero_y), (cur_x, cur_y)], fill=(0, 255, 230, 220), width=4)
    draw.line([(hero_x, hero_y), (cur_x, cur_y)], fill=(255, 255, 255, 255), width=2)

    # 周囲の放電・稲妻
    for _ in range(3):
        ox1 = random.randint(-10, 10)
        oy1 = random.randint(-10, 10)
        mid_x = (hero_x + cur_x) / 2 + ox1
        mid_y = (hero_y + cur_y) / 2 + oy1
        draw.line(
            [(hero_x, hero_y), (mid_x, mid_y), (cur_x, cur_y)],
            fill=(100, 200, 255, 180),
            width=1,
        )


def draw_servant_awakening(canvas: Image.Image, husk_x: int, husk_y: int):
    """従属者覚醒時の赤目点灯とemote_heartエフェクト"""
    draw = ImageDraw.Draw(canvas)

    # 覚醒スプライト（通常カラーで再描画）
    draw_sprite(canvas, "TR_MONSTER_01", husk_x, husk_y, scale=4, anchor="center")

    # 目が赤く光るグロー
    eye_lx, eye_rx, eye_y = husk_x - 12, husk_x + 12, husk_y - 12
    draw.ellipse(
        [eye_lx - 4, eye_y - 4, eye_lx + 4, eye_y + 4], fill=(255, 30, 30, 255)
    )
    draw.ellipse(
        [eye_rx - 4, eye_y - 4, eye_rx + 4, eye_y + 4], fill=(255, 30, 30, 255)
    )

    # 忠誠ハートアイコン
    draw_emote(canvas, "emote_heart", husk_x, husk_y - 45, size=28, anchor="center")

    # 覚醒テキスト
    f = get_font(12)
    draw.text(
        (husk_x - 70, husk_y - 75),
        "[SERVANT TURRET AWAKENED]",
        font=f,
        fill=(255, 100, 100, 255),
    )


def draw_servant_attack(
    canvas: Image.Image,
    servant_x: int,
    servant_y: int,
    target_x: int,
    target_y: int,
    progress: float,
):
    """従属者の自律射撃・エネルギー弾道演出"""
    draw = ImageDraw.Draw(canvas)

    # 弾道位置
    bullet_x = lerp(servant_x, target_x, progress)
    bullet_y = lerp(servant_y, target_y, progress)

    # エネルギー弾
    r = 8
    draw.ellipse(
        [bullet_x - r, bullet_y - r, bullet_x + r, bullet_y + r],
        fill=(255, 100, 50, 255),
        outline=(255, 255, 200, 255),
        width=2,
    )

    # 砲火マズルフラッシュ
    if progress < 0.3:
        draw_emote(
            canvas, "emote_anger", servant_x - 30, servant_y, size=24, anchor="center"
        )


def draw_servant_lifespan(
    canvas: Image.Image, servant_x: int, servant_y: int, remaining_turns: int
):
    """従属者タレットの残り寿命（ターン数）バッジ表示"""
    draw = ImageDraw.Draw(canvas)

    badge_w, badge_h = 90, 22
    bx = servant_x - badge_w // 2
    by = servant_y - 65

    color = (200, 50, 50) if remaining_turns <= 1 else (50, 180, 220)
    draw.rectangle(
        [bx, by, bx + badge_w, by + badge_h],
        fill=(20, 20, 30, 220),
        outline=(*color, 255),
        width=2,
    )
    f = get_font(11)
    draw.text(
        (bx + 8, by + 4),
        f"LIFESPAN: {remaining_turns}T",
        font=f,
        fill=(255, 255, 255, 255),
    )


def draw_servant_overload(
    canvas: Image.Image, servant_x: int, servant_y: int, frame_i: int
):
    """寿命限界による過負荷・小刻みなシェイク演出"""
    shake_x = servant_x + random.randint(-5, 5)
    shake_y = servant_y + random.randint(-4, 4)
    draw_sprite(canvas, "TR_MONSTER_01", shake_x, shake_y, scale=4, anchor="center")

    # 警告アイコン
    draw_emote(canvas, "emote_alert", shake_x, shake_y - 45, size=28, anchor="center")
    draw_servant_lifespan(canvas, shake_x, shake_y, 0)


def draw_servant_destruction(
    canvas: Image.Image, servant_x: int, servant_y: int, progress: float
):
    """自壊崩壊時のピクセル破片散乱とemote_faceSadの哀愁演出"""
    draw = ImageDraw.Draw(canvas)

    # 破片パーティクル散乱
    num_particles = 30
    for idx in range(num_particles):
        angle = (idx / num_particles) * math.pi * 2
        dist = lerp(0, 70, ease_out_quad(progress)) + (idx % 5) * 4
        px = servant_x + int(math.cos(angle) * dist)
        py = servant_y + int(math.sin(angle) * dist + progress * 20)  # 重力落下

        alpha = int(255 * (1.0 - progress))
        size = max(1, int(4 * (1.0 - progress * 0.5)))
        color = (120, 100, 140, alpha) if idx % 2 == 0 else (200, 50, 50, alpha)
        draw.rectangle([px - size, py - size, px + size, py + size], fill=color)

    # 哀愁のemote_faceSad
    draw_emote(
        canvas, "emote_faceSad", servant_x, servant_y - 20, size=32, anchor="center"
    )

    # ログ
    f = get_font(12)
    draw.text(
        (servant_x - 70, servant_y - 65),
        "[SERVANT DESTROYED]",
        font=f,
        fill=(180, 180, 200, 255),
    )


def generate_husk_servant_gif(output_path: Path):
    """従属者タレット（Husk操縦・射撃・自壊）を描画するGIF4を生成"""
    frames = []

    # タイムライン (30fps)
    # 0.0s - 1.0s (30F): 主人公と抜け殻（Husk）の対峙
    # 1.0s - 2.2s (35F): スキル移植ビーム
    # 2.2s - 3.2s (30F): 覚醒 ＆ 忠誠エフェクト
    # 3.2s - 4.2s (30F): 自律射撃（ターン消費 3->2->1）
    # 4.2s - 5.0s (25F): 寿命限界・過負荷シェイク (0T)
    # 5.0s - 6.0s (30F): 自壊・粉砕・哀愁ログ

    hx, hy = 160, 200
    sx, sy = 480, 200

    # パート1: 対峙 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            title="Phase 4: Dead Monster Husk Discovered",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_husk_sprite(c, "TR_MONSTER_01", sx, sy, scale=4)
        frames.append(c)

    # パート2: 移植ビーム (35F)
    for i in range(35):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=35,
            max_mp=50,
            title="Phase 4: Implanting Skill Circuit...",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_husk_sprite(c, "TR_MONSTER_01", sx, sy, scale=4)
        draw_skill_implantation(c, hx, hy, sx, sy, i / 35.0)
        frames.append(c)

    # パート3: 覚醒 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=35,
            max_mp=50,
            title="Phase 4: Turret Servant Online",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_servant_awakening(c, sx, sy)
        draw_servant_lifespan(c, sx, sy, 3)
        frames.append(c)

    # パート4: 自律射撃 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=35,
            max_mp=50,
            title="Phase 4: Autonomous Turret Fire",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_sprite(c, "TR_MONSTER_01", sx, sy, scale=4, anchor="center")
        draw_servant_lifespan(c, sx, sy, 2 if i < 15 else 1)
        p = (i % 15) / 15.0
        draw_servant_attack(c, sx, sy, 0, sy, p)
        frames.append(c)

    # パート5: 過負荷シェイク (25F)
    for i in range(25):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=35,
            max_mp=50,
            title="Phase 4: Critical Lifespan Exceeded!",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_servant_overload(c, sx, sy, i)
        frames.append(c)

    # パート6: 自壊 (30F)
    for i in range(30):
        c = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw_dungeon_background(c)
        draw_hud(
            c,
            hp=100,
            max_hp=100,
            mp=35,
            max_mp=50,
            title="Phase 4: Servant Disassembled",
        )
        draw_sprite(c, "TR_HERO_IDLE_01", hx, hy, scale=4, anchor="center")
        draw_servant_destruction(c, sx, sy, i / 30.0)
        frames.append(c)

    save_gif(frames, output_path, fps=30)


if __name__ == "__main__":
    out_gif4 = Path("e:/narou2/assets/demo_husk_servant.gif")
    generate_husk_servant_gif(out_gif4)
