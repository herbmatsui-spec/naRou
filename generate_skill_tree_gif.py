"""
Generate GIF showcasing Skill Tree & Job System features.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

W, H = 840, 500
BG_DARK = (10, 12, 18)
PANEL_BG = (16, 20, 32)
PANEL_BORDER = (45, 60, 90)
TEXT_WHITE = (240, 245, 255)
TEXT_MUTED = (140, 155, 180)
GOLD = (255, 215, 0)
GREEN = (100, 255, 100)
BLUE = (100, 200, 255)
PURPLE = (180, 120, 255)
PINK = (255, 160, 200)
ORANGE = (255, 180, 60)
RED = (255, 80, 80)

scenes = [
    # Scene 1: Skill Tree Overview
    {
        "title": "スキルツリー画面 (Shift+S)",
        "subtitle": "70種類以上のスキルから自由にビルド構築",
        "panels": [
            {
                "name": "【戦士の道】",
                "skills": [
                    "剣術 Lv.5 ████████░░",
                    "重装備 Lv.3 █████░░░░░",
                    "盾防御 Lv.4 ███████░░░",
                    "戦闘狂 Lv.2 ████░░░░░░",
                    "戦吼 Lv.1 ██░░░░░░░░",
                ],
                "color": ORANGE,
            },
            {
                "name": "【魔法の道】",
                "skills": [
                    "火炎魔法 Lv.4 ███████░░░",
                    "氷結魔法 Lv.3 █████░░░░░",
                    "雷撃魔法 Lv.2 ████░░░░░░",
                    "治癒魔法 Lv.5 ████████░░",
                    "召喚魔法 Lv.1 ██░░░░░░░░",
                ],
                "color": BLUE,
            },
            {
                "name": "【特殊・神秘】",
                "skills": [
                    "錬金術 Lv.3 █████░░░░░",
                    "鑑定眼 Lv.4 ███████░░░",
                    "交渉術 Lv.2 ████░░░░░░",
                    "幸運 Lv.3 █████░░░░░",
                    "神秘学 Lv.1 ██░░░░░░░░",
                ],
                "color": PURPLE,
            },
        ],
        "info": "SP: 42  |  獲得: レベルアップ/クエスト/読書  |  [Enter]:習得 [Shift+Click]:詳細",
        "fx": [],
    },
    # Scene 2: Job System & Class Change
    {
        "title": "ジョブシステム・転職メニュー (J)",
        "subtitle": "15種類の職業から選択・マルチクラス対応",
        "panels": [
            {
                "name": "【基礎職】",
                "skills": [
                    "ウォーリア ████████████ Lv.15",
                    "メイジ ██████████░░ Lv.12",
                    "シーフ ████████░░░░ Lv.10",
                    "クレリック ██████░░░░░░ Lv.8",
                    "レンジャー ████░░░░░░░░ Lv.6",
                ],
                "color": GREEN,
            },
            {
                "name": "【上位職 (転職済)】",
                "skills": [
                    "パラディン ★ 解放済",
                    "アークメイジ ★ 解放済",
                    "アサシン ★ 解放済",
                    "ハイプリースト ░ 条件未達",
                    "スナイパー ░ 条件未達",
                ],
                "color": GOLD,
            },
            {
                "name": "【マスター職 (NG+)】",
                "skills": [
                    "神聖騎士王 ░ NG+1で解放",
                    "賢者の塔 ░ NG+1で解放",
                    "影の支配者 ░ NG+1で解放",
                ],
                "color": PURPLE,
            },
        ],
        "info": "現在: ウォーリア Lv.15 → パラディン転職可能!  |  ジョブポイント: 28  |  [Enter]:転職実行",
        "fx": [("particle", "✨", (35, 8), GOLD), ("particle", "★", (42, 8), GOLD)],
    },
    # Scene 3: Skill Fusion & Evolution
    {
        "title": "スキル融合・覚醒・進化システム",
        "subtitle": "スキル同士を融合させて新たな力を生み出す",
        "panels": [
            {
                "name": "【スキル融合 実験中】",
                "skills": [
                    "剣術 Lv.5 + 火炎魔法 Lv.4",
                    "    ↓ 融合実行 ↓",
                    "『炎剣・業火斬』 解放!",
                    "消費SP: 15 + 融合触媒×1",
                    "成功率: 78% (熟練度ボーナス+5%)",
                ],
                "color": ORANGE,
            },
            {
                "name": "【覚醒スキル】",
                "skills": [
                    "条件: 基礎スキルLv.5 + 特定クエスト",
                    "神威・次元斬 (剣術覚醒)",
                    "星屑の杖 (魔法覚醒)",
                    "影縫い (特殊覚醒)",
                    "各覚醒で専用エフェクト獲得",
                ],
                "color": PURPLE,
            },
            {
                "name": "【継承スキル (NG+)】",
                "skills": [
                    "輪廻転生で継承可能なレガシー",
                    "『不屈の闘志』 HP+20% 防御+15%",
                    "『魔力の奔流』 MP+30% 詠唱-20%",
                    "『幸運の女神の微笑み』 ドロップ+50%",
                    "次回プレイで即座に使用可能",
                ],
                "color": GOLD,
            },
        ],
        "info": "融合レシピ: 図鑑/ギルド/古文書で発見  |  失敗時: 素材消失なし SPのみ消費  |  [F]:融合 [A]:覚醒",
        "fx": [
            ("particle", "✧", (25, 12), PURPLE),
            ("particle", "🔥", (28, 6), ORANGE),
        ],
    },
]

frames = []

for sc_idx, sc in enumerate(scenes):
    for sub in range(5):
        img = Image.new("RGB", (W, H), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle(
            [(12, 10), (W - 12, 48)], fill=PANEL_BG, outline=PANEL_BORDER, width=2
        )
        draw.text((24, 16), "naRou: Masterpiece Edition", fill=GOLD)
        draw.text((24, 34), sc["title"], fill=TEXT_WHITE)
        draw.text((420, 34), sc["subtitle"], fill=TEXT_MUTED)

        # Three panel columns
        panel_w = 260
        panel_h = 380
        start_x = 20
        gap = 14

        for p_idx, panel in enumerate(sc["panels"]):
            px = start_x + p_idx * (panel_w + gap)
            py = 70

            # Panel background
            draw.rectangle(
                [(px, py), (px + panel_w, py + panel_h)],
                fill=PANEL_BG,
                outline=panel["color"],
                width=2,
            )

            # Panel title
            draw.rectangle([(px, py), (px + panel_w, py + 32)], fill=panel["color"])
            draw.text((px + 10, py + 6), panel["name"], fill=BG_DARK)

            # Skills list
            for s_idx, skill in enumerate(panel["skills"]):
                sy = py + 42 + s_idx * 30
                skill_color = (
                    GOLD
                    if "解放" in skill or "★" in skill
                    else (GREEN if "Lv." in skill and "█" in skill else TEXT_WHITE)
                )
                if "↓" in skill:
                    skill_color = ORANGE
                if "条件" in skill or "継承" in skill:
                    skill_color = TEXT_MUTED
                draw.text((px + 12, sy), skill, fill=skill_color)

        # Bottom info bar
        info_y = H - 50
        draw.rectangle(
            [(12, info_y), (W - 12, H - 12)],
            fill=(20, 26, 40),
            outline=PANEL_BORDER,
            width=1,
        )
        draw.text((24, info_y + 12), sc["info"], fill=GOLD)

        # FX particles
        for fx_type, fx_val, (fx_x, fx_y), fx_col in sc.get("fx", []):
            draw.text((fx_x * 20, fx_y * 20 + sub * 3), fx_val, fill=fx_col)

        frames.append(img)

# Save
out_gif = "demo_skill_tree.gif"
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=1200, loop=0)
print(f"Generated {out_gif} with {len(frames)} frames.")
