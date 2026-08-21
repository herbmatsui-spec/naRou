"""
generate_readme_gifs.py

README 用のデモ GIF を「実際のゲーム画面」に極力近い見た目で生成する。
naRou は tcod コンソール (80x50 グリッド) の本格ローグライク。このスクリプトは
game の描画パイプライン (render_system.py / uirenderer.py / map_renderer.py /
entity_renderer.py / item_renderer.py / ui_fx_systems.py) の見た目を
PIL で再現し、4 大スキル喰い演出をアニメーションさせる。

出力:
  assets/demo_combat_devour.gif
  assets/demo_synthesis_economy.gif
  assets/demo_meta_reincarnation.gif
  assets/demo_husk_servant.gif
"""
from __future__ import annotations

import copy
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 画面定数 (constants.py / uirenderer.py に合わせる)
# ---------------------------------------------------------------------------
SCREEN_W = 80
SCREEN_H = 50
VIEW_W = 80
VIEW_H = 38
UI_Y = VIEW_H  # 38

CELL_W = 11
CELL_H = 18
FONT_SIZE = 18

# カラーパレット (constants.py から)
BG = (8, 10, 16)
WALL_LIT = (145, 120, 90)
WALL_DARK = (35, 35, 45)
FLOOR_LIT = (195, 175, 145)
FLOOR_DARK = (18, 18, 25)
ALTAR = (255, 215, 0)
HP_COL = (100, 255, 100)
MP_COL = (100, 200, 255)
GOLD_COL = (255, 215, 0)
PET_COL = (255, 180, 210)
SEP_COL = (60, 70, 90)
NAME_COL = (255, 255, 160)
TEXT_WHITE = (230, 235, 245)
MUTED = (150, 165, 190)
ENEMY_COL = (255, 90, 90)
NEUTRAL = (200, 200, 200)
PANEL_FG = (100, 180, 255)
WARN_COL = (255, 90, 90)
CRIT_COL = (255, 230, 80)
SCAN_COL = (0, 255, 200)
DEVOUR_COL = (220, 100, 255)
SUCCESS_COL = (255, 220, 100)

FONTS = [
    ("C:/Windows/Fonts/BIZ-UDGothicR.ttc", 0),
    ("C:/Windows/Fonts/msgothic.ttc", 0),
    ("C:/Windows/Fonts/meiryo.ttc", 0),
    ("C:/Windows/Fonts/consola.ttf", 0),
]
_FONT = None


def get_font(size: int = FONT_SIZE):
    global _FONT
    if _FONT is not None:
        return _FONT
    for path, idx in FONTS:
        try:
            _FONT = ImageFont.truetype(path, size, index=idx)
            return _FONT
        except Exception:
            continue
    _FONT = ImageFont.load_default()
    return _FONT


# ゲーム画面に出ない絵文字を安全なグリフへ正規化
_REPL = {
    "💡": "*",
    "🎮": ">",
    "🎯": "+",
    "⛩": "_",
    "⛩️": "_",
    "🔥": "^",
    "☠": "+",
}


def sanitize_char(ch: str) -> str:
    if ch in _REPL:
        return _REPL[ch]
    o = ord(ch)
    if o > 0xFFFF:  # カラー絵文字などは表示不可
        return "?"
    return ch


def sanitize(s: str) -> str:
    return "".join(sanitize_char(c) for c in s)


# ---------------------------------------------------------------------------
# GameConsole: tcod.console.Console の最小互換実装
# ---------------------------------------------------------------------------
class GameConsole:
    def __init__(self, w: int = SCREEN_W, h: int = SCREEN_H):
        self.w = w
        self.h = h
        self.fg = [[TEXT_WHITE for _ in range(w)] for _ in range(h)]
        self.bg = [[BG for _ in range(w)] for _ in range(h)]
        self.ch = [[" " for _ in range(w)] for _ in range(h)]

    def clear(self, bg=BG):
        for y in range(self.h):
            for x in range(self.w):
                self.bg[y][x] = bg
                self.fg[y][x] = TEXT_WHITE
                self.ch[y][x] = " "

    def print(self, x, y, string, fg=TEXT_WHITE, bg=None):
        string = sanitize(string)
        for i, c in enumerate(string):
            cx = x + i
            if 0 <= cx < self.w and 0 <= y < self.h:
                self.ch[y][cx] = c
                self.fg[y][cx] = fg
                if bg is not None:
                    self.bg[y][cx] = bg

    def draw_rect(self, x, y, w, h, ch=0, fg=TEXT_WHITE, bg=None):
        ch = " " if ch == 0 else sanitize_char(ch)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    self.ch[yy][xx] = ch
                    self.fg[yy][xx] = fg
                    if bg is not None:
                        self.bg[yy][xx] = bg

    def draw_frame(self, x, y, w, h, title="", fg=PANEL_FG, bg=None):
        self.draw_rect(x, y, w, h, ch=" ", fg=fg, bg=bg)
        # 枠線
        for xx in range(x, x + w):
            if 0 <= xx < self.w:
                if y >= 0 and y < self.h:
                    self.ch[y][xx] = "─"
                    self.fg[y][xx] = fg
                if y + h - 1 >= 0 and y + h - 1 < self.h:
                    self.ch[y + h - 1][xx] = "─"
                    self.fg[y + h - 1][xx] = fg
        for yy in range(y, y + h):
            if 0 <= yy < self.h:
                if x >= 0 and x < self.w:
                    self.ch[yy][x] = "│"
                    self.fg[yy][x] = fg
                if x + w - 1 >= 0 and x + w - 1 < self.w:
                    self.ch[yy][x + w - 1] = "│"
                    self.fg[yy][x + w - 1] = fg
        corners = [(x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)]
        for (cx, cy) in corners:
            if 0 <= cx < self.w and 0 <= cy < self.h:
                self.ch[cy][cx] = "┼" if False else "+"
                self.fg[cy][cx] = fg
        # タイトル
        if title:
            self.print(x + 1, y, title, fg=fg)


# ---------------------------------------------------------------------------
# ラスタライザ: コンソール -> PIL Image
# ---------------------------------------------------------------------------
def rasterize(console: GameConsole) -> Image.Image:
    img = Image.new("RGB", (SCREEN_W * CELL_W, SCREEN_H * CELL_H), BG)
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_SIZE)
    for y in range(console.h):
        for x in range(console.w):
            bx = x * CELL_W
            by = y * CELL_H
            bg = console.bg[y][x]
            draw.rectangle([bx, by, bx + CELL_W - 1, by + CELL_H - 1], fill=bg)
            ch = console.ch[y][x]
            if ch != " ":
                fg = console.fg[y][x]
                draw.text(
                    (bx + 2, by + 1),
                    ch,
                    font=font,
                    fill=fg,
                )
    return img


# ---------------------------------------------------------------------------
# ライティング (ui_fx_systems.DynamicLighting.calculate_tile_lighting の簡易再現)
# ---------------------------------------------------------------------------
def compute_lighting(wx, wy, base, light_sources, player_pos, torch_r=12):
    """戻り値: (lit_color, intensity)"""
    # プレイヤー松明
    d = math.hypot(wx - player_pos[0], wy - player_pos[1])
    intensity = max(0.0, 1.0 - d / torch_r)
    for (lx, ly, lr, lcol) in light_sources:
        dd = math.hypot(wx - lx, wy - ly)
        intensity = max(intensity, max(0.0, 1.0 - dd / lr) * 0.9)
    intensity = min(1.0, intensity)
    f = 0.32 + 0.68 * intensity
    col = tuple(int(c * f) for c in base)
    # 松明付近の暖色ティント
    if d < 3:
        col = (
            min(255, int(col[0] * 1.05 + 12)),
            min(255, int(col[1] * 1.0 + 4)),
            int(col[2] * 0.95),
        )
    return col, intensity


# ---------------------------------------------------------------------------
# ダンジョン生成 (本物っぽい部屋+柱)
# ---------------------------------------------------------------------------
def make_room_map(altar=None, stairs=None):
    tiles = [["#" for _ in range(VIEW_W)] for _ in range(VIEW_H)]
    for y in range(1, VIEW_H - 1):
        for x in range(1, VIEW_W - 1):
            tiles[y][x] = "."
    # 内壁の柱 / 壁柱
    pillars = [
        (12, 8), (12, 14), (12, 22), (12, 29),
        (28, 10), (28, 18), (28, 27),
        (44, 8), (44, 22), (44, 30),
        (60, 12), (60, 26),
    ]
    for (px, py) in pillars:
        if 1 <= px < VIEW_W - 1 and 1 <= py < VIEW_H - 1:
            tiles[py][px] = "#"
    # 少し壁を追加して有機的に
    for y in range(4, VIEW_H - 4, 6):
        for x in range(18, 24):
            tiles[y][x] = "#"
    if stairs:
        tiles[stairs[1]][stairs[0]] = ">"
    if altar:
        tiles[altar[1]][altar[0]] = "_"
    return tiles


# ---------------------------------------------------------------------------
# ヘルパ: 演出描画
# ---------------------------------------------------------------------------
def gauge(current, maximum, length=8, fill="■", empty="□"):
    if maximum <= 0:
        return empty * length
    ratio = max(0.0, min(1.0, current / maximum))
    filled = int(ratio * length)
    return fill * filled + empty * (length - filled)


def draw_scan_box(cons, vx, vy, progress):
    """敵の深度解析演出 (セル上)"""
    bw, bh = 9, 7
    x0 = vx - bw // 2
    y0 = vy - bh // 2
    cons.draw_frame(x0, y0, bw, bh, fg=SCAN_COL)
    cons.print(x0, y0 - 1, f"SCAN {int(progress*100)}%", fg=SCAN_COL)
    # 走査線
    line_y = y0 + 1 + int(progress * (bh - 2))
    for xx in range(x0 + 1, x0 + bw - 1):
        if 0 <= xx < SCREEN_W and 0 <= line_y < SCREEN_H:
            cons.ch[line_y][xx] = "="
            cons.fg[line_y][xx] = SCAN_COL


def draw_devour_stream(cons, sx, sy, dx, dy, progress):
    """捕食核の吸収 (紫色パーティクル)"""
    n = 6
    for i in range(n):
        p = max(0.0, progress - i * 0.06)
        cx = sx + (dx - sx) * p
        cy = sy + (dy - sy) * p - math.sin(p * math.pi) * 3
        ix, iy = int(round(cx)), int(round(cy))
        if 0 <= ix < SCREEN_W and 0 <= iy < SCREEN_H:
            cons.ch[iy][ix] = "*"
            cons.fg[iy][ix] = DEVOUR_COL


def draw_window(cons, x, y, w, h, title, fg=PANEL_FG, body_bg=(14, 18, 28)):
    cons.draw_frame(x, y, w, h, title=f" {title} ", fg=fg, bg=body_bg)
    cons.draw_rect(x + 1, y + 1, w - 2, h - 2, ch=" ", bg=body_bg)


def draw_banner(cons, text, color=SUCCESS_COL, y=None):
    if y is None:
        y = UI_Y // 2
    w = min(SCREEN_W - 4, len(sanitize(text)) + 6)
    x = (SCREEN_W - w) // 2
    draw_window(cons, x, y, w, 3, "", fg=color, body_bg=(18, 14, 26))
    cons.print(x + 3, y + 1, text, fg=color)


# ---------------------------------------------------------------------------
# 汎用シーン描画 (render_system.py に準拠)
# ---------------------------------------------------------------------------
def render_scene(scene, return_console: bool = False):
    cons = GameConsole()
    p = scene["player"]
    cam_x = max(0, min(VIEW_W - VIEW_W, p["x"] - VIEW_W // 2))
    cam_y = max(0, min(VIEW_H - VIEW_H, p["y"] - VIEW_H // 2))

    tiles = scene["tiles"]
    visible = scene.get("visible")
    explored = scene.get("explored")
    light_sources = scene.get("light_sources", [])
    altar_pos = scene.get("altar_pos")
    stairs_pos = scene.get("stairs_pos")

    # 1. マップ
    for vy in range(VIEW_H):
        for vx in range(VIEW_W):
            wx = cam_x + vx
            wy = cam_y + vy
            if not (0 <= wx < VIEW_W and 0 <= wy < VIEW_H):
                continue
            vis = visible[wy][vx] if visible else True
            exp = explored[wy][vx] if explored else True
            t = tiles[wy][vx]
            if vis:
                if (altar_pos and (wx, wy) == altar_pos):
                    col, _ = compute_lighting(wx, wy, ALTAR, light_sources, p["pos"], scene.get("torch", 12))
                    cons.print(vx, vy, "_", fg=col)
                elif t == "#":
                    col, _ = compute_lighting(wx, wy, WALL_LIT, light_sources, p["pos"], scene.get("torch", 12))
                    cons.print(vx, vy, "#", fg=col)
                elif t == ">":
                    col, _ = compute_lighting(wx, wy, (100, 200, 255), light_sources, p["pos"], scene.get("torch", 12))
                    cons.print(vx, vy, ">", fg=col)
                else:
                    col, _ = compute_lighting(wx, wy, FLOOR_LIT, light_sources, p["pos"], scene.get("torch", 12))
                    cons.print(vx, vy, ".", fg=col)
            elif exp:
                if (altar_pos and (wx, wy) == altar_pos):
                    cons.print(vx, vy, "_", fg=(80, 70, 30))
                elif t == "#":
                    cons.print(vx, vy, "#", fg=WALL_DARK)
                else:
                    cons.print(vx, vy, ".", fg=FLOOR_DARK)

    # 2. 採取ノード
    for node in scene.get("nodes", []):
        nx, ny = node["x"], node["y"]
        vx, vy = nx - cam_x, ny - cam_y
        if 0 <= vx < VIEW_W and 0 <= vy < VIEW_H and (visible is None or visible[ny][nx]):
            base = node.get("color", (100, 255, 180))
            col, _ = compute_lighting(nx, ny, base, light_sources, p["pos"], scene.get("torch", 12))
            cons.print(vx, vy, node.get("ch", "%"), fg=col)

    # 3. アイテム
    for it in scene.get("items", []):
        ix, iy = it["x"], it["y"]
        vx, vy = ix - cam_x, iy - cam_y
        if 0 <= vx < VIEW_W and 0 <= vy < VIEW_H and (visible is None or visible[iy][ix]):
            base = it["color"]
            col, intensity = compute_lighting(ix, iy, base, light_sources, p["pos"], scene.get("torch", 12))
            if intensity < 0.25:
                col = (60, 65, 80)
            cons.print(vx, vy, it["ch"], fg=col)

    # 4. プレイヤー (本物のゲームでは entities に含まれる)
    player_ent = {
        "x": p["x"], "y": p["y"], "ch": "@", "color": TEXT_WHITE,
        "is_player": True, "hp": 1, "anim": 0,
    }
    all_entities = [player_ent] + list(scene.get("entities", []))

    # 4. エンティティ
    for e in all_entities:
        ex, ey = e["x"], e["y"]
        vx, vy = ex - cam_x, ey - cam_y
        if 0 <= vx < VIEW_W and 0 <= vy < VIEW_H and (visible is None or visible[ey][ex]) and e.get("hp", 1) > 0:
            base = e["color"]
            col, intensity = compute_lighting(ex, ey, base, light_sources, p["pos"], scene.get("torch", 12))
            if not e.get("is_player", False) and not e.get("is_pet", False) and intensity < 0.3:
                col = (70, 70, 90)
            bob = int(math.sin(e.get("anim", 0) + ex) * 0.6)
            cons.print(vx, vy + bob, e["ch"], fg=col)

    # 5. フローティングテキスト
    for ft in scene.get("floating_texts", []):
        fx, fy = ft["x"], ft["y"]
        vx = fx - cam_x + ft.get("dx", 0)
        vy = fy - cam_y + ft.get("dy", 0)
        if 0 <= vx < VIEW_W and 0 <= vy < SCREEN_H:
            cons.print(vx, vy, ft["text"], fg=ft["color"])

    # 6. オーバーレイ (演出用セル描画)
    for ov in scene.get("overlays", []):
        cons.print(ov["x"] - cam_x, ov["y"] - cam_y, ov["text"], fg=ov["color"])

    # 7. 下部UI (uirenderer.py 準拠)
    cons.draw_rect(0, UI_Y, SCREEN_W, SCREEN_H - UI_Y, ch=" ", bg=(10, 12, 16))
    cons.print(1, UI_Y, "━" * 78, fg=SEP_COL)

    hp_bar = gauge(p["hp"], p["max_hp"], length=8)
    mp_bar = gauge(p["mp"], p["max_mp"], length=6)
    pet = scene.get("pet", {})
    hunger = p.get("hunger", "満腹")
    cons.print(2, UI_Y + 1, "♥", fg=HP_COL)
    cons.print(4, UI_Y + 1, f"{p['name']} [{hunger}]", fg=NAME_COL)
    cons.print(22, UI_Y + 1, "♥", fg=HP_COL)
    cons.print(24, UI_Y + 1, f"HP:[{hp_bar}] {p['hp']}/{p['max_hp']}", fg=HP_COL)
    cons.print(46, UI_Y + 1, "♢", fg=MP_COL)
    cons.print(48, UI_Y + 1, f"MP:[{mp_bar}] {p['mp']}/{p['max_mp']}", fg=MP_COL)
    cons.print(66, UI_Y + 1, "★", fg=GOLD_COL)
    cons.print(68, UI_Y + 1, f"Lv.{p['level']} {p['gold']}G", fg=GOLD_COL)

    pet_hp_bar = gauge(pet.get("hp", 0), pet.get("max_hp", 1), length=6) if pet.get("hp", 0) > 0 else "DEAD"
    pet_str = f"HP:[{pet_hp_bar}] {pet.get('hp',0)}/{pet.get('max_hp',0)}" if pet.get("hp", 0) > 0 else "死亡"
    cons.print(2, UI_Y + 2, f"【仲間】シエル {pet_str}", fg=PET_COL)
    cons.print(34, UI_Y + 2, f"信仰:{p.get('god','ジュア')}({p.get('piety',80)})", fg=(200, 150, 255))
    cons.print(54, UI_Y + 2, f"{scene.get('time','Day1 08:00')} B{scene.get('dlevel',1)}F", fg=(170, 170, 170))

    tip = scene.get("tooltip", "🎮 [矢印]:移動 [Space]:便利行動 [l]:調査 [i]:荷物 [c]:能力 [Shift+T]:称号 [?]:ヘルプ")
    cons.print(2, UI_Y + 3, tip[:78], fg=(140, 180, 220))

    # 8. 凡例ボックス
    lx, ly = SCREEN_W - 21, 13
    cons.draw_frame(lx, ly, 20, 8, title=" [凡例] ", fg=PANEL_FG, bg=(12, 16, 24))
    cons.print(lx + 1, ly + 1, "@:自分  p:仲間", fg=(200, 240, 255))
    cons.print(lx + 1, ly + 2, "#:壁    .:床", fg=(180, 180, 180))
    cons.print(lx + 1, ly + 3, ">:階段下 <:階段上", fg=(255, 220, 100))
    cons.print(lx + 1, ly + 4, "_:祭壇  %:薬草", fg=(255, 215, 0))
    cons.print(lx + 1, ly + 5, "?:キノコ $:鉱石", fg=(100, 255, 180))
    cons.print(lx + 1, ly + 6, "x:敵(赤) !:薬品", fg=(255, 120, 120))

    # 9. トップ通知ボックス
    notif = scene.get("notification")
    if notif:
        nw = min(60, len(sanitize(notif["message"])) + len(sanitize(notif["title"])) + 8)
        nbx = max(2, (SCREEN_W - nw) // 2)
        nby = 2
        cons.draw_frame(nbx, nby, nw, 3, title=f" {notif['title']} ", fg=notif["color"], bg=(20, 25, 40))
        cons.print(nbx + 2, nby + 1, notif["message"][: nw - 4], fg=(255, 255, 255))

    # 10. シネマティックログ
    logs = scene.get("log", [])
    for i, lmsg in enumerate(logs[-4:]):
        text = lmsg["text"]
        col = lmsg["color"]
        tag = lmsg.get("tag", " ")
        line = f"{tag} {text}"[:74]
        cons.print(2, UI_Y + 7 + i, line, fg=col)

    if return_console:
        return cons
    return rasterize(cons)


# ---------------------------------------------------------------------------
# シーン基本状態
# ---------------------------------------------------------------------------
def base_scene(dlevel=1):
    altar = (10, 19)
    stairs = (74, 19)
    tiles = make_room_map(altar=altar, stairs=stairs)
    visible = [[True for _ in range(VIEW_W)] for _ in range(VIEW_H)]
    return {
        "tiles": tiles,
        "visible": visible,
        "altar_pos": altar,
        "stairs_pos": stairs,
        "torch": 12,
        "dlevel": dlevel,
        "time": "Day1 08:00",
        "player": {
            "name": "名無しの冒険者",
            "x": 40, "y": 19, "pos": (40, 19),
            "hp": 120, "max_hp": 120,
            "mp": 60, "max_mp": 60,
            "level": 12, "gold": 8200,
            "piety": 80, "god": "ジュア", "hunger": "満腹",
        },
        "pet": {"hp": 95, "max_hp": 95},
        "entities": [],
        "items": [],
        "nodes": [],
        "floating_texts": [],
        "overlays": [],
        "log": [],
        "tooltip": "🎮 [矢印]:移動 [Space]:便利行動 [l]:調査 [i]:荷物 [c]:能力 [Shift+T]:称号 [?]:ヘルプ",
        "notification": None,
    }


# ===========================================================================
# シーン1: 戦闘・深度解析・捕食・属性シナジー
# ===========================================================================
def scene_combat_devour():
    s = base_scene(3)
    enemy = {"x": 50, "y": 19, "ch": "D", "color": ENEMY_COL, "is_player": False, "hp": 320, "anim": 0, "name": "★深淵のドラゴン"}
    s["entities"] = [enemy]
    s["player"]["x"] = 38
    s["player"]["pos"] = (38, 19)
    s["items"] = [{"x": 44, "y": 17, "ch": "!", "color": (120, 200, 255), "category": "potion"}]
    s["log"] = [
        {"text": "★深淵のドラゴン が立ちふさがる！", "color": ENEMY_COL, "tag": " "},
        {"text": "『スキル喰い』モード: 構造解析を開始。", "color": SCAN_COL, "tag": " "},
        {"text": "弱化した隙に《喰らい》を狙え。", "color": MUTED, "tag": " "},
        {"text": "[?]で操作一覧 / [i]荷物を開く", "color": (180, 220, 255), "tag": " "},
    ]
    s["tooltip"] = "💡 敵に接近し [Space] で深度解析 → [F] で《喰らい》発動"

    frames = []
    total_hp = 320
    # Phase 1: スキャン (0-1.2s @15fps = 18F)
    for i in range(18):
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(enemy, anim=i * 0.3)]
        s2["overlays"] = [{"x": 50, "y": 19, "text": "", "color": SCAN_COL}]
        prog = i / 18.0
        # スキャンボックスは直接コンソール描画が必要なので overlay 経由では不可 -> render内で処理するため専用フラグ
        s2["_scan"] = (50, 19, prog)
        s2["floating_texts"] = [{"x": 50, "y": 15, "text": f"SCAN {int(prog*100)}%", "color": SCAN_COL}]
        s2["log"][1] = {"text": f"深度解析: 核残量 {int(100-prog*30)}% / 弱点=火", "color": SCAN_COL, "tag": " "}
        frames.append(build_with_scan(s2))
    # Phase 2: 攻撃 + シナジー爆発 (18F)
    for i in range(18):
        p = i / 18.0
        s2 = copy.deepcopy(s)
        ehp = max(20, int(total_hp - p * 240))
        s2["entities"] = [dict(enemy, hp=ehp, anim=i * 0.3)]
        s2["player"]["x"] = 38 + int(math.sin(p * math.pi) * 6)
        s2["player"]["pos"] = (s2["player"]["x"], 19)
        s2["_synergy"] = (50, 19, p)
        if i >= 4:
            s2["floating_texts"] = [{"x": 50, "y": 16 - int((i - 4) / 3), "text": "-280 CRIT!", "color": CRIT_COL}]
        s2["log"] = [
            {"text": "属性連鎖 [火x風] 熱爆発を発動！", "color": (255, 150, 40), "tag": " "},
            {"text": "★深淵のドラゴン に 280 のクリティカル！", "color": CRIT_COL, "tag": "★"},
            {"text": "敵の構造が崩壊、捕食可能状態に。", "color": (255, 200, 100), "tag": " "},
            {"text": "[F] で《喰らい》を実行せよ。", "color": DEVOUR_COL, "tag": " "},
        ]
        frames.append(build_with_synergy(s2))
    # Phase 3: 喰らい吸収 (22F)
    for i in range(22):
        p = i / 22.0
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(enemy, hp=0, anim=0)]
        s2["_devour"] = (50, 19, 38, 19, p)
        s2["player"]["name"] = "名無しの冒険者"
        s2["notification"] = {"title": "DEVOUR", "message": "スキル核を吸収中… Inferno Breath", "color": DEVOUR_COL}
        s2["log"] = [
            {"text": "《喰らい》発動: 敵のスキルを核ごと吸収。", "color": DEVOUR_COL, "tag": " "},
            {"text": "永続ステータス: 攻撃+18 / 火耐性+10", "color": (255, 200, 255), "tag": " "},
            {"text": "胃袋内シナジー: 雷x水 = 放電麻痺 解放", "color": (150, 200, 255), "tag": " "},
            {"text": "捕食完了まであと少し…", "color": MUTED, "tag": " "},
        ]
        frames.append(build_with_devour(s2))
    # Phase 4: 完了バナー (14F)
    for i in range(14):
        s2 = copy.deepcopy(s)
        s2["entities"] = []
        s2["items"].append({"x": 50, "y": 19, "ch": "★", "color": GOLD_COL, "category": "skill"})
        s2["player"]["hp"] = 138
        s2["player"]["max_hp"] = 138
        s2["notification"] = {"title": "ACQUIRED", "message": "Inferno Breath Lv.1 を獲得！", "color": SUCCESS_COL}
        if i < 4:
            s2["_flash"] = DEVOUR_COL
        s2["log"] = [
            {"text": "★捕食完了！ Inferno Breath を習得。", "color": SUCCESS_COL, "tag": "★"},
            {"text": "HP上限 +18 / 最大MP +12 上昇。", "color": HP_COL, "tag": " "},
            {"text": "新たなキメラ合成の素材が増えた。", "color": (200, 240, 255), "tag": " "},
            {"text": "[i]でスキル一覧を確認。", "color": (180, 220, 255), "tag": " "},
        ]
        frames.append(build_with_overlay(s2))
    return frames


# scan/synergy/devour 用の中間描画ヘルパ
def build_with_scan(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    sx, sy, prog = s2["_scan"]
    bx = sx * CELL_W
    by = sy * CELL_H
    bw, bh = 9 * CELL_W, 7 * CELL_H
    draw.rectangle([bx - bw // 2, by - bh // 2, bx + bw // 2, by + bh // 2],
                   outline=SCAN_COL, width=1)
    ly = by - bh // 2 + int(prog * bh)
    draw.line([(bx - bw // 2, ly), (bx + bw // 2, ly)], fill=SCAN_COL, width=2)
    return img


def build_with_synergy(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    tx, ty, p = s2["_synergy"]
    px = tx * CELL_W + CELL_W // 2
    py = ty * CELL_H + CELL_H // 2
    r = int(80 * p)
    if r > 0:
        a = max(0, int(200 * (1 - p)))
        draw.ellipse([px - r, py - r, px + r, py + r], outline=(255, 120, 0), width=4)
        draw.ellipse([px - int(r * 0.6), py - int(r * 0.6), px + int(r * 0.6), py + int(r * 0.6)],
                     fill=(255, 60, 0, a))
    return img


def build_with_devour(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    sx, sy, dx, dy, p = s2["_devour"]
    x0 = sx * CELL_W + CELL_W // 2
    y0 = sy * CELL_H + CELL_H // 2
    x1 = dx * CELL_W + CELL_W // 2
    y1 = dy * CELL_H + CELL_H // 2
    n = 6
    for i in range(n):
        pp = max(0.0, p - i * 0.06)
        cx = x0 + (x1 - x0) * pp
        cy = y0 + (y1 - y0) * pp - math.sin(pp * math.pi) * 40
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=DEVOUR_COL, outline=(255, 255, 255))
    return img


def build_with_overlay(s2):
    img = render_scene(s2)
    if s2.get("_flash"):
        col = s2["_flash"]
        overlay = Image.new("RGB", img.size, col)
        img = Image.blend(img, overlay, 0.35)
    return img


# ===========================================================================
# シーン2: キメラ合成・闇市場・監査官レイド
# ===========================================================================
def scene_synthesis_economy():
    s = base_scene(5)
    s["player"]["x"] = 40
    s["player"]["pos"] = (40, 19)
    s["items"] = [
        {"x": 36, "y": 19, "ch": "╿", "color": (0, 200, 255), "category": "skill"},
        {"x": 44, "y": 19, "ch": "╿", "color": (255, 120, 50), "category": "skill"},
    ]
    s["log"] = [
        {"text": "錬金炉を起動。2つのスキルをセット。", "color": (200, 240, 255), "tag": " "},
        {"text": "Flame Strike + Gale Slash -> ?", "color": (255, 220, 100), "tag": " "},
        {"text": "禁忌のキメラ合成を実行可能。", "color": (255, 150, 40), "tag": " "},
        {"text": "[c]能力 / [Shift+S]ツリー", "color": (180, 220, 255), "tag": " "},
    ]
    s["tooltip"] = "💡 [Space] で炉に投入 → キメラ合成を実行"
    frames = []
    # Phase 1: セット (16F)
    for i in range(16):
        s2 = copy.deepcopy(s)
        s2["_alchemy"] = (40, 19, 0.0, i / 16.0)
        frames.append(build_with_alchemy(s2))
    # Phase 2: 回転魔法陣 + 吸い込み (18F)
    for i in range(18):
        p = i / 18.0
        s2 = copy.deepcopy(s)
        s2["_alchemy"] = (40, 19, p, 1.0)
        s2["notification"] = {"title": "TRANSMUTE", "message": "元素を融合中…", "color": (100, 200, 255)}
        s2["log"][1] = {"text": f"魔法陣回転 {int(p*100)}% - 共振上昇", "color": (150, 180, 255), "tag": " "}
        frames.append(build_with_alchemy(s2))
    # Phase 3: 完成バナー (14F)
    for i in range(14):
        s2 = copy.deepcopy(s)
        s2["_alchemy_done"] = (40, 19)
        s2["notification"] = {"title": "CHIMERA", "message": "Inferno Storm Slash 誕生！", "color": SUCCESS_COL}
        s2["items"] = [{"x": 40, "y": 19, "ch": "★", "color": GOLD_COL, "category": "skill"}]
        s2["log"] = [
            {"text": "★キメラ合成成功: Inferno Storm Slash", "color": SUCCESS_COL, "tag": "★"},
            {"text": "認可外スキル (違法等級 B) を生成。", "color": (255, 120, 120), "tag": " "},
            {"text": "闇市場で高値売却か、自ら運用か。", "color": (255, 220, 100), "tag": " "},
            {"text": "[m]で闇市場を開く", "color": (180, 220, 255), "tag": " "},
        ]
        frames.append(build_with_alchemy(s2))
    # Phase 4: 闇市場密売 (16F)
    for i in range(16):
        p = i / 16.0
        s2 = copy.deepcopy(s)
        s2["_market"] = (40, 19, p)
        s2["player"]["gold"] = 8200 + int(p * 3600)
        s2["notification"] = {"title": "MARKET", "message": f"違法スキル売却 +{int(p*3600)}G", "color": (100, 255, 120)}
        s2["log"] = [
            {"text": "☠ UNDERGROUND MARKET: 密売成立", "color": (255, 120, 150), "tag": " "},
            {"text": f"Contraband SOLD: +{int(p*3600)} G", "color": (255, 235, 80), "tag": " "},
            {"text": "監査レベルが上昇中…", "color": (255, 120, 120), "tag": " "},
            {"text": "早期撤退を推奨。", "color": MUTED, "tag": " "},
        ]
        frames.append(build_with_market(s2))
    # Phase 5: 監査官レイド (16F)
    for i in range(16):
        s2 = copy.deepcopy(s)
        s2["_raid"] = i / 16.0
        s2["notification"] = {"title": "RAID", "message": "INQUISITION RAID DETECTED!", "color": WARN_COL}
        s2["log"] = [
            {"text": "⚠ 異端審問官レイド発動！", "color": WARN_COL, "tag": "!"},
            {"text": "Audit Level Critical: 没収寸前", "color": (255, 200, 200), "tag": "!"},
            {"text": "所持スキルを隠匿 / 撤退せよ。", "color": (255, 180, 180), "tag": " "},
            {"text": "[>]で階段へ急行", "color": (180, 220, 255), "tag": " "},
        ]
        frames.append(build_with_raid(s2))
    return frames


def build_with_alchemy(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    info = s2.get("_alchemy")
    if info:
        cx, cy, prog, setp = info
        px = cx * CELL_W + CELL_W // 2
        py = cy * CELL_H + CELL_H // 2
        # 魔法陣 (回転)
        if prog > 0:
            import math as _m
            for k in range(6):
                a = prog * 6.28 + k * (_m.pi / 3)
                ex = px + int(_m.cos(a) * 36)
                ey = py + int(_m.sin(a) * 36)
                draw.line([(px, py), (ex, ey)], fill=(120, 180, 255), width=1)
            draw.ellipse([px - 40, py - 40, px + 40, py + 40], outline=(150, 100, 255), width=1)
        # 炉
        draw.rectangle([px - 14, py - 12, px + 14, py + 14], fill=(40, 25, 55), outline=(220, 120, 255))
    if s2.get("_alchemy_done"):
        px = cx0 = s2["_alchemy_done"][0] * CELL_W + CELL_W // 2
        py = s2["_alchemy_done"][1] * CELL_H + CELL_H // 2
        draw.rectangle([px - 14, py - 12, px + 14, py + 14], fill=(60, 30, 80), outline=(255, 215, 0), width=2)
    return img


def build_with_market(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    cx, cy, p = s2["_market"]
    px = cx * CELL_W + CELL_W // 2
    py = cy * CELL_H + CELL_H // 2
    # コイン散乱
    for idx, (ox, oy) in enumerate([(-40, -30), (40, -36), (-60, 10), (60, 6), (0, -54), (-24, 34), (30, 40)]):
        pp = min(1.0, p * 1.4 + idx * 0.04)
        fx = px + int(ox * pp)
        fy = py + int(oy * pp - _sin(pp * math.pi) * 24)
        draw.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill=(255, 215, 0))
    return img


def build_with_raid(s2):
    img = render_scene(s2)
    p = s2["_raid"]
    a = int(110 * abs(math.sin(p * math.pi * 3)))
    if a > 0:
        overlay = Image.new("RGB", img.size, (180, 0, 0))
        img = Image.blend(img, overlay, a / 255.0 * 0.6)
    return img


def _sin(v):
    return math.sin(v)


# ===========================================================================
# シーン3: ROOTハック・精神侵食・輪廻転生
# ===========================================================================
def scene_meta_reincarnation():
    s = base_scene(7)
    s["player"]["x"] = 40
    s["player"]["pos"] = (40, 19)
    s["log"] = [
        {"text": "世界法則へのアクセス経路を探索中…", "color": SCAN_COL, "tag": " "},
        {"text": "ROOT権限昇格を試行。", "color": (0, 255, 180), "tag": " "},
        {"text": "生命力で世界の定数を書き換え可能。", "color": (200, 160, 255), "tag": " "},
        {"text": "[r]でROOTハック実行", "color": (180, 220, 255), "tag": " "},
    ]
    s["tooltip"] = "💡 [r] ROOTハック: ダメージ倍率 1.0x -> 2.5x (代償: 最大HP-25%)"
    frames = []
    # Phase 1: ターミナル (18F)
    for i in range(18):
        s2 = copy.deepcopy(s)
        s2["_term"] = i / 18.0
        frames.append(build_with_term(s2))
    # Phase 2: 法則書き換えUI (16F)
    for i in range(16):
        s2 = copy.deepcopy(s)
        s2["_override"] = True
        s2["notification"] = {"title": "ROOT OVERRIDE", "message": "GLOBAL DMG x2.5 / MAXHP -25%", "color": (0, 255, 200)}
        s2["log"] = [
            {"text": "★SYSTEM LAW OVERRIDE APPLIED", "color": (0, 255, 200), "tag": "★"},
            {"text": "GLOBAL DAMAGE MULTIPLIER: 1.0x -> 2.5x", "color": (0, 255, 160), "tag": " "},
            {"text": "COST: MAX HP -25% (Sanity Erosion +25%)", "color": (255, 100, 100), "tag": " "},
            {"text": "世界の物理定数が書き換わった。", "color": (200, 160, 255), "tag": " "},
        ]
        frames.append(build_with_override(s2))
    # Phase 3: 侵食 (16F)
    for i in range(16):
        p = i / 16.0
        s2 = copy.deepcopy(s)
        s2["_override"] = True
        s2["_erosion"] = p
        cur_max = int(120 - p * 30)
        s2["player"]["max_hp"] = cur_max
        s2["player"]["hp"] = min(s2["player"]["hp"], cur_max)
        s2["notification"] = {"title": "CORRUPTED", "message": f"Sanity Erosion +{int(p*25)}%", "color": (255, 90, 90)}
        frames.append(build_with_override(s2))
    # Phase 4: 世界崩壊 (16F)
    for i in range(16):
        s2 = copy.deepcopy(s)
        s2["_collapse"] = i / 16.0
        s2["log"] = [
            {"text": "世界の根幹が崩壊…輪廻の儀式へ。", "color": (200, 150, 255), "tag": " "},
            {"text": "前世の功績をカルマに変換中。", "color": (255, 215, 0), "tag": " "},
            {"text": "遺伝スキルを継承して再誕。", "color": (100, 255, 200), "tag": " "},
            {"text": "[Enter]で NG+ 開始", "color": (180, 220, 255), "tag": " "},
        ]
        frames.append(build_with_collapse(s2))
    # Phase 5: カルマ清算 + 新生 (18F)
    for i in range(18):
        p = i / 18.0
        s2 = copy.deepcopy(s)
        s2["_reborn"] = p
        frames.append(build_with_reborn(s2))
    return frames


def build_with_term(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    logs = [
        "[*] INITIATING ROOT PRIVILEGE ESCALATION...",
        "[*] CONNECTING TO SYSTEM CORE 0x7FFF...",
        "[*] BYPASSING SANCTUARY FIREWALL [OK]",
        "[*] INJECTING KERNEL OVERRIDE...",
        "[+] ROOT ACCESS GRANTED.",
    ]
    n = int(s2["_term"] * (len(logs) + 1))
    y = 6 * CELL_H
    f = get_font(14)
    for k in range(min(len(logs), n)):
        draw.text((8, y + k * 16), logs[k], font=f, fill=(0, 255, 160))
    # 走査線
    for yy in range(0, img.height, 4):
        draw.line([(0, yy), (img.width, yy)], fill=(0, 0, 0), width=1)
    return img


def build_with_override(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    # 法則書き換えウィンドウ
    wx, wy, ww, wh = 18 * CELL_W, 16 * CELL_H, 44 * CELL_W, 12 * CELL_H
    draw.rectangle([wx, wy, wx + ww, wy + wh], fill=(8, 18, 26), outline=(0, 255, 200), width=2)
    draw.rectangle([wx, wy, wx + ww, wy + 3 * CELL_H], fill=(0, 100, 120))
    f = get_font(14)
    draw.text((wx + 10, wy + 8), "[!] SYSTEM LAW OVERRIDE APPLIED", font=f, fill=(255, 255, 255))
    draw.text((wx + 14, wy + 4 * CELL_H), "GLOBAL DAMAGE MULTIPLIER: 1.0x -> 2.5x", font=f, fill=(0, 255, 200))
    draw.text((wx + 14, wy + 6 * CELL_H), "COST: MAX HP -25% (Sanity Erosion)", font=f, fill=(255, 100, 100))
    # 閃き
    draw.text((wx + ww - 30, wy + 8), "✦", font=f, fill=(255, 230, 100))
    # グリッチ
    if random.random() < 0.4:
        gy = random.randint(10, img.height - 30)
        gh = random.randint(4, 18)
        sl = img.crop((0, gy, img.width, gy + gh))
        img.paste(sl, (random.randint(-12, 12), gy))
    return img


def build_with_collapse(s2):
    img = render_scene(s2)
    p = s2["_collapse"]
    cx, cy = img.width // 2, img.height // 2
    r = int(math.hypot(cx, cy) * 1.2 * p)
    if r > 0:
        draw = ImageDraw.Draw(img)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(5, 5, 10), outline=(120, 50, 200), width=3)
        draw.text((cx - 20, cy - 10), "✧", font=get_font(28), fill=(200, 150, 255))
    return img


def build_with_reborn(s2):
    p = s2["_reborn"]
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    # ブラックアウトからフェードインする新生ログ
    logs = [
        "=== CYCLE SETTLEMENT ===",
        "SKILLS DEVOUR: 42 (+840 KARMA)",
        "ROOT OVERRIDES: 3 (+600 KARMA)",
        "HEREDITARY GENE: [Void Core Lv.2]",
        "-> Cycle #2 REBORN",
    ]
    draw.rectangle([0, 0, img.width, img.height], fill=(5, 5, 8))
    f = get_font(15)
    n = int(p * (len(logs) + 1))
    for k in range(min(len(logs), n)):
        col = (255, 215, 0) if k == 0 else (200, 240, 255)
        draw.text((img.width // 2 - 150, 60 + k * 30), logs[k], font=f, fill=col)
    if p > 0.6:
        a = int(255 * (1 - (p - 0.6) / 0.4))
        if a > 0:
            overlay = Image.new("RGB", img.size, (0, 0, 0))
            img = Image.blend(img, overlay, a / 255.0)
            # 新生バナーを上書き
            draw = ImageDraw.Draw(img)
            draw.rectangle([18 * CELL_W, 6 * CELL_H, 62 * CELL_W, 9 * CELL_H], fill=(20, 40, 30), outline=(0, 255, 180), width=2)
            draw.text((20 * CELL_W, 7 * CELL_H), "NEW INCARNATION INITIATED", font=get_font(14), fill=(100, 255, 200))
    return img


# ===========================================================================
# シーン4: Husk従属者タレット
# ===========================================================================
def scene_husk_servant():
    s = base_scene(4)
    s["player"]["x"] = 36
    s["player"]["pos"] = (36, 19)
    husk = {"x": 50, "y": 19, "ch": "h", "color": (120, 120, 140), "is_player": False, "hp": 1, "anim": 0, "name": "Husk"}
    s["entities"] = [husk]
    s["log"] = [
        {"text": "スキルを抜かれた抜け殻(Husk)を発見。", "color": (200, 200, 220), "tag": " "},
        {"text": "魔力回路を移植し使い捨てタレットに。", "color": (0, 255, 200), "tag": " "},
        {"text": "[Space]で回路移植を実行。", "color": (180, 220, 255), "tag": " "},
        {"text": "寿命到達で自壊、周囲を巻き込む。", "color": (255, 180, 180), "tag": " "},
    ]
    s["tooltip"] = "💡 [Space] 魔力回路移植 → 自律迎撃タレット化"
    frames = []
    # Phase 1: 対峙 (14F)
    for i in range(14):
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(husk, anim=i * 0.2)]
        frames.append(render_scene(s2))
    # Phase 2: 移植ビーム (18F)
    for i in range(18):
        p = i / 18.0
        s2 = copy.deepcopy(s)
        s2["_implant"] = (36, 19, 50, 19, p)
        s2["notification"] = {"title": "IMPLANT", "message": "Skill Circuit 移植中…", "color": (0, 255, 200)}
        frames.append(build_with_implant(s2))
    # Phase 3: 覚醒 (14F)
    for i in range(14):
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(husk, ch="H", color=(255, 120, 120), anim=i * 0.2)]
        s2["_awake"] = (50, 19)
        s2["_lifespan"] = 3
        s2["notification"] = {"title": "SERVANT", "message": "Turret Servant Online", "color": (255, 100, 100)}
        s2["log"][0] = {"text": "★Husk 覚醒: 忠誠の赤眼が灯る。", "color": (255, 120, 120), "tag": "★"}
        frames.append(build_with_awake(s2))
    # Phase 4: 自律射撃 (18F)
    for i in range(18):
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(husk, ch="H", color=(255, 120, 120))]
        s2["_fire"] = (50, 19, 10 + (i % 9), 19, (i % 9) / 9.0)
        s2["_lifespan"] = 2 if i < 9 else 1
        frames.append(build_with_fire(s2))
    # Phase 5: 過負荷 (12F)
    for i in range(12):
        s2 = copy.deepcopy(s)
        s2["entities"] = [dict(husk, ch="H", color=(255, 120, 120))]
        s2["_overload"] = True
        s2["_lifespan"] = 0
        s2["notification"] = {"title": "OVERLOAD", "message": "Lifespan Critical!", "color": (255, 90, 90)}
        frames.append(build_with_overload(s2))
    # Phase 6: 自壊 (16F)
    for i in range(16):
        p = i / 16.0
        s2 = copy.deepcopy(s)
        s2["_destroy"] = (50, 19, p)
        if i == 0:
            s2["entities"] = []
        s2["log"] = [
            {"text": "★SERVANT DESTROYED: 過負荷自壊", "color": (255, 120, 120), "tag": "★"},
            {"text": "周囲の敵を巻き込み爆散。", "color": (255, 180, 180), "tag": " "},
            {"text": "新たなHuskを狩って再錬成。", "color": (200, 240, 255), "tag": " "},
            {"text": "[Space]で次のHuskを確保", "color": (180, 220, 255), "tag": " "},
        ]
        frames.append(build_with_destroy(s2))
    return frames


def build_with_implant(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    hx, hy, sx, sy, p = s2["_implant"]
    x0 = hx * CELL_W + CELL_W // 2
    y0 = hy * CELL_H + CELL_H // 2
    x1 = sx * CELL_W + CELL_W // 2
    y1 = sy * CELL_H + CELL_H // 2
    cx = x0 + (x1 - x0) * p
    cy = y0 + (y1 - y0) * p
    draw.line([(x0, y0), (cx, cy)], fill=(0, 255, 200), width=3)
    draw.line([(x0, y0), (cx, cy)], fill=(255, 255, 255), width=1)
    return img


def build_with_awake(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    x, y = s2["_awake"]
    px = x * CELL_W + CELL_W // 2
    py = y * CELL_H + CELL_H // 2
    draw.ellipse([px - 14, py - 14, px - 6, py - 6], fill=(255, 30, 30))
    draw.ellipse([px + 6, py - 14, px + 14, py - 6], fill=(255, 30, 30))
    draw.text((px - 10, py - 40), "♥", font=get_font(18), fill=(255, 120, 180))
    if s2.get("_lifespan") is not None:
        draw.text((px - 30, py - 56), f"LIFESPAN:{s2['_lifespan']}T", font=get_font(11), fill=(100, 200, 255))
    return img


def build_with_fire(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    sx, sy, tx, ty, p = s2["_fire"]
    x0 = sx * CELL_W + CELL_W // 2
    y0 = sy * CELL_H + CELL_H // 2
    x1 = int(x0 + (tx * CELL_W + CELL_W // 2 - x0) * p)
    y1 = int(y0 + (ty * CELL_H + CELL_H // 2 - y0) * p)
    draw.ellipse([x1 - 6, y1 - 6, x1 + 6, y1 + 6], fill=(255, 120, 50), outline=(255, 255, 200), width=2)
    px = sx * CELL_W + CELL_W // 2
    py = sy * CELL_H + CELL_H // 2
    draw.text((px - 30, py - 20), " anger", font=get_font(16), fill=(255, 120, 120))
    draw.text((px - 30, py - 56), f"LIFESPAN:{s2['_lifespan']}T", font=get_font(11), fill=(50, 180, 220))
    return img


def build_with_overload(s2):
    img = render_scene(s2)
    if s2.get("_overload"):
        # シェイク
        import random as _r
        ox = _r.randint(-4, 4)
        oy = _r.randint(-3, 3)
        img = ImageChops.offset(img, ox, oy)
    draw = ImageDraw.Draw(img)
    if s2.get("_lifespan") is not None:
        draw.text((40 * CELL_W, 14 * CELL_H), f"LIFESPAN:{s2['_lifespan']}T", font=get_font(11), fill=(255, 90, 90))
        draw.text((40 * CELL_W, 16 * CELL_H), "! ALERT", font=get_font(16), fill=(255, 90, 90))
    return img


def build_with_destroy(s2):
    img = render_scene(s2)
    draw = ImageDraw.Draw(img)
    x, y, p = s2["_destroy"]
    px = x * CELL_W + CELL_W // 2
    py = y * CELL_H + CELL_H // 2
    for idx in range(30):
        a = (idx / 30) * math.pi * 2
        d = int(8 + p * 70) + (idx % 5) * 4
        dx = px + int(math.cos(a) * d)
        dy = py + int(math.sin(a) * d + p * 20)
        col = (120, 100, 140) if idx % 2 == 0 else (200, 50, 50)
        draw.rectangle([dx - 2, dy - 2, dx + 2, dy + 2], fill=col)
    draw.text((px - 40, py - 50), " faceSad", font=get_font(18), fill=(180, 180, 200))
    return img


from PIL import ImageChops


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------
def save_gif(frames, path: Path, fps=15):
    path.parent.mkdir(parents=True, exist_ok=True)
    # グローバルパレットを作って全フレームで共有 -> 容量削減 + 色の一貫性
    w, h = frames[0].size
    stride = max(1, len(frames) // 24)
    sample = Image.new("RGB", (w, h * (len(frames[::stride]) or 1)))
    for i, f in enumerate(frames[::stride]):
        sample.paste(f.convert("RGB"), (0, i * h))
    pal_img = sample.convert("P", palette=Image.ADAPTIVE, colors=255)
    palette = pal_img.getpalette()
    base_pal = Image.new("P", (1, 1))
    base_pal.putpalette(palette)
    pal_frames = [f.convert("RGB").quantize(palette=base_pal, dither=Image.NONE) for f in frames]
    pal_frames[0].save(
        path,
        save_all=True,
        append_images=pal_frames[1:],
        duration=int(1000 / fps),
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"Saved {path} ({len(frames)} frames, ~{len(frames)/fps:.1f}s)")


def main():
    out = Path("assets")
    fps = 15
    save_gif(scene_combat_devour(), out / "demo_combat_devour.gif", fps=fps)
    save_gif(scene_synthesis_economy(), out / "demo_synthesis_economy.gif", fps=fps)
    save_gif(scene_meta_reincarnation(), out / "demo_meta_reincarnation.gif", fps=fps)
    save_gif(scene_husk_servant(), out / "demo_husk_servant.gif", fps=fps)


if __name__ == "__main__":
    main()
