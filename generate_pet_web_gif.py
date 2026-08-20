"""
Generate GIF showcasing Pet System & Web Client features.
"""

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
CYAN = (80, 255, 255)

scenes = [
    # Scene 1: Pet Contract & Management
    {
        "title": "ペット契約・管理システム",
        "subtitle": "モンスターを仲間に！契約・進化・融合で最強の相棒を育成",
        "panels": [
            {
                "name": "【契約可能なモンスター】",
                "skills": [
                    "🐌 かたつむり少女『グウェン』",
                    "   好感度: ★★★★☆ (親愛)",
                    "   契約コスト: 500G + 餌×3",
                    "   特性: 回復・支援・アイテム収集",
                    "   [Enter]で契約成立！",
                ],
                "color": PINK,
            },
            {
                "name": "【現在のパートナー】",
                "skills": [
                    "p 妹分シエル (第2進化: 天馬)",
                    "   Lv.24  HP: 420/420  MP: 180/180",
                    "   好感度: ◎ 至高の絆 (最大)",
                    "   AI: 攻撃支援 / 回復優先 / アイテム回収",
                    "   装備: 天使の弓 +5 / 羽衣ローブ",
                ],
                "color": GREEN,
            },
            {
                "name": "【ペットコマンド】",
                "skills": [
                    "[Shift+P] ペットメニュー開く",
                    "   1. 指示: 待機/追従/積極/支援",
                    "   2. 装備: アイテム渡し/外す",
                    "   3. 進化: 進化分岐選択/実行",
                    "   4. 融合: 他ペットと融合",
                    "   5. 解放: 野生に返す (レアアイテム)",
                ],
                "color": BLUE,
            },
        ],
        "info": "ペット上限: 3体 (魅力値で増加)  |  共鳴スキル: 絆Lv.で解放  |  餌やりで好感度上昇",
        "fx": [("particle", "💖", (15, 10), PINK), ("particle", "✨", (22, 10), GOLD)],
    },
    # Scene 2: Pet Evolution & Fusion
    {
        "title": "ペット進化・融合システム",
        "subtitle": "多段階進化と融合で無限のカスタマイズ",
        "panels": [
            {
                "name": "【シエル 進化ツリー】",
                "skills": [
                    "Lv.10 → 第1進化 分岐点",
                    "   ├─ 天馬 (飛行・光・回復) ← 現在",
                    "   ├─ 夜馬 (闇・速度・吸血)",
                    "   └─ 竜馬 (炎・攻撃・耐性)",
                    "",
                    "Lv.25 → 第2進化 (選択確定)",
                ],
                "color": PURPLE,
            },
            {
                "name": "【融合システム】",
                "skills": [
                    "ベース: シエル (天馬 Lv.24)",
                    "素材: グウェン (かたつむり Lv.18)",
                    "    ↓ 融合実行 ↓",
                    "結果: 『天使のグウェン』",
                    "継承: 回復光線 + 粘液バリア",
                    "新特性: 空飛ぶ治癒士",
                ],
                "color": ORANGE,
            },
            {
                "name": "【ペット固有スキル】",
                "skills": [
                    "シエル: 『天翔の癒し』 (範囲回復)",
                    "          『光の加護』 (パーティバフ)",
                    "グウェン: 『粘液バリア』 (物理軽減)",
                    "          『アイテムハンター』 (ドロップ↑)",
                    "融合後: 両方のスキル使用可能!",
                ],
                "color": CYAN,
            },
        ],
        "info": "進化素材: 進化の宝珠/特定アイテム/クエスト  |  融合は元に戻せません  |  [E]:進化 [F]:融合",
        "fx": [
            ("particle", "🌟", (28, 6), PURPLE),
            ("particle", "🔮", (35, 12), ORANGE),
        ],
    },
    # Scene 3: Web Client & Browser Play
    {
        "title": "Webブラウザ版クライアント (Web Client)",
        "subtitle": "インストール不要！ブラウザでフル機能プレイ",
        "panels": [
            {
                "name": "【Web版 特徴】",
                "skills": [
                    "✅ ターミナル版と完全同期",
                    "✅ WebSocket リアルタイム通信",
                    "✅ スマホ/タブレット対応 (タッチ操作)",
                    "✅ ローカルLAN でマルチデバイス",
                    "✅ テーマカスタマイズ (CSS)",
                    "✅ PWA 対応 (オフライン・インストール)",
                ],
                "color": BLUE,
            },
            {
                "name": "【起動手順】",
                "skills": [
                    "1. python main.py  (ゲーム起動)",
                    "2. メニューで [1] ゲーム開始",
                    "3. 別ターミナル: python web_server.py",
                    "4. ブラウザで http://localhost:8080",
                    "5. スマホなら: http://<PCのIP>:8080",
                    "",
                ],
                "color": GREEN,
            },
            {
                "name": "【Web版 UI】",
                "skills": [
                    "左: マップビューポート (タッチ移動)",
                    "右: ステータス/インベントリ/ログ",
                    "下: バーチャルキーパッド/コマンド",
                    "メニュー: ☰ ハンバーガーで全機能",
                    "設定: 🌓 ダーク/ライトテーマ切替",
                    "チャット: 💬 他プレイヤーと会話 (将来)",
                ],
                "color": ORANGE,
            },
        ],
        "info": "Web版は game.py と同一ロジック使用  |  web/theme.css で見た目変更可能  |  ポート変更: config.yaml",
        "fx": [("particle", "🌐", (42, 8), CYAN), ("particle", "📱", (45, 10), BLUE)],
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
                    if "解放" in skill
                    or "★" in skill
                    or "結果" in skill
                    or "新特性" in skill
                    or "継承" in skill
                    else (
                        GREEN
                        if "✅" in skill or "現在" in skill
                        else (ORANGE if "←" in skill or "↓" in skill else TEXT_WHITE)
                    )
                )
                if "空" in skill or "飛行" in skill:
                    skill_color = CYAN
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
out_gif = "demo_pet_web.gif"
frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=1200, loop=0)
print(f"Generated {out_gif} with {len(frames)} frames.")
