"""
Generate a high quality animated GIF preview for naRou: Masterpiece Edition gameplay.
Creates demo_gameplay.gif showing a rogue adventure loop in naRou: Masterpiece Edition.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

W, H = 720, 420
BG_COLOR = (10, 14, 25)
PANEL_BG = (18, 25, 45)
PANEL_BORDER = (50, 75, 120)
TEXT_WHITE = (240, 245, 255)
TEXT_MUTED = (140, 160, 190)
GOLD = (255, 200, 60)
HP_GREEN = (46, 204, 113)
MP_BLUE = (52, 152, 219)
RED_ACCENT = (231, 76, 60)
PURPLE_ACCENT = (155, 89, 182)

# Grid setup
COLS, ROWS = 22, 11
CELL_SZ = 26
GRID_X, GRID_Y = 24, 75

scenes = [
    {
        "floor": "B1F 洞窟の拠点",
        "action": "我が家でシエルと会話＆冒険準備中...",
        "player_pos": (2, 5),
        "mobs": [],
        "logs": [
            "『naRou: Masterpiece Edition』の世界へようこそ！",
            "妹分シエル「お兄ちゃん、今日も一緒に頑張ろうね！」",
        ],
    },
    {
        "floor": "B1F ヴェルニスの街",
        "action": "鉱山の街ヴェルニスに到着！酒場で依頼を受注",
        "player_pos": (6, 4),
        "mobs": [
            ("商人", (5, 3), (120, 200, 255)),
            ("街の案内人", (8, 6), (200, 220, 100)),
        ],
        "logs": [
            "街の案内人「ここは鉱山の街ヴェルニスだよ」",
            "酒場マスターから『子犬の救出依頼』を受けた！",
        ],
    },
    {
        "floor": "B3F 子犬の洞窟",
        "action": "ダンジョン探索！ぷちの大群と交戦中",
        "player_pos": (10, 5),
        "mobs": [
            ("ぷち", (11, 5), (100, 255, 150)),
            ("ぷち", (12, 6), (100, 255, 150)),
            ("オーク", (14, 4), (255, 120, 120)),
        ],
        "logs": [
            "ぷちに通常攻撃！ 18のダメージ！",
            "ぷちを撃破した！ (経験値+35, 120G)",
        ],
    },
    {
        "floor": "B7F ネフィア深層",
        "action": "★火炎の古龍との決戦！範囲魔法を詠唱！",
        "player_pos": (8, 6),
        "mobs": [
            ("★古龍", (14, 5), (255, 60, 60)),
            ("竜の眷属", (12, 3), (255, 140, 60)),
        ],
        "logs": [
            "★古龍のブレスを回避！",
            "必殺スキル『神威・次元斬』発動！ 248のクリティカル！",
        ],
    },
    {
        "floor": "クリア 輪廻の祠",
        "action": "主クエスト制覇！第1回転生NG+へ突入",
        "player_pos": (11, 5),
        "mobs": [("女神ジュア", (11, 2), (255, 220, 100))],
        "logs": [
            "主クエスト『レシマスの秘宝』を完全踏破！",
            "転生ボーナス獲得: 全能力値+10%, カルマ+50, 継承スキル開放！",
        ],
    },
]

frames = []

for sc_idx, sc in enumerate(scenes):
    for sub in range(4):  # 4 frames per scene for smooth animation
        img = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Header Bar
        draw.rectangle([(16, 12), (W - 16, 56)], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
        draw.text((28, 22), "naRou: Masterpiece Edition", fill=GOLD)
        draw.text((260, 22), f"| {sc['floor']}", fill=TEXT_WHITE)
        draw.text((450, 22), "💰 12,500G   💎 45P   ⚖️ +20", fill=(200, 220, 255))

        # Viewport Map Grid Panel
        map_w = COLS * CELL_SZ
        map_h = ROWS * CELL_SZ
        draw.rectangle(
            [(GRID_X - 4, GRID_Y - 4), (GRID_X + map_w + 4, GRID_Y + map_h + 4)],
            fill=(12, 16, 28),
            outline=PANEL_BORDER,
            width=2,
        )

        # Draw Grid Tiles
        for r in range(ROWS):
            for c in range(COLS):
                cx = GRID_X + c * CELL_SZ
                cy = GRID_Y + r * CELL_SZ
                # Draw floor dot
                if (r == 0 or r == ROWS - 1 or c == 0 or c == COLS - 1) and not (
                    r == 5 and c == COLS - 1
                ):
                    # Wall
                    draw.rectangle(
                        [(cx, cy), (cx + CELL_SZ - 2, cy + CELL_SZ - 2)],
                        fill=(30, 38, 60),
                    )
                else:
                    # Floor
                    draw.text((cx + 8, cy + 4), ".", fill=(45, 60, 90))

        # Draw stairs
        draw.text(
            (GRID_X + (COLS - 2) * CELL_SZ + 6, GRID_Y + 5 * CELL_SZ + 2),
            ">",
            fill=(100, 200, 255),
        )

        # Draw Mobs
        for name, pos, color in sc["mobs"]:
            mx = GRID_X + pos[0] * CELL_SZ + 4
            my = GRID_Y + pos[1] * CELL_SZ + 2
            draw.text((mx, my), name[0], fill=color)

        # Draw Player with subtle bobbing
        px, py = sc["player_pos"]
        bob = int(math.sin((sub + sc_idx * 4) * 0.8) * 2)
        pl_x = GRID_X + px * CELL_SZ + 6
        pl_y = GRID_Y + py * CELL_SZ + 2 + bob
        draw.text((pl_x, pl_y), "@", fill=(255, 255, 120))
        # Draw Pet (Ciel)
        draw.text((pl_x - CELL_SZ + 2, pl_y), "p", fill=(255, 160, 200))

        # Right Side Status / Vitals Card
        stat_x = GRID_X + map_w + 16
        stat_w = W - stat_x - 16
        draw.rectangle(
            [(stat_x, GRID_Y - 4), (stat_x + stat_w, GRID_Y + map_h + 4)],
            fill=PANEL_BG,
            outline=PANEL_BORDER,
            width=1,
        )

        draw.text((stat_x + 12, GRID_Y + 8), "冒険者ステータス", fill=GOLD)
        draw.text((stat_x + 12, GRID_Y + 30), "Lv.24  ウォーリア", fill=TEXT_WHITE)

        # HP Bar
        draw.text((stat_x + 12, GRID_Y + 58), "HP 380/380", fill=HP_GREEN)
        draw.rectangle(
            [(stat_x + 12, GRID_Y + 76), (stat_x + stat_w - 12, GRID_Y + 84)],
            fill=(30, 40, 50),
        )
        draw.rectangle(
            [(stat_x + 12, GRID_Y + 76), (stat_x + stat_w - 12, GRID_Y + 84)],
            fill=HP_GREEN,
        )

        # MP Bar
        draw.text((stat_x + 12, GRID_Y + 96), "MP 190/190", fill=MP_BLUE)
        draw.rectangle(
            [(stat_x + 12, GRID_Y + 114), (stat_x + stat_w - 12, GRID_Y + 122)],
            fill=(30, 40, 50),
        )
        draw.rectangle(
            [
                (stat_x + 12, GRID_Y + 114),
                (stat_x + int((stat_w - 24) * 0.85), GRID_Y + 122),
            ],
            fill=MP_BLUE,
        )

        # Pet Info
        draw.text((stat_x + 12, GRID_Y + 140), "相棒: 妹分シエル", fill=(255, 180, 210))
        draw.text((stat_x + 12, GRID_Y + 160), "進化: 第2段階 [天馬の加護]", fill=TEXT_MUTED)

        # Quick Actions info
        draw.text((stat_x + 12, GRID_Y + 200), "【操作キー】", fill=(180, 200, 230))
        draw.text((stat_x + 12, GRID_Y + 220), "矢印:移動  Space:行動", fill=TEXT_MUTED)
        draw.text((stat_x + 12, GRID_Y + 238), "i:所持品   c:能力  j:職業", fill=TEXT_MUTED)
        draw.text((stat_x + 12, GRID_Y + 256), "Shift+S:ツリー  ?:ヘルプ", fill=TEXT_MUTED)

        # Bottom Log Box
        log_y = GRID_Y + map_h + 12
        log_h = H - log_y - 12
        draw.rectangle(
            [(16, log_y), (W - 16, log_y + log_h)],
            fill=(12, 16, 26),
            outline=PANEL_BORDER,
            width=1,
        )

        # Draw Scene Action Banner
        draw.text((26, log_y + 6), f"▶ {sc['action']}", fill=GOLD)

        # Draw Event Logs
        for l_idx, log_line in enumerate(sc["logs"][:2]):
            draw.text(
                (26, log_y + 26 + l_idx * 16),
                f"• {log_line}",
                fill=TEXT_WHITE if l_idx == 0 else TEXT_MUTED,
            )

        frames.append(img)

# Save as GIF
out_path = "e:/notedesk/elona/demo_gameplay.gif"
frames[0].save(
    out_path,
    save_all=True,
    append_images=frames[1:],
    duration=900,  # 900ms per frame
    loop=0,
)
print(f"Generated {out_path} with {len(frames)} frames.")
