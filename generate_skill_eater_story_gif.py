"""
High-Resolution Cinematic GIF Generator for World A: Skill Eater (All 5 Phases)
Generates demo_skill_eater.gif and assets/demo_skill_eater_story.gif
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 760
HEIGHT = 420
FPS = 12

def get_font(size=14, bold=False):
    fonts = [
        "msgothic.ttc",
        "meiryo.ttc",
        "yumindb.ttf",
        "arial.ttf",
    ]
    for f in fonts:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()

font_title = get_font(18, bold=True)
font_subtitle = get_font(13)
font_body = get_font(12)
font_log = get_font(11)
font_huge = get_font(24, bold=True)

# 5 Major Story Phases
SCENES = [
    # Scene 1: Phase 0 - 転落と覚醒 (Betrayal & Awakening)
    {
        "phase": "PHASE 0: PROLOGUE",
        "title": "【転落と覚醒】 バベルタワー最下層・廃棄場",
        "sub": "エリート監査官から最底辺の廃棄民へ。ゴミ捨て場で見出した禁忌のコード《喰らい》",
        "player_status": "主人公 [元監査官]  HP: 45/100  毒性: 0%  所持スキル: [基礎解析]",
        "target_status": "廃棄場の追捕犬 (HP: 80/80)  敵意: MAX",
        "action_text": "最底辺スキル《解析(X)》を実行中...",
        "log_lines": [
            "[SYSTEM] バベルタワー監査権限を永久剥奪されました。",
            "[STATUS] 廃棄層深度700mへ投棄。生存確率: 3.2%",
            "《解析》完了: 追捕犬はスキル《電撃牙》を保有（捕食確率: 78%）",
        ],
        "bg_color": (15, 18, 25),
        "accent_color": (80, 180, 255),
        "duration": 24,
    },
    # Scene 2: Phase 1 - 禁忌の《喰らい》と抜け殻 (Devour & Husk)
    {
        "phase": "PHASE 1: SURVIVAL & DEVOUR",
        "title": "【禁忌の捕食】 敵スキル強奪と抜け殻化",
        "sub": "弱らせた敵の核を直接喰らい尽くす。スキルを奪われた敵は意志なきHuskと化す",
        "player_status": "主人公 [スキルイーター]  HP: 90/100  毒性: 25%  所持: [基礎解析, 電撃牙]",
        "target_status": "ミダス重装兵 (HP: 15/120) [瀕死・無防備]",
        "action_text": "キー《V》発動！ 《喰らい(Devour)》を実行！！",
        "log_lines": [
            "【喰らい成功！】ミダス重装兵から《鋼鉄の皮膚》を強奪！",
            "【スキル習得】防御力 +25 / 物理耐性 +15% を恒久獲得！",
            "対象はすべてのスキルを失い『抜け殻（Husk）』へと退化した。",
        ],
        "bg_color": (30, 15, 20),
        "accent_color": (255, 80, 120),
        "duration": 26,
    },
    # Scene 3: Phase 2 - キメラ合成炉とスラム復興 (Chimera Synthesis & Base)
    {
        "phase": "PHASE 2: CHIMERA SYNTHESIS",
        "title": "【キメラ合成炉】 認可外スキルの錬成と拠点拡張",
        "sub": "強奪したスキルを炉で融合。ペットを探索へ派遣し、スラム解放戦線を拡大せよ",
        "player_status": "主人公 [アジト拠点 Lv.2]  アルド: 4,500  施設: [合成炉, 闇市, ペット宿舎]",
        "target_status": "キメラ錬成炉: 《初級火炎》 × 《思考加速》",
        "action_text": "キー《Shift+T》：プロシージャル魔導合成を実行！",
        "log_lines": [
            "【魔導合成成功！】新スキル《変異融合：業火の超思考》[Rare] が誕生！",
            "【ペット帰還】ハスクハウンドが『廃棄処分場』から 1,200 アルドを持ち帰った！",
            "【拠点改修】『地下闇市場』が Lv.2 にアップグレード！",
        ],
        "bg_color": (25, 20, 35),
        "accent_color": (200, 120, 255),
        "duration": 26,
    },
    # Scene 4: Phase 3 - 神格化星座盤と因果律ボス (Ascension & Boss)
    {
        "phase": "PHASE 3: ASCENSION & FINAL BATTLE",
        "title": "【神格化ボード】 星座リンクと因果律の打破",
        "sub": "マスタースキルを星座グリッドに装着。世界の理を司る因果律の執行官に挑む",
        "player_status": "主人公 [神格覚醒]  HP: 450/450  星座共鳴: [Void-Flame Synergy]",
        "target_status": "第0因果律執行神『クロノス・ミダス』 (HP: 1200/50000)",
        "action_text": "《概念喰らい》発動！ 因果律の防壁を突破！",
        "log_lines": [
            "【星座共鳴発動】Void × Flameリンクにより全攻撃力 +150%！",
            "【環境ギミック解除】氷壁の防壁を《業火の超思考》で一撃粉砕！",
            "【因果律崩壊】クロノス・ミダスを撃破！ Aの世界の全因果が解放された！",
        ],
        "bg_color": (15, 30, 25),
        "accent_color": (100, 255, 180),
        "duration": 28,
    },
    # Scene 5: Phase 4-5 - 概念結晶とマルチバース跳躍 (Concept & Multiverse)
    {
        "phase": "PHASE 4-5: MULTIVERSE TRANSITION",
        "title": "【時空金庫と次元跳躍】 次なる異世界へ",
        "sub": "強奪した力を3重概念結晶に圧縮。時空金庫に封じ、マルチバースへの門を開く",
        "player_status": "主人公 [次元放浪者]  時空金庫: 3/3 結晶格納  概念: [貪食の極致]",
        "target_status": "次元ゲート『Bの世界：錬金術の深淵』開放率: 100%",
        "action_text": "ワールド遷移コマンド実行：次元ゲートへ突入！！",
        "log_lines": [
            "【概念結晶化】同系統スキル3つを《概念結晶：大罪捕食》へ超圧縮！",
            "【エピローグ】スラムの民は独立を勝ち取り、主人公は伝説の概念喰いとなった。",
            "【次元跳躍完了】永続の証『concept_eater_mark』を携え、次なる世界へ！",
        ],
        "bg_color": (20, 25, 45),
        "accent_color": (255, 215, 80),
        "duration": 30,
    },
]

def draw_scene(scene, frame_idx, total_frames):
    img = Image.new("RGB", (WIDTH, HEIGHT), scene["bg_color"])
    draw = ImageDraw.Draw(img)
    accent = scene["accent_color"]
    t = frame_idx / total_frames

    # Header Panel
    draw.rectangle([10, 10, WIDTH - 10, 48], fill=(10, 12, 18), outline=accent, width=1)
    draw.text((20, 14), scene["phase"], fill=accent, font=font_subtitle)
    draw.text((180, 13), scene["title"], fill=(255, 255, 255), font=font_title)

    # Subtitle / Story Context
    draw.text((20, 56), scene["sub"], fill=(180, 190, 210), font=font_subtitle)

    # Middle Content: Status & Battle Arena Simulation
    # Left Box: Player & Target HUD
    draw.rectangle([10, 80, 360, 240], fill=(12, 15, 22), outline=(50, 60, 80), width=1)
    draw.rectangle([10, 80, 360, 105], fill=(20, 25, 38))
    draw.text((20, 85), "◆ プレイヤーステータス & 戦況", fill=(200, 220, 255), font=font_subtitle)
    draw.text((20, 115), scene["player_status"], fill=(150, 255, 180), font=font_body)
    
    # HP Bar simulation
    draw.rectangle([20, 140, 340, 152], fill=(40, 40, 50))
    hp_width = 320 * (0.8 + 0.15 * math.sin(t * math.pi * 2))
    draw.rectangle([20, 140, 20 + hp_width, 152], fill=(80, 220, 120))
    
    draw.text((20, 165), "◆ 対象ステータス", fill=(255, 180, 180), font=font_subtitle)
    draw.text((20, 190), scene["target_status"], fill=(255, 200, 150), font=font_body)
    draw.rectangle([20, 215, 340, 227], fill=(40, 40, 50))
    target_hp_width = max(10, 320 * (1.0 - t * 0.7))
    draw.rectangle([20, 215, 20 + target_hp_width, 227], fill=(255, 80, 80))

    # Right Box: Visual Effects & Combat Animation Sim
    draw.rectangle([375, 80, WIDTH - 10, 240], fill=(8, 10, 16), outline=accent, width=1)
    draw.rectangle([375, 80, WIDTH - 10, 105], fill=(20, 25, 38))
    draw.text((385, 85), "⚡ リアルタイム実行シミュレーション", fill=accent, font=font_subtitle)
    
    # Pulse / Action Text in Center
    pulse = int(15 * math.sin(t * math.pi * 4))
    action_box_y = 135 + pulse // 2
    draw.rectangle([390, action_box_y, WIDTH - 25, action_box_y + 40], fill=(25, 30, 45), outline=accent, width=2)
    draw.text((405, action_box_y + 10), scene["action_text"], fill=(255, 255, 100), font=font_body)
    
    # Visual Particle Glyphs
    for i in range(6):
        px = 400 + int((WIDTH - 440) * ((t * 2 + i * 0.2) % 1.0))
        py = 200 + int(12 * math.sin(t * 8 + i))
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=accent)

    # Bottom Log Panel (Cinematic Message Log)
    draw.rectangle([10, 250, WIDTH - 10, HEIGHT - 15], fill=(6, 8, 12), outline=(50, 60, 80), width=1)
    draw.rectangle([10, 250, WIDTH - 10, 272], fill=(16, 20, 30))
    draw.text((20, 254), "📜 シネマティック・エンジンログ (Kernel MessageLog)", fill=(180, 190, 210), font=font_log)

    for idx, log in enumerate(scene["log_lines"]):
        log_y = 280 + idx * 24
        # Gradual appearance
        if t >= idx * 0.25:
            color = (255, 255, 255) if idx == 0 else ((255, 215, 100) if idx == 1 else (150, 220, 255))
            draw.text((25, log_y), f"❯ {log}", fill=color, font=font_log)

    return img

def main():
    frames = []
    for scene in SCENES:
        dur = scene["duration"]
        for i in range(dur):
            frame = draw_scene(scene, i, dur)
            frames.append(frame)

    out_main = Path("demo_skill_eater.gif")
    out_assets = Path("assets/demo_skill_eater_story.gif")
    out_assets.parent.mkdir(parents=True, exist_ok=True)

    frames[0].save(
        out_main,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )
    print(f"Generated {out_main} ({out_main.stat().st_size // 1024} KB)")

    frames[0].save(
        out_assets,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
    )
    print(f"Generated {out_assets} ({out_assets.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    main()
