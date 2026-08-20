import math
import sys
from pathlib import Path

# 本物のPillowのパスを最優先に設定
sys.path = [p for p in sys.path if p not in ("", ".", "e:\\narou2", "E:\\narou2")]
sys.path.insert(0, r"C:\Users\keide\AppData\Roaming\Python\Python314\site-packages")
sys.path.insert(0, r"C:\Python314\Lib\site-packages")

from PIL import Image, ImageDraw, ImageFont

OUTPUT_PATH = Path("e:/narou2/demo_skill_eater.gif")
EMOTE_DIR = Path("e:/narou2/emote/PNG/Vector/Style 1")

WIDTH = 640
HEIGHT = 360
FPS = 10
FRAMES = []


def get_font(size=14):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


font_title = get_font(18)
font_body = get_font(13)
font_small = get_font(11)

scenes = [
    # Scene 1: スキャン解析 (Analyze)
    {
        "title": "【Aの世界：スキル喰い】 1. 深度解析（Scan & Analyze）",
        "actor": "主人公 (Lv.10)",
        "target": "ミダス重装執行官 (HP 180/180)",
        "action": "最底辺スキル《解析》を発動...",
        "emote": "emote_dots3.png",
        "log": "[SCAN] 弱点検出: 【Magic/Ice】 / スキル《鋼鉄の皮膚》検出 (喰らい成功率: 45%)",
        "color": (20, 25, 35),
        "duration": 18,
    },
    # Scene 2: 禁忌の《喰らい》発動 (Devour)
    {
        "title": "【Aの世界：スキル喰い】 2. 禁忌の強奪《喰らい（Devour）》",
        "actor": "主人公 (Lv.10)",
        "target": "ミダス重装執行官 (HP 40/180)",
        "action": "禁忌捕食を発動！ 敵から《鋼鉄の皮膚》を強奪！",
        "emote": "emote_star.png",
        "sound": "🔊 SE: clothBelt.ogg ➔ handleSmallLeather2.ogg",
        "log": "【捕食成功！】執行官から《鋼鉄の皮膚》を剥奪！ 敵は『空っぽ（Husk）』と化した！",
        "color": (35, 20, 25),
        "duration": 22,
    },
    # Scene 3: 連鎖熱爆発シナジー (Devour Combo)
    {
        "title": "【Aの世界：スキル喰い】 3. 胃袋内シナジー爆発 (Devour Synergy)",
        "actor": "主人公 (Lv.10)",
        "target": "風術師 (HP 60/60)",
        "action": "前回【Fire】× 今回【Wind】➔ 連鎖熱爆発！",
        "emote": "emote_exclamations.png",
        "sound": "🔊 SE: metalPot1.ogg (爆発衝撃音)",
        "log": "★【連鎖熱爆発！】爆風が業火を巻き込み全体に 40 の追撃大ダメージ！",
        "color": (45, 25, 15),
        "duration": 20,
    },
    # Scene 4: 魔導合成炉での変異融合 (Synthesis)
    {
        "title": "【Aの世界：スキル喰い】 4. 魔導キメラ合成 (Procedural Synthesis)",
        "actor": "アジト：魔導合成炉",
        "target": "素材：《初級火炎》×《思考加速》",
        "action": "2つのスキルを融合し、認可外の違法キメラを生成...",
        "emote": "emote_stars.png",
        "sound": "🔊 SE: metalPot2.ogg ➔ metalPot3.ogg",
        "log": "【プロシージャル合成成功！】《変異融合：業火の超思考》が誕生！（闇市場価値: 12,000アルド）",
        "color": (25, 20, 45),
        "duration": 22,
    },
    # Scene 5: メタシステム 世界法則上書き (Global Rule Override)
    {
        "title": "【Aの世界：スキル喰い】 5. 世界法則書き換え (ROOT Override)",
        "actor": "主人公 [ROOT権限]",
        "target": "世界法則：ダメージ倍率 (1.0 ➔ 2.0x)",
        "action": "生命力（最大HP -20）を代償に、世界システムを直接ハック！",
        "emote": "emote_idea.png",
        "sound": "🔊 SE: bookFlip3.ogg ➔ doorClose_4.ogg (重厚な確定音)",
        "log": "[SYSTEM ROOT] 世界法則 'damage_multiplier' を 2.0 に恒久改変！",
        "color": (15, 35, 30),
        "duration": 22,
    },
]


def render_frame(scene, progress):
    img = Image.new("RGB", (WIDTH, HEIGHT), scene["color"])
    draw = ImageDraw.Draw(img)

    # ヘッダーバー
    draw.rectangle([0, 0, WIDTH, 36], fill=(10, 12, 18))
    draw.text((15, 8), scene["title"], fill=(255, 215, 0), font=font_title)

    # メインバトル / ステータスボックス
    draw.rectangle(
        [20, 50, WIDTH - 20, 220], outline=(70, 80, 100), width=2, fill=(15, 18, 25)
    )

    # アクター・ターゲット情報
    draw.text((40, 65), f"👤 {scene['actor']}", fill=(120, 220, 255), font=font_title)
    draw.text((360, 65), f"🎯 {scene['target']}", fill=(255, 140, 140), font=font_title)

    # 行動アクションテキスト
    draw.text(
        (40, 110), f"⚡ ACTION: {scene['action']}", fill=(240, 240, 240), font=font_body
    )

    if "sound" in scene:
        draw.text((40, 140), scene["sound"], fill=(255, 180, 80), font=font_small)

    # エモートアイコン描画
    emote_file = scene.get("emote")
    if emote_file and (EMOTE_DIR / emote_file).exists():
        try:
            emo_img = Image.open(EMOTE_DIR / emote_file).convert("RGBA")
            emo_img = emo_img.resize((54, 54), Image.Resampling.LANCZOS)
            # ふわふわアニメーション
            y_offset = int(math.sin(progress * math.pi * 2) * 4)
            img.paste(emo_img, (530, 95 + y_offset), emo_img)
            draw.rectangle(
                [520, 85 + y_offset, 595, 160 + y_offset],
                outline=(255, 215, 0),
                width=1,
            )
        except Exception:
            pass

    # HP/MPゲージ演出（擬似）
    draw.rectangle([40, 180, 280, 195], fill=(30, 40, 50))
    draw.rectangle([40, 180, 240, 195], fill=(50, 180, 80))
    draw.text((45, 182), "HP 100/100  MP 50/50", fill=(255, 255, 255), font=font_small)

    draw.rectangle([360, 180, 600, 195], fill=(30, 40, 50))
    draw.rectangle([360, 180, 460, 195], fill=(220, 60, 60))
    draw.text((365, 182), "TARGET HP", fill=(255, 255, 255), font=font_small)

    # ログウィンドウ
    draw.rectangle(
        [20, 235, WIDTH - 20, HEIGHT - 20], fill=(5, 8, 12), outline=(50, 60, 80)
    )
    draw.text((35, 248), "LOG >", fill=(100, 200, 100), font=font_body)
    draw.text((85, 248), scene["log"], fill=(255, 255, 220), font=font_body)

    # プログレスバー（下部）
    bar_w = int((WIDTH - 40) * progress)
    draw.rectangle([20, HEIGHT - 12, 20 + bar_w, HEIGHT - 8], fill=(255, 215, 0))

    return img


print("Generating frames...")
for scene in scenes:
    dur = scene["duration"]
    for f in range(dur):
        prog = f / max(1, dur - 1)
        frame = render_frame(scene, prog)
        FRAMES.append(frame)

print(f"Saving {len(FRAMES)} frames to {OUTPUT_PATH}...")
FRAMES[0].save(
    OUTPUT_PATH, save_all=True, append_images=FRAMES[1:], duration=100, loop=0
)
print("GIF generated successfully!")
