"""
generate_web_visual_showcase_gif.py
Web版ビジュアル強化（改善案2〜9）の魅力を伝えるデモGIFをPillowで生成するスクリプト。
出力: assets/demo_web_visual_v2.gif
"""

from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import os

def generate_gif():
    width, height = 640, 400
    fps = 5
    duration_per_frame = 800  # ms
    
    frames = []
    
    # フォント取得（デフォルトまたはシステムフォント）
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font_title = font_main = font_sub = ImageFont.load_default()

    # 3シーン分のフレームを作成
    scenes = [
        {
            "title": "Scene 1: 9-slice Panel & Rarity Frames",
            "desc": "Glass-morphic panels with border glow & 5 rarity tiers",
            "bg": (10, 11, 16),
            "panel_bg": (18, 22, 36),
            "accent": (229, 169, 59),
            "rarity": ("LEGENDARY ITEM", (212, 175, 55))
        },
        {
            "title": "Scene 2: Typography & Font Hierarchy",
            "desc": "Cinzel title, H1-H3 headers, and clean body fonts",
            "bg": (15, 23, 42),
            "panel_bg": (30, 41, 59),
            "accent": (56, 189, 248),
            "rarity": ("EPIC SKILL", (168, 85, 247))
        },
        {
            "title": "Scene 3: Animations & 5 Themes",
            "desc": "Float-up damage, smooth modals, Dark/Light/Sepia",
            "bg": (26, 22, 37),
            "panel_bg": (45, 38, 64),
            "accent": (16, 185, 129),
            "rarity": ("RARE EQUIPMENT", (59, 130, 246))
        }
    ]

    for idx, scene in enumerate(scenes):
        # 各シーンで数フレーム（アニメーション効果）
        for step in range(3):
            img = Image.new("RGB", (width, height), scene["bg"])
            draw = ImageDraw.Draw(img)
            
            # 背景グラデーション風の装飾
            draw.rectangle([0, 0, width, 50], fill=(20, 24, 40))
            
            # ヘッダータイトル
            draw.text((24, 15), "naRogue: Web Visual Edition (v2)", fill=scene["accent"], font=font_title)
            
            # メインパネル（奥行き表現：二重枠）
            panel_box = [40, 70, width - 40, height - 60]
            draw.rounded_rectangle(panel_box, radius=12, fill=scene["panel_bg"], outline=(99, 130, 210, 100), width=2)
            # 内枠ハイライト
            inner_box = [42, 72, width - 42, height - 62]
            draw.rounded_rectangle(inner_box, radius=10, outline=(255, 255, 255, 20), width=1)
            
            # シーン内コンテンツ
            draw.text((60, 95), scene["title"], fill=(240, 244, 252), font=font_main)
            draw.text((60, 125), scene["desc"], fill=(139, 155, 180), font=font_sub)
            
            # レアリティバッジのプレビュー
            r_box = [60, 165, width - 60, 220]
            r_color = scene["rarity"][1]
            draw.rounded_rectangle(r_box, radius=8, fill=(10, 12, 20), outline=r_color, width=2)
            draw.text((80, 182), f"★ {scene['rarity'][0]} [Affix Bonus]", fill=r_color, font=font_main)
            
            # ステータス・アニメーションプレビュー要素
            y_offset = step * 10
            draw.text((60, 240), f">> Vitals & Status Bars [Step {step+1}/3]", fill=(200, 210, 230), font=font_sub)
            draw.rounded_rectangle([60, 265, 300, 285], radius=4, fill=(20, 30, 50))
            draw.rounded_rectangle([60, 265, 60 + 180 + y_offset * 15, 285], radius=4, fill=(46, 204, 113))
            draw.text((310, 267), "HP: 100/100", fill=(200, 200, 200), font=font_sub)
            
            # 浮遊ダメージ表示プレビュー（float-up表現）
            if step > 0:
                float_y = 210 - (step * 15)
                draw.text((450, float_y), "-48 CRITICAL!", fill=(231, 76, 60), font=font_main)
                
            # フッター
            draw.text((40, height - 35), "demos/visual-showcase.html | assets/css/components.css", fill=(100, 115, 140), font=font_sub)
            
            frames.append(img)

    os.makedirs("assets", exist_ok=True)
    out_path = "assets/demo_web_visual_v2.gif"
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_per_frame,
        loop=0
    )
    print(f"Successfully generated {out_path}")

if __name__ == "__main__":
    generate_gif()
