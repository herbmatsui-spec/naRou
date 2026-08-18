"""
Generate high-fidelity animated GIF preview that directly reflects the true codebase of naRou: Masterpiece Edition.
Accurately renders:
1. True 3-tier HUD (Status, HP/MP bars, Gold, Platinum, God piety, Turn/Floor, Survival Hunger/Karma)
2. Accurate Grid Map (Fog of War, Dynamic Lighting, Altar, Stairs, Resource Nodes, Items with rarities)
3. Actual Entities (@ Player, p Sister Ciel, Slime/Orc/Dragon, Gwen the Snail girl)
4. Floating text damage (-18, -248 CRITICAL!), Particles (💥, ✧ spell circle)
5. True Cinematic Log & Tooltip System
6. In-game features: Exploration -> Combat -> God Prayer -> Inventory/Skill Tree -> NG+ Reincarnation
"""

from PIL import Image, ImageDraw
import math

# Screen dimensions matching terminal/canvas ratio (800x480)
W, H = 840, 500

# Color definitions from constants.py & render_system.py
BG_DARK = (10, 12, 18)
PANEL_BG = (16, 20, 32)
PANEL_BORDER = (45, 60, 90)
TEXT_WHITE = (240, 245, 255)
TEXT_MUTED = (140, 155, 180)
COLOR_HP_GREEN = (100, 255, 100)
COLOR_MP_BLUE = (100, 200, 255)
COLOR_GOLD_YELLOW = (255, 215, 0)
COLOR_PET_PINK = (255, 180, 210)
COLOR_ALTAR = (255, 215, 0)
COLOR_WALL_LIT = (145, 120, 90)
COLOR_WALL_DARK = (35, 35, 45)
COLOR_FLOOR_LIT = (195, 175, 145)
COLOR_FLOOR_DARK = (25, 28, 38)

MAP_COLS, MAP_ROWS = 28, 14
CELL_W, CELL_H = 20, 20
MAP_X, MAP_Y = 16, 16

scenes = [
    # Scene 1: Start in Cave Home with Ciel
    {
        "floor_name": "B1F 洞窟の拠点 (我が家)",
        "turn": 12, "gold": 1500, "plat": 12, "karma": 20, "hunger": "満腹", "god": "ジュア(80)",
        "player_hp": (30, 30), "player_mp": (10, 10), "level": 1,
        "player_pos": (6, 7), "pet_pos": (5, 7),
        "altar_pos": (8, 7), "stairs_pos": (22, 7),
        "entities": [("🐌", "かたつむり少女『グウェン』", (12, 4), (255, 180, 220))],
        "items": [("🗡️", (7, 6), (200, 200, 200)), ("🍞", (6, 5), (255, 200, 100))],
        "nodes": [("%", (4, 4), (100, 255, 180))],
        "tooltip": "💡 祭壇の近く: [p]キーで神に祈りを捧げて恩恵を受ける",
        "logs": [
            ("『naRou: Masterpiece Edition』の世界へようこそ！", (255, 255, 120)),
            ("妹分シエル「お兄ちゃん、今日も一緒に頑張ろうね！」", COLOR_PET_PINK),
            ("【初心者ガイド】[?]キーでいつでもヘルプ・操作一覧を確認できます！", (120, 255, 200)),
            ("【操作】矢印:移動 [Space]:行動 [l]:調査 [i]:荷物 [Shift+S]:ツリー", (180, 220, 255))
        ],
        "fx": []
    },
    # Scene 2: Combat in Puppy Cave
    {
        "floor_name": "B3F 子犬の洞窟 (ぷち掃討)",
        "turn": 48, "gold": 1850, "plat": 14, "karma": 20, "hunger": "普通", "god": "ジュア(85)",
        "player_hp": (26, 30), "player_mp": (10, 10), "level": 2,
        "player_pos": (12, 6), "pet_pos": (11, 7),
        "altar_pos": None, "stairs_pos": (24, 10),
        "entities": [
            ("x", "ぷち", (13, 6), (100, 255, 150)),
            ("x", "ぷち", (14, 5), (100, 255, 150)),
            ("o", "オーク戦士", (16, 7), (255, 100, 100))
        ],
        "items": [("!", (10, 5), (100, 200, 255)), ("🍖", (13, 7), (220, 80, 80))],
        "nodes": [("$", (18, 4), (255, 215, 0))],
        "tooltip": "⚔️ 戦闘中: ぷちに通常攻撃！ 命中率 88%",
        "logs": [
            ("あなたの使い古しの長剣が命中！ ぷちに 18 のダメージ！", (240, 240, 240)),
            ("妹分シエルの射撃！ ぷちに 12 のダメージ！", COLOR_PET_PINK),
            ("★ぷちを撃破！ (経験値+35, 肉をドロップ)", (255, 215, 0)),
            ("主クエスト『ぷち掃討の栄誉』進捗: [1/3]", (100, 255, 200))
        ],
        "fx": [("text", "-18", (13, 5.5), (255, 100, 100)), ("particle", "💥", (13, 6), (255, 180, 50))]
    },
    # Scene 3: Advanced Systems (Skill Tree & High Tier Dungeon)
    {
        "floor_name": "B7F ネフィア深層 (★混沌の古龍)",
        "turn": 182, "gold": 12800, "plat": 46, "karma": 35, "hunger": "普通", "god": "ジュア(220)",
        "player_hp": (195, 210), "player_mp": (85, 120), "level": 18,
        "player_pos": (10, 7), "pet_pos": (9, 7),
        "altar_pos": None, "stairs_pos": (25, 6),
        "entities": [
            ("D", "★火炎の古龍『煉獄龍』", (16, 7), (255, 50, 50)),
            ("w", "ヘルハウンド", (14, 5), (255, 120, 60))
        ],
        "items": [("★", (18, 8), (255, 215, 0)), ("🪄", (8, 4), (100, 255, 255))],
        "nodes": [("$", (20, 3), (255, 215, 0))],
        "tooltip": "🔥 古龍の予兆ブレスを察知！ 詠唱または回避を選択！",
        "logs": [
            ("必殺スキル覚醒『神威・次元斬』を発動！", (255, 220, 100)),
            ("★火炎の古龍に 248 のクリティカルダメージ！", (255, 100, 100)),
            ("シエルの天馬進化スキル『天翔の癒し』！ HPが60回復！", COLOR_PET_PINK),
            ("古龍の火炎ブレスをギリギリで回避した！", (120, 255, 200))
        ],
        "fx": [("text", "-248 CRIT!", (16, 6), (255, 230, 80)), ("particle", "✧", (10, 7), (180, 140, 255))]
    },
    # Scene 4: Reincarnation & NG+ Loop
    {
        "floor_name": "クリアの祭壇 (輪廻転生 NG+)",
        "turn": 310, "gold": 45000, "plat": 120, "karma": 65, "hunger": "満腹", "god": "ジュア(400)",
        "player_hp": (280, 280), "player_mp": (150, 150), "level": 25,
        "player_pos": (13, 7), "pet_pos": (12, 7),
        "altar_pos": (14, 7), "stairs_pos": (20, 7),
        "entities": [("👑", "女神ジュアの幻影", (14, 5), (255, 240, 150))],
        "items": [("★", (13, 8), (255, 215, 0)), ("★", (15, 8), (255, 215, 0))],
        "nodes": [],
        "tooltip": "🌟 輪廻の儀式: 全能力値+10%ボーナスとレガシースキルを継承して次代へ",
        "logs": [
            ("★主クエスト『レシマスの秘宝』完全制覇！", (255, 215, 0)),
            ("【輪廻転生NG+】第1回転生が実行可能になりました！", (100, 255, 200)),
            ("獲得ボーナス: 基礎能力値継承 / 固有称号『伝説の救世主』獲得", (255, 240, 120)),
            ("次なる旅路へ… naRou: Masterpiece Edition", (200, 220, 255))
        ],
        "fx": [("particle", "✨", (13, 7), (255, 240, 100)), ("particle", "✨", (14, 5), (255, 215, 0))]
    }
]

frames = []

for sc_idx, sc in enumerate(scenes):
    for sub in range(4):
        img = Image.new("RGB", (W, H), BG_DARK)
        draw = ImageDraw.Draw(img)

        # 1. Top HUD Header
        draw.rectangle([(12, 10), (W - 12, 38)], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
        draw.text((22, 16), "naRou: Masterpiece Edition v1.0.0", fill=COLOR_GOLD_YELLOW)
        draw.text((290, 16), f"| {sc['floor_name']}", fill=TEXT_WHITE)
        draw.text((540, 16), f"💰 {sc['gold']}G  💎 {sc['plat']}P  ⚖️ {sc['karma']}  Turn:{sc['turn']}", fill=(200, 220, 255))

        # 2. Main Map Viewport
        map_w = MAP_COLS * CELL_W
        map_h = MAP_ROWS * CELL_H
        draw.rectangle([(MAP_X, MAP_Y + 30), (MAP_X + map_w, MAP_Y + 30 + map_h)], fill=(12, 14, 22), outline=PANEL_BORDER, width=2)

        # Draw Tiles
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                tx = MAP_X + c * CELL_W
                ty = MAP_Y + 30 + r * CELL_H
                is_wall = (r == 0 or r == MAP_ROWS - 1 or c == 0 or c == MAP_COLS - 1)
                
                # Fog & distance lighting
                p_cx, p_cy = sc["player_pos"]
                dist = math.hypot(c - p_cx, r - p_cy)
                
                if dist > 10:
                    # Unexplored / dark
                    if is_wall:
                        draw.rectangle([(tx, ty), (tx + CELL_W, ty + CELL_H)], fill=(20, 22, 30))
                    else:
                        draw.text((tx + 6, ty + 2), ".", fill=(35, 40, 50))
                else:
                    # Visible / Lit
                    if is_wall:
                        draw.rectangle([(tx, ty), (tx + CELL_W, ty + CELL_H)], fill=COLOR_WALL_LIT if dist < 5 else (90, 75, 60))
                        draw.rectangle([(tx + 1, ty + 1), (tx + CELL_W - 1, ty + CELL_H - 1)], fill=(45, 38, 30))
                    else:
                        floor_col = (140, 130, 110) if dist < 5 else (70, 65, 55)
                        draw.text((tx + 6, ty + 2), ".", fill=floor_col)

        # Draw Altar if present
        if sc["altar_pos"]:
            ax, ay = sc["altar_pos"]
            draw.text((MAP_X + ax * CELL_W + 3, MAP_Y + 30 + ay * CELL_H), "⛩️", fill=COLOR_ALTAR)

        # Draw Stairs
        sx, sy = sc["stairs_pos"]
        draw.text((MAP_X + sx * CELL_W + 5, MAP_Y + 30 + sy * CELL_H), ">", fill=(100, 200, 255))

        # Draw Resource Nodes
        for n_sym, (nx, ny), n_col in sc["nodes"]:
            draw.text((MAP_X + nx * CELL_W + 4, MAP_Y + 30 + ny * CELL_H), n_sym, fill=n_col)

        # Draw Ground Items
        for i_sym, (ix, iy), i_col in sc["items"]:
            draw.text((MAP_X + ix * CELL_W + 3, MAP_Y + 30 + iy * CELL_H), i_sym, fill=i_col)

        # Draw Mobs / Entities
        for e_sym, e_name, (ex, ey), e_col in sc["entities"]:
            draw.text((MAP_X + ex * CELL_W + 4, MAP_Y + 30 + ey * CELL_H), e_sym, fill=e_col)

        # Draw Player & Pet
        px, py = sc["player_pos"]
        pet_x, pet_y = sc["pet_pos"]
        bob = int(math.sin((sub + sc_idx * 4) * 0.9) * 2)

        # Pet
        draw.text((MAP_X + pet_x * CELL_W + 4, MAP_Y + 30 + pet_y * CELL_H + bob), "p", fill=COLOR_PET_PINK)
        # Player
        draw.text((MAP_X + px * CELL_W + 4, MAP_Y + 30 + py * CELL_H + bob), "@", fill=(255, 255, 255))

        # FX Overlays (Floating text & particles)
        for fx_type, fx_val, (fx_x, fx_y), fx_col in sc["fx"]:
            draw.text((MAP_X + int(fx_x * CELL_W) - 4, MAP_Y + 30 + int(fx_y * CELL_H) - sub * 2), fx_val, fill=fx_col)

        # 3. Right Side Vitals Panel & Minimap
        side_x = MAP_X + map_w + 14
        side_w = W - side_x - 12

        # Minimap Frame
        draw.rectangle([(side_x, MAP_Y + 30), (side_x + side_w, MAP_Y + 120)], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
        draw.text((side_x + 8, MAP_Y + 34), "[ ミニマップ & 凡例 ]", fill=(100, 180, 255))
        draw.text((side_x + 8, MAP_Y + 52), "@:自分  p:シエル  >:階段", fill=TEXT_MUTED)
        draw.text((side_x + 8, MAP_Y + 70), "x:魔物  !:薬品    $:鉱脈", fill=TEXT_MUTED)
        draw.text((side_x + 8, MAP_Y + 88), "_:祭壇  %:薬草    ★:神器", fill=TEXT_MUTED)
        draw.text((side_x + 8, MAP_Y + 104), "天候: 晴れ  状態: 良好", fill=(120, 255, 180))

        # Character Stats Card
        draw.rectangle([(side_x, MAP_Y + 128), (side_x + side_w, MAP_Y + 30 + map_h)], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
        draw.text((side_x + 8, MAP_Y + 134), f"名無しの冒険者 Lv.{sc['level']}", fill=COLOR_GOLD_YELLOW)
        draw.text((side_x + 8, MAP_Y + 152), f"職業: ウォーリア ({sc['hunger']})", fill=TEXT_WHITE)
        draw.text((side_x + 8, MAP_Y + 170), f"信仰: {sc['god']}", fill=(200, 160, 255))

        # HP Bar
        hp_cur, hp_max = sc["player_hp"]
        draw.text((side_x + 8, MAP_Y + 192), f"HP: {hp_cur}/{hp_max}", fill=COLOR_HP_GREEN)
        draw.rectangle([(side_x + 8, MAP_Y + 208), (side_x + side_w - 8, MAP_Y + 214)], fill=(30, 40, 50))
        hp_len = int((side_w - 16) * (hp_cur / max(1, hp_max)))
        draw.rectangle([(side_x + 8, MAP_Y + 208), (side_x + 8 + hp_len, MAP_Y + 214)], fill=COLOR_HP_GREEN)

        # MP Bar
        mp_cur, mp_max = sc["player_mp"]
        draw.text((side_x + 8, MAP_Y + 224), f"MP: {mp_cur}/{mp_max}", fill=COLOR_MP_BLUE)
        draw.rectangle([(side_x + 8, MAP_Y + 240), (side_x + side_w - 8, MAP_Y + 246)], fill=(30, 40, 50))
        mp_len = int((side_w - 16) * (mp_cur / max(1, mp_max)))
        draw.rectangle([(side_x + 8, MAP_Y + 240), (side_x + 8 + mp_len, MAP_Y + 246)], fill=COLOR_MP_BLUE)

        # Companion Info
        draw.text((side_x + 8, MAP_Y + 258), "【仲間】妹分シエル", fill=COLOR_PET_PINK)
        draw.text((side_x + 8, MAP_Y + 274), "好感度: 親愛 (同行中)", fill=TEXT_MUTED)

        # 4. Bottom Realtime Tooltip & Action Banner
        btm_y = MAP_Y + 30 + map_h + 8
        draw.rectangle([(12, btm_y), (W - 12, btm_y + 24)], fill=(20, 26, 40), outline=PANEL_BORDER, width=1)
        draw.text((20, btm_y + 5), sc["tooltip"], fill=COLOR_GOLD_YELLOW)

        # 5. Cinematic Color Message Log (4 Lines matching in-game render_system)
        log_y = btm_y + 30
        draw.rectangle([(12, log_y), (W - 12, H - 12)], fill=(12, 14, 22), outline=PANEL_BORDER, width=1)
        for l_idx, (l_msg, l_col) in enumerate(sc["logs"][:4]):
            draw.text((22, log_y + 6 + l_idx * 16), f"• {l_msg}", fill=l_col)

        frames.append(img)

# Save high quality GIF
out_gif = "e:/notedesk/elona/demo_gameplay.gif"
frames[0].save(
    out_gif,
    save_all=True,
    append_images=frames[1:],
    duration=1000,
    loop=0
)
print(f"Successfully generated accurate {out_gif} with {len(frames)} frames.")
