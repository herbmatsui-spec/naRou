"""
Roguelike-Authentic GIF Generator for World A: Skill Eater
Generates GIFs that look like actual in-game screenshots:
  - ASCII/tile dungeon map with walls (#), floors (.), entities (@, B, etc.)
  - HP/MP bars, minimap, status HUD
  - Combat log at the bottom
  - Animated combat sequences, scan overlays, devour effects
"""
from __future__ import annotations
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# === Constants ===
W, H = 760, 480
CELL = 16  # tile cell size
MAP_COLS, MAP_ROWS = 30, 18  # visible map area
MAP_X, MAP_Y = 8, 50  # map top-left pixel
HUD_Y = 0
LOG_Y = MAP_Y + MAP_ROWS * CELL + 4
FPS = 8

# Elona-like color palette
C_BG       = (10, 10, 16)
C_WALL_D   = (35, 35, 45)
C_WALL_L   = (120, 100, 75)
C_FLOOR_D  = (18, 18, 25)
C_FLOOR_L  = (60, 55, 45)
C_PLAYER   = (80, 255, 120)
C_ENEMY    = (255, 80, 80)
C_ENEMY2   = (255, 160, 60)
C_PET      = (255, 180, 220)
C_HUSK     = (100, 100, 100)
C_NPC      = (100, 200, 255)
C_ITEM     = (255, 215, 0)
C_STAIRS   = (200, 200, 255)
C_WATER    = (40, 90, 180)
C_HUD_BG   = (15, 18, 28)
C_HP_BAR   = (80, 220, 100)
C_MP_BAR   = (80, 160, 255)
C_TOX_BAR  = (200, 60, 200)
C_SCAN_OV  = (0, 180, 255, 60)
C_DEVOUR   = (255, 40, 80)
C_SYNTH    = (180, 100, 255)
C_LOG_BG   = (8, 10, 16)


def get_font(sz):
    for name in ["Consolas", "msgothic.ttc", "Courier New", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, sz)
        except:
            pass
    return ImageFont.load_default()

def get_jp_font(sz):
    for name in ["msgothic.ttc", "meiryo.ttc", "yumindb.ttf"]:
        try:
            return ImageFont.truetype(name, sz)
        except:
            pass
    return get_font(sz)

font_tile = get_font(14)
font_hud  = get_jp_font(12)
font_log  = get_jp_font(11)
font_big  = get_jp_font(16)
font_huge = get_jp_font(22)

# === Dungeon Map Data (pre-designed rooms & corridors) ===
DUNGEON_SLUM = [
    "##############################",
    "#....#.........#.............#",
    "#....#.........#......$......#",
    "#....+.........+.............#",
    "#....#.........#.............#",
    "####+#####+#####..#####+######",
    "#........#.....#..#..........#",
    "#........#.....#..#..........#",
    "#........+.....+..+..........#",
    "#........#.....#..#..........#",
    "#........#.....#..#..........#",
    "####+#####..####..#####+######",
    "#..........~~~~~..#..........#",
    "#..........~~~~~..#....>.....#",
    "#..........~~~~~..+..........#",
    "#.................#..........#",
    "#.................#..........#",
    "##############################",
]

DUNGEON_TOWER = [
    "##############################",
    "#<...........##..............#",
    "#............##..............#",
    "#....####....##....####......#",
    "#....#..#....##....#..#......#",
    "#....#..#....++....#..#......#",
    "#....####....##....####......#",
    "#............##..............#",
    "######++####.##.####++#######",
    "#............##..............#",
    "#....####....##....####......#",
    "#....#..#....##....#..#......#",
    "#....#..#....++....#..#......#",
    "#....####....##....####......#",
    "#............##..............#",
    "#............##...........$..#",
    "#............##..............#",
    "##############################",
]

# === Entity definitions per scene ===
class Ent:
    def __init__(self, x, y, ch, color, name, hp=None, max_hp=None):
        self.x, self.y, self.ch, self.color, self.name = x, y, ch, color, name
        self.hp = hp or 0
        self.max_hp = max_hp or hp or 0

# === Drawing Helpers ===
def draw_dungeon(draw, dmap, cam_x=0, cam_y=0, highlights=None):
    """Draw ASCII dungeon map with proper roguelike tile colors."""
    highlights = highlights or {}
    for ry, row in enumerate(dmap):
        for rx, ch in enumerate(row):
            px = MAP_X + rx * CELL
            py = MAP_Y + ry * CELL
            if ch == '#':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_WALL_L)
                draw.text((px+3, py+1), '#', fill=(80, 70, 55), font=font_tile)
            elif ch == '~':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_WATER)
                draw.text((px+3, py+1), '~', fill=(100, 170, 255), font=font_tile)
            elif ch == '>':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_FLOOR_L)
                draw.text((px+3, py+1), '>', fill=C_STAIRS, font=font_tile)
            elif ch == '<':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_FLOOR_L)
                draw.text((px+3, py+1), '<', fill=C_STAIRS, font=font_tile)
            elif ch == '+':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=(90, 70, 40))
                draw.text((px+3, py+1), '+', fill=(180, 140, 80), font=font_tile)
            elif ch == '$':
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_FLOOR_L)
                draw.text((px+3, py+1), '$', fill=C_ITEM, font=font_tile)
            else:
                draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_FLOOR_L)
                if (rx, ry) in highlights:
                    draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=highlights[(rx,ry)])

def draw_entity(draw, ent, pulse=0):
    """Draw a single entity on the map."""
    px = MAP_X + ent.x * CELL
    py = MAP_Y + ent.y * CELL
    draw.rectangle([px, py, px+CELL-1, py+CELL-1], fill=C_FLOOR_L)
    c = ent.color
    if pulse:
        c = tuple(min(255, v + pulse) for v in c)
    draw.text((px+3, py+1), ent.ch, fill=c, font=font_tile)

def draw_hp_bar_above(draw, ent, ratio, color=C_HP_BAR, width=14):
    """Draw a small HP bar above an entity."""
    px = MAP_X + ent.x * CELL + 1
    py = MAP_Y + ent.y * CELL - 4
    draw.rectangle([px, py, px+width, py+2], fill=(40, 40, 40))
    draw.rectangle([px, py, px+int(width*ratio), py+2], fill=color)

def draw_hud(draw, player_name, hp, max_hp, mp, max_mp, level, floor_name,
             toxicity=0, skills=None, gold=0):
    """Draw top HUD bar."""
    draw.rectangle([0, 0, W, MAP_Y-2], fill=C_HUD_BG)
    # Player info
    draw.text((10, 4), f"◆ {player_name}", fill=C_PLAYER, font=font_hud)
    draw.text((10, 22), f"Lv.{level}", fill=(200, 200, 200), font=font_hud)
    # HP bar
    draw.text((80, 4), "HP", fill=(200, 200, 200), font=font_hud)
    draw.rectangle([100, 6, 240, 16], fill=(40, 40, 50))
    draw.rectangle([100, 6, 100+int(140*(hp/max_hp)), 16], fill=C_HP_BAR)
    draw.text((245, 4), f"{hp}/{max_hp}", fill=(200, 200, 200), font=font_hud)
    # MP bar
    draw.text((80, 22), "MP", fill=(200, 200, 200), font=font_hud)
    draw.rectangle([100, 24, 240, 34], fill=(40, 40, 50))
    draw.rectangle([100, 24, 100+int(140*(mp/max(1,max_hp))), 34], fill=C_MP_BAR)
    draw.text((245, 22), f"{mp}/{max_hp//2}", fill=(200, 200, 200), font=font_hud)
    # Toxicity
    if toxicity > 0:
        draw.text((320, 4), "毒性", fill=C_TOX_BAR, font=font_hud)
        draw.rectangle([350, 6, 440, 16], fill=(40, 40, 50))
        draw.rectangle([350, 6, 350+int(90*(toxicity/100)), 16], fill=C_TOX_BAR)
        draw.text((445, 4), f"{toxicity}%", fill=C_TOX_BAR, font=font_hud)
    # Floor
    draw.text((520, 4), f"📍 {floor_name}", fill=(180, 190, 210), font=font_hud)
    # Gold
    draw.text((520, 22), f"💰 {gold} アルド", fill=C_ITEM, font=font_hud)
    # Skills count
    if skills:
        draw.text((320, 22), f"📦 スキル: {skills}", fill=(150, 200, 255), font=font_hud)
    # Separator
    draw.line([(0, MAP_Y-2), (W, MAP_Y-2)], fill=(50, 60, 80), width=1)

def draw_log(draw, lines, highlight_last=False):
    """Draw bottom message log panel."""
    draw.rectangle([0, LOG_Y, W, H], fill=C_LOG_BG)
    draw.line([(0, LOG_Y), (W, LOG_Y)], fill=(50, 60, 80), width=1)
    draw.text((10, LOG_Y+2), "📜 メッセージログ", fill=(120, 130, 150), font=font_log)
    for i, (text, color) in enumerate(lines[-5:]):
        y = LOG_Y + 18 + i * 16
        draw.text((15, y), f"❯ {text}", fill=color, font=font_log)

def draw_minimap(draw, dmap, player_x, player_y, x_off=660, y_off=52):
    """Draw a tiny minimap in the corner."""
    draw.rectangle([x_off-2, y_off-2, x_off+62, y_off+38], fill=(15,18,28), outline=(50,60,80))
    for ry, row in enumerate(dmap):
        for rx, ch in enumerate(row):
            px = x_off + rx * 2
            py = y_off + ry * 2
            if ch == '#':
                draw.rectangle([px, py, px+1, py+1], fill=(80, 70, 55))
            elif ch == '~':
                draw.rectangle([px, py, px+1, py+1], fill=(40, 90, 180))
    # Player blip
    draw.rectangle([x_off+player_x*2, y_off+player_y*2,
                     x_off+player_x*2+2, y_off+player_y*2+2], fill=C_PLAYER)

def draw_scan_overlay(draw, ent, info_lines):
    """Draw scan analysis popup near an entity."""
    px = MAP_X + ent.x * CELL + CELL + 4
    py = MAP_Y + ent.y * CELL - 10
    bw = 200
    bh = 14 * len(info_lines) + 12
    # Background box
    draw.rectangle([px, py, px+bw, py+bh], fill=(10, 20, 40), outline=(0, 180, 255))
    draw.rectangle([px, py, px+bw, py+14], fill=(0, 60, 120))
    draw.text((px+4, py+1), f"《解析結果》{ent.name}", fill=(0, 220, 255), font=font_log)
    for i, (txt, col) in enumerate(info_lines):
        draw.text((px+8, py+16+i*14), txt, fill=col, font=font_log)

def draw_devour_fx(draw, ent, frame):
    """Draw devour absorption effect around entity."""
    px = MAP_X + ent.x * CELL + CELL//2
    py = MAP_Y + ent.y * CELL + CELL//2
    for i in range(8):
        angle = (frame * 0.5 + i * 0.785)
        r = 20 + 8 * math.sin(frame * 0.8 + i)
        ex = int(px + r * math.cos(angle))
        ey = int(py + r * math.sin(angle))
        draw.ellipse([ex-3, ey-3, ex+3, ey+3], fill=C_DEVOUR)
    # Inner glow
    gr = 10 + int(5 * math.sin(frame * 1.2))
    draw.ellipse([px-gr, py-gr, px+gr, py+gr], outline=(255, 80, 120), width=2)

# =================================================================
# SCENE GENERATORS
# =================================================================

def gen_scene_1_dungeon_explore():
    """Scene 1: Exploring the Slum Dungeon — shows dungeon, player, enemies, items."""
    player = Ent(5, 3, '@', C_PLAYER, "主人公", 85, 100)
    pet    = Ent(6, 3, 'p', C_PET, "ハスクハウンド", 40, 40)
    enemies = [
        Ent(14, 2, 'B', C_ENEMY, "ミダス重装兵", 120, 120),
        Ent(22, 6, 'W', C_ENEMY2, "風術師", 60, 60),
        Ent(10, 8, 'H', C_HUSK, "抜け殻", 0, 0),
    ]
    npc = Ent(20, 14, 'N', C_NPC, "バルバロッサ", 200, 200)

    frames = []
    # Player walks right over 16 frames
    path = [(5,3),(6,3),(7,3),(8,3),(8,3),(9,3),(10,3),(11,3),
            (11,3),(12,3),(12,3),(12,3),(12,3),(12,3),(12,3),(12,3)]
    log_lines = [
        ("廃棄層 深度700m に到着した。", (180, 190, 210)),
        ("周囲に敵影を感知... 慎重に進もう。", (200, 200, 150)),
    ]
    for fi, (px, py) in enumerate(path):
        img = Image.new("RGB", (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        player.x, player.y = px, py
        pet.x, pet.y = max(1, px-1), py

        draw_hud(draw, "主人公", 85, 100, 40, 50, 10, "廃棄層 B7F",
                 toxicity=15, skills="3個", gold=1200)
        draw_dungeon(draw, DUNGEON_SLUM)
        draw_minimap(draw, DUNGEON_SLUM, player.x, player.y)
        for e in enemies:
            draw_entity(draw, e)
            if e.hp > 0:
                draw_hp_bar_above(draw, e, e.hp/e.max_hp, C_ENEMY)
        draw_entity(draw, npc)
        draw_entity(draw, pet, pulse=int(20*math.sin(fi*0.5)))
        draw_entity(draw, player, pulse=int(30*math.sin(fi*0.8)))

        if fi >= 8:
            log_lines_show = log_lines + [
                ("ミダス重装兵 を発見！ 《解析(X)》で弱点を確認しよう。", (255, 200, 100))
            ]
        else:
            log_lines_show = log_lines
        draw_log(draw, log_lines_show)
        frames.append(img)
    return frames

def gen_scene_2_scan_analyze():
    """Scene 2: Using Scan (X key) on an enemy — shows analysis overlay."""
    player = Ent(12, 3, '@', C_PLAYER, "主人公", 85, 100)
    target = Ent(14, 2, 'B', C_ENEMY, "ミダス重装兵", 120, 120)
    pet    = Ent(11, 3, 'p', C_PET, "ハスクハウンド", 40, 40)

    scan_info = [
        ("HP: 120/120  種族: 人型", (200, 200, 200)),
        ("弱点属性: 【Ice / Magic】", (100, 200, 255)),
        ("保有スキル: 《鋼鉄の皮膚》[Rare]", (255, 215, 100)),
        ("保有スキル: 《重撃》[Common]", (200, 200, 200)),
        ("捕食成功率: 45%", (255, 120, 120)),
    ]
    log_lines = [
        ("【キー X】《深度解析》を発動！", (100, 200, 255)),
        ("ミダス重装兵 のスキル構成と弱点を検出した！", (200, 255, 200)),
        ("弱点【Ice/Magic】を突けば捕食成功率が上昇する。", (255, 215, 100)),
    ]
    frames = []
    for fi in range(20):
        img = Image.new("RGB", (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        draw_hud(draw, "主人公", 85, 100, 38, 50, 10, "廃棄層 B7F",
                 toxicity=15, skills="3個", gold=1200)
        # Highlight scan range
        highlights = {}
        if fi >= 3:
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    tx, ty = target.x+dx, target.y+dy
                    if 0 <= tx < 30 and 0 <= ty < 18:
                        highlights[(tx, ty)] = (20, 40, 60)
        draw_dungeon(draw, DUNGEON_SLUM, highlights=highlights)
        draw_minimap(draw, DUNGEON_SLUM, player.x, player.y)
        draw_entity(draw, pet)
        draw_entity(draw, target, pulse=int(40*math.sin(fi*0.6)))
        draw_entity(draw, player)
        # Scan popup appears gradually
        if fi >= 5:
            visible = min(len(scan_info), (fi - 5) // 2 + 1)
            draw_scan_overlay(draw, target, scan_info[:visible])
        vis_log = log_lines[:min(len(log_lines), fi//4+1)]
        draw_log(draw, vis_log)
        frames.append(img)
    return frames

def gen_scene_3_devour_combat():
    """Scene 3: Devour action (V key) — shows combat, skill theft, Husk transformation."""
    player = Ent(13, 2, '@', C_PLAYER, "主人公", 80, 100)
    target = Ent(14, 2, 'B', C_ENEMY, "ミダス重装兵", 15, 120)

    frames = []
    log_phases = [
        [("ミダス重装兵のHPが低下！ 捕食のチャンスだ！", (255, 200, 100))],
        [("ミダス重装兵のHPが低下！ 捕食のチャンスだ！", (255, 200, 100)),
         ("【キー V】《喰らい(Devour)》を発動！！", (255, 80, 120))],
        [("【キー V】《喰らい(Devour)》を発動！！", (255, 80, 120)),
         ("【捕食成功！】《鋼鉄の皮膚》[Rare] を強奪した！", (255, 215, 0)),
         ("防御力 +25 / 物理耐性 +15% を恒久獲得！", (100, 255, 180))],
        [("【捕食成功！】《鋼鉄の皮膚》[Rare] を強奪した！", (255, 215, 0)),
         ("防御力 +25 / 物理耐性 +15% を恒久獲得！", (100, 255, 180)),
         ("敵はスキルを失い『抜け殻（Husk）』へと退化した...", (150, 150, 150)),
         ("【毒性上昇】スキル拒絶反応: 15% → 28%", (200, 60, 200))],
    ]
    for fi in range(28):
        img = Image.new("RGB", (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        tox = 15 if fi < 16 else 28
        draw_hud(draw, "主人公", 80, 100, 35, 50, 10, "廃棄層 B7F",
                 toxicity=tox, skills="3→4個" if fi >= 16 else "3個", gold=1200)
        draw_dungeon(draw, DUNGEON_SLUM)
        draw_minimap(draw, DUNGEON_SLUM, player.x, player.y)

        if fi < 8:
            # Pre-devour: enemy is damaged
            target.hp = 15
            draw_entity(draw, target, pulse=int(20*math.sin(fi)))
            draw_hp_bar_above(draw, target, 15/120, C_ENEMY)
            phase = 0
        elif fi < 16:
            # Devour animation
            draw_entity(draw, target, pulse=int(60*math.sin(fi*1.5)))
            draw_devour_fx(draw, target, fi)
            phase = 1 if fi < 12 else 2
        else:
            # Post-devour: enemy becomes Husk
            husk = Ent(14, 2, 'H', C_HUSK, "抜け殻", 0, 0)
            draw_entity(draw, husk)
            phase = 3

        draw_entity(draw, player, pulse=int(30*math.sin(fi*0.6)))
        draw_log(draw, log_phases[min(phase, len(log_phases)-1)])
        frames.append(img)
    return frames

def gen_scene_4_synthesis_base():
    """Scene 4: Chimera Synthesis (Shift+T) and Base expansion — shows town/base screen."""
    base_map = [
        "##############################",
        "#.....#........##............#",
        "#.合成.#..闇市..##...ペット...#",
        "#..炉..+........+....宿舎...#",
        "#.....#........##............#",
        "####+####+#######+#####+######",
        "#..........................>.#",
        "#...........拠点...........>.#",
        "#..........中央広場.........>.#",
        "#...........................>#",
        "####+#####+#######+#####+#####",
        "#.....#........##............#",
        "#.医療.#..武器庫.##...訓練場..#",
        "#.施設.+........+...........#",
        "#.....#........##............#",
        "##############################",
        "                              ",
        "                              ",
    ]
    player = Ent(14, 7, '@', C_PLAYER, "主人公", 95, 100)
    npc1 = Ent(3, 3, 'C', (200, 150, 255), "鍛冶師クラフト", 100, 100)
    npc2 = Ent(10, 3, 'M', C_NPC, "闇商ルカ", 100, 100)
    npc3 = Ent(24, 3, 'P', C_PET, "ハスクハウンド", 45, 45)

    log_phases = [
        [("スラム地下拠点に帰還した。", (180, 190, 210)),
         ("合成炉の前に立つ。所持スキルから2つを選択...", (200, 200, 150))],
        [("【Shift+T】《キメラ合成炉》を起動！", (180, 100, 255)),
         ("素材: 《初級火炎》× 《思考加速》を投入中...", (200, 200, 200))],
        [("【合成成功！】《変異融合：業火の超思考》[Rare] が誕生した！", (255, 215, 0)),
         ("闇市場価値: 12,000 アルド", (255, 200, 100))],
        [("【合成成功！】《変異融合：業火の超思考》[Rare] が誕生した！", (255, 215, 0)),
         ("【ペット帰還】ハスクハウンドが 800 アルドを持ち帰った！", (255, 180, 220)),
         ("【拠点】施設『地下闇市場』が Lv.2 にアップグレード！", (100, 255, 200))],
    ]
    frames = []
    for fi in range(28):
        img = Image.new("RGB", (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        gold = 4500 if fi < 20 else 5300
        draw_hud(draw, "主人公", 95, 100, 45, 50, 12, "スラム地下拠点 Lv.2",
                 toxicity=10, skills="6個", gold=gold)
        draw_dungeon(draw, base_map)
        draw_minimap(draw, base_map, player.x, player.y)
        draw_entity(draw, npc1, pulse=int(15*math.sin(fi*0.3)))
        draw_entity(draw, npc2)
        draw_entity(draw, npc3, pulse=int(20*math.sin(fi*0.4)))
        draw_entity(draw, player)

        # Synthesis FX
        if 8 <= fi < 16:
            cx = MAP_X + 3 * CELL + CELL//2
            cy = MAP_Y + 3 * CELL + CELL//2
            for i in range(6):
                angle = fi * 0.8 + i * 1.05
                r = 15 + 10 * math.sin(fi * 0.5)
                ex = int(cx + r * math.cos(angle))
                ey = int(cy + r * math.sin(angle))
                draw.ellipse([ex-4, ey-4, ex+4, ey+4], fill=C_SYNTH)
            draw.ellipse([cx-8, cy-8, cx+8, cy+8], outline=(255, 200, 255), width=2)

        phase = min(fi // 7, len(log_phases) - 1)
        draw_log(draw, log_phases[phase])
        frames.append(img)
    return frames

def gen_scene_5_boss_warp():
    """Scene 5: Boss battle and world transition."""
    player = Ent(5, 8, '@', C_PLAYER, "主人公", 400, 450)
    boss   = Ent(20, 8, 'Ω', (255, 50, 50), "クロノス・ミダス", 50000, 50000)

    log_phases = [
        [("【BOSS ENCOUNTER】第0因果律執行神『クロノス・ミダス』が出現！", (255, 80, 80)),
         ("星座共鳴 [Void-Flame] により全攻撃力 +150%！", (180, 100, 255))],
        [("《概念喰らい》を発動！ 因果律の防壁に亀裂が入る！", (255, 215, 0)),
         ("クロノス・ミダスに 12,800 の因果崩壊ダメージ！", (255, 180, 80))],
        [("【因果律崩壊】クロノス・ミダスを撃破！", (100, 255, 180)),
         ("Aの世界の全因果が解放された！", (255, 255, 255))],
        [("【次元ゲート開放】次なる世界への境界線が溶解していく...", (255, 215, 80)),
         ("永続の証『concept_eater_mark』を携え、旅立ちの時。", (200, 230, 255))],
    ]
    frames = []
    for fi in range(32):
        img = Image.new("RGB", (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        boss_hp = max(0, 50000 - fi * 2500)
        draw_hud(draw, "主人公 [神格覚醒]", 400, 450, 200, 225, 50,
                 "バベルタワー 最上層", toxicity=65, skills="22個", gold=45000)
        draw_dungeon(draw, DUNGEON_TOWER)
        draw_minimap(draw, DUNGEON_TOWER, player.x, player.y)

        if fi < 24:
            draw_entity(draw, boss, pulse=int(50*math.sin(fi*0.7)))
            # Boss HP bar (large)
            bpx = MAP_X + boss.x * CELL - 30
            bpy = MAP_Y + boss.y * CELL - 8
            draw.rectangle([bpx, bpy, bpx+80, bpy+4], fill=(60, 20, 20))
            draw.rectangle([bpx, bpy, bpx+int(80*boss_hp/50000), bpy+4],
                           fill=(255, 40, 40))
            draw.text((bpx, bpy-12), f"Ω {boss.name}", fill=(255, 100, 100), font=font_log)
            # Battle FX
            if 8 <= fi < 24:
                for i in range(10):
                    fx = random.randint(MAP_X + 6*CELL, MAP_X + 24*CELL)
                    fy = random.randint(MAP_Y + 4*CELL, MAP_Y + 14*CELL)
                    s = random.randint(2, 5)
                    c = random.choice([(255,80,80),(255,200,60),(100,200,255),(200,100,255)])
                    draw.ellipse([fx-s, fy-s, fx+s, fy+s], fill=c)
        else:
            # Warp gate FX
            cx = MAP_X + 14 * CELL
            cy = MAP_Y + 8 * CELL
            for r in range(3):
                radius = 30 + r * 20 + int(10 * math.sin(fi * 0.5 + r))
                draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                             outline=(100+r*50, 200, 255), width=2)

        draw_entity(draw, player, pulse=int(40*math.sin(fi*0.5)))

        phase = min(fi // 8, len(log_phases) - 1)
        draw_log(draw, log_phases[phase])
        frames.append(img)
    return frames


# =================================================================
# MAIN
# =================================================================
def main():
    print("Generating Scene 1: Dungeon Exploration...")
    f1 = gen_scene_1_dungeon_explore()
    print("Generating Scene 2: Scan & Analyze...")
    f2 = gen_scene_2_scan_analyze()
    print("Generating Scene 3: Devour Combat...")
    f3 = gen_scene_3_devour_combat()
    print("Generating Scene 4: Synthesis & Base...")
    f4 = gen_scene_4_synthesis_base()
    print("Generating Scene 5: Boss & World Transition...")
    f5 = gen_scene_5_boss_warp()

    all_frames = f1 + f2 + f3 + f4 + f5

    out_main  = Path("demo_skill_eater.gif")
    out_asset = Path("assets/demo_skill_eater_story.gif")
    out_asset.parent.mkdir(parents=True, exist_ok=True)

    for out in [out_main, out_asset]:
        all_frames[0].save(
            out,
            save_all=True,
            append_images=all_frames[1:],
            duration=int(1000 / FPS),
            loop=0,
            optimize=True,
        )
        print(f"  -> {out} ({out.stat().st_size // 1024} KB, {len(all_frames)} frames)")

    print("Done!")

if __name__ == "__main__":
    main()
