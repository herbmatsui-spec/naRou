"""
Generate 24 High-Quality Interactive HTML Demo Scenes for naRou: Masterpiece Edition.

Each scene reflects a REAL, currently-implemented system of the game
(data-driven from data/*.yaml + the *_system.py managers). A single SCENES
data structure drives both the 24 individual scene HTML files and the
grand gallery, so they never drift apart.

Usage:
    python generate_24_scenes.py
"""
from __future__ import annotations

import json
import os

OUT_DIR = "demos"

# (filename, title, desc, icon, grid(5x10), log)
SCENES = [
    (
        "scene_01_base_home.html",
        "1. 拠点・我が家 (洞窟の拠点)",
        "仲間シエルと暮らす拠点、SHA256検証セーブで冒険の準備",
        "🏡",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "▫️", "▫️", "📦", "▫️", "▫️", "▫️", "💾", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "▫️", "🛏️", "▫️", "🧱"],
            ["🧱", "▫️", "▫️", "▫️", "🍞", "▫️", "▫️", "▫️", "🪙", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "拠点🏡でシエル👧と共に過ごし、SHA256検証付きセーブ💾で冒険の準備を整えた！",
    ),
    (
        "scene_02_adventurers_guild.html",
        "2. 冒険者ギルド (ヴェルニス)",
        "ランク昇格と日替わり依頼を受ける冒険者の拠点",
        "🏰",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "📜", "▫️", "▫️", "🏆", "▫️", "▫️", "👤", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "▫️", "💰", "▫️", "🧱"],
            ["🧱", "▫️", "▫️", "🗡️", "▫️", "▫️", "🛡️", "▫️", "⚔️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "冒険者ギルド🏰で日替わり依頼📜を受注！ランク novice→member→veteran→officer→leader への昇格を目指す。",
    ),
    (
        "scene_03_job_system.html",
        "3. ジョブシステム (職業転職)",
        "見習いから剣聖・大賢者へ。専用スキルを解放",
        "⚔️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "📘", "▫️", "▫️", "🗡️", "▫️", "✨", "▫️", "🔮", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "⚔️", "▫️", "📜", "🧱"],
            ["🧱", "▫️", "▫️", "🔥", "▫️", "▫️", "❄️", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ジョブ転職！戦士🗡️の専用スキル『シールドバッシュ』、剣聖⚔️の『居合術』、大賢者🔮の『メテオ』を解放。",
    ),
    (
        "scene_04_skill_tree.html",
        "4. スキルツリー (剣術/魔法/体術)",
        "3系統・9ノード。スキルポイントで習得",
        "🌳",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "⚔️", "🔘", "▫️", "🔮", "🔘", "▫️", "🥊", "🔘", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "⭐", "▫️", "📊", "🧱"],
            ["🧱", "▫️", "▫️", "🔗", "▫️", "▫️", "🔗", "▫️", "▫️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "スキルツリー🌳を開放：剣術⚔️・魔法🔮・体術🥊の3系統9ノードをスキルポイントで段階習得。",
    ),
    (
        "scene_05_skill_fusion.html",
        "5. スキル合成 (Skill Fusion)",
        "スキル同士を合成し新たな上位スキルを生む",
        "🔥",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🔮", "➕", "🔥", "▫️", "▫️", "💥", "▫️", "🛡️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "✝️", "▫️", "🔗", "🧱"],
            ["🧱", "▫️", "▫️", "🗡️", "➕", "🔮", "▫️", "▫️", "⚡", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "スキル合成🔥！『火炎爆砕合成』でメガファイアボール💥、『聖光撃合成』で聖撃✝️、魔導剣⚡セットを生み出した。",
    ),
    (
        "scene_06_skill_evolution_awakening.html",
        "6. スキル進化・覚醒",
        "熟練→極意→神速の剣聖。竜殺しの覚醒",
        "✨",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🗡️", "▫️", "➡️", "▫️", "⚔️", "▫️", "➡️", "▫️", "🌟"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🐉", "▫️", "✨", "▫️", "🔥"],
            ["🧱", "▫️", "▫️", "📈", "▫️", "▫️", "💥", "▫️", "▫️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "スキル進化『剣術の進化の道』→『神速の剣聖』🌟！さらに『竜殺しの覚醒』で竜へのダメージが2倍に。",
    ),
    (
        "scene_07_skill_meta.html",
        "7. 専門化・継承・共鳴・転移",
        "火炎魔専門化、血統継承、炎騎士セット、転移",
        "🔗",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🔥", "▫️", "🩸", "▫️", "🛡️", "▫️", "🔗", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "✨", "▫️", "📜", "🧱"],
            ["🧱", "▫️", "▫️", "⚡", "▫️", "▫️", "🌟", "▫️", "💠", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "火炎魔導専門化🔥・血統スキル継承🩸・炎の騎士セット🛡️・急所看破の転移🔗を習得し戦術を広げる。",
    ),
    (
        "scene_08_pet_contract.html",
        "8. ペット契約 (Pet Contract)",
        "標準契約・魂の絆契約。絆で進化・救出解放",
        "🤝",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🐶", "▫️", "💗", "▫️", "🐱", "▫️", "🤝", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🔗", "▫️", "💞", "▫️", "🧱"],
            ["🧱", "▫️", "▫️", "📊", "▫️", "▫️", "🏅", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ペット契約🤝！標準契約🤝と魂の絆契約💗で子犬🐶と絆を深め、進化ボーナスと救出スキルを解放。",
    ),
    (
        "scene_09_pet_evolution.html",
        "9. ペット進化 (Pet Evolution)",
        "子犬→猟犬/警備犬/魔導猟犬、子猫→黒豹",
        "🐕",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🐶", "🐕", "🐺", "▫️", "▫️", "🐱", "🐆", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "▫️", "✨", "▫️", "🔥", "🧱"],
            ["🧱", "▫️", "▫️", "💗", "▫️", "▫️", "📜", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ペット進化🐕！子犬🐶→猟犬🐕→警備犬🐺、子猫🐱→黒豹🐆へ多段進化し能力が飛躍。",
    ),
    (
        "scene_10_pet_fusion.html",
        "10. ペット融合 (Pet Fusion)",
        "ハウンド+ドレイク→ドラゴンハウンド etc",
        "🐉",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🐕", "➕", "🐉", "▫️", "▫️", "🦄", "➕", "🐎", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "💥", "▫️", "🦄", "🪽", "🧱"],
            ["🧱", "▫️", "▫️", "🔬", "▫️", "▫️", "⚗️", "▫️", "✨", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ペット融合🐉！ハウンド×ドレイクでドラゴンハウンド🐉🐕、ユニコーン×ペガサスでユニコーンペガサス🦄🪽を誕生。",
    ),
    (
        "scene_11_procedural_dungeon.html",
        "11. 自動生成ダンジョン",
        "8舞台×3次元(material/ethereal/void)の垂直世界",
        "🗺️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🌲", "▫️", "🏚️", "▫️", "🌋", "▫️", "❄️", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🕳️", "▫️", "🌌", "▫️", "🧱"],
            ["🧱", "▫️", "🗺️", "▫️", "▫️", "🔄", "▫️", "⬇️", "▫️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "自動生成ダンジョン🗺️！街/森/洞窟/遺跡/火山/雪原/沼/深淵の8舞台と material/ethereal/void の3次元を探索。",
    ),
    (
        "scene_12_combat_system.html",
        "12. 戦闘システム (Combat)",
        "命中率・クリティカル・6元素・状態異常",
        "⚔️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "💥", "▫️", "▫️", "🔥", "▫️", "❄️", "▫️", "⚡", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🗡️", "▫️", "👹", "▫️", "🧱"],
            ["🧱", "▫️", "🩸", "▫️", "☠️", "▫️", "😵", "▫️", "💢", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "戦闘⚔️！命中率 75+DEX-DEF、クリティカル補正、火/冷/雷/闇/混沌/魔の6元素と毒🩸・麻痺☠️・出血💢を実装。",
    ),
    (
        "scene_13_monsters_ai.html",
        "13. モンスター＆AI",
        "ぷち〜レッドドラゴン、6種のAI行動",
        "👹",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🍮", "▫️", "👺", "▫️", "👹", "▫️", "🐂", "▫️", "🧱"],
            ["🧱", "▫️", "💀", "▫️", "🐉", "▫️", "🧙", "▫️", "👧", "🧱"],
            ["🧱", "▫️", "🤖", "▫️", "🏃", "▫️", "🔮", "▫️", "🛡️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "モンスター👹は6種AIで行動：ぷち🍮・ゴブリン👺・オーク👹・ミノタウロス🐂・リッチ💀・レッドドラゴン🐉。",
    ),
    (
        "scene_14_gods_faith.html",
        "14. 神々と信仰 (Gods & Faith)",
        "5柱の神とエーテル病の生存管理",
        "⛩️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "💚", "▫️", "🌬️", "▫️", "⚙️", "▫️", "🔥", "🧱", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🌾", "▫️", "✨", "▫️", "🧱"],
            ["🧱", "▫️", "🤒", "▫️", "▫️", "☣️", "▫️", "▫️", "🍞", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "信仰⛩️：癒やしのジュア💚・風のルルウィ🌬️・機械のマニ⚙️・元素のイツパロトル🔥・収穫のクミロミ🌾。エーテル病🤒に注意。",
    ),
    (
        "scene_15_faction_war.html",
        "15. 派閥戦争 (Faction War)",
        "3派閥の勢力値変動と噂・評判",
        "⚔️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🛡️", "▫️", "⛪", "▫️", "🔥", "▫️", "⚔️", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "📊", "▫️", "💬", "▫️", "🧱"],
            ["🧱", "▫️", "🤝", "▫️", "⚔️", "▫️", "😠", "▫️", "▫️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "派閥戦争⚔️：ガルド王国🛡️・ルミエスト教会⛪・シャドウハンド🔥が勢力値を奪い合い、噂💬が評判を動かす。",
    ),
    (
        "scene_16_guilds_detail.html",
        "16. 魔術士・盗賊ギルド",
        "lumiestの魔術士ギルドとderphyの盗賊ギルド",
        "🔮",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🔮", "▫️", "📘", "▫️", "🗝️", "▫️", "🦹", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🌑", "▫️", "💰", "▫️", "🧱"],
            ["🧱", "▫️", "✨", "▫️", "▫️", "🥷", "▫️", "🔓", "▫️", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "魔術士ギルド🔮(lumiest)で魔法研究、盗賊ギルド🦹(derphy)で暗影の帳🥷と闇取引💰を展開。",
    ),
    (
        "scene_17_reincarnation.html",
        "17. 輪廻転生 (Reincarnation)",
        "Lv50で転生、カルマと記憶の欠片を継承",
        "🔄",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🔄", "▫️", "💎", "▫️", "🧠", "▫️", "📜", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "⚖️", "▫️", "✨", "▫️", "🧱"],
            ["🧱", "▫️", "🔁", "▫️", "📈", "▫️", "🏅", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "輪廻転生🔄！Lv50で転生し、カルマ⚖️と記憶の欠片💎を継承して能力ボーナスを獲得。",
    ),
    (
        "scene_18_ng_plus.html",
        "18. ニューゲーム+ (NG+)",
        "周回ごとに敵強化・ドロップ増・カルマ変動",
        "💫",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "💫", "▫️", "📈", "▫️", "🔁", "▫️", "💀", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "💰", "▫️", "🎁", "▫️", "🧱"],
            ["🧱", "▫️", "⚖️", "▫️", "▫️", "🔥", "▫️", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ニューゲーム+💫！周回毎に敵ステータス+15%/ドロップ+10% scaling、カルマ⚖️も変動する。",
    ),
    (
        "scene_19_meta_progression.html",
        "19. メタ進行・記憶の欠片",
        "複数周回の目標と運命の特異点(サイクル修正)",
        "🧩",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🧩", "▫️", "🏆", "▫️", "📜", "▫️", "🌟", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🔮", "▫️", "🎲", "▫️", "🧱"],
            ["🧱", "▫️", "📊", "▫️", "💪", "▫️", "🧠", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "メタ進行🧩：『深淵の踏破者』『輪廻の超越者』等の目標と、運命の特異点🌟(サイクル修正)を獲得。",
    ),
    (
        "scene_20_storyteller.html",
        "20. ストーリーテラー (Storyteller)",
        "自動生成ストーリー「ゴブリンの侵略」と分岐",
        "📖",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "📖", "▫️", "👺", "▫️", "🏰", "▫️", "⚔️", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🔀", "▫️", "🕊️", "▫️", "🧱"],
            ["🧱", "▫️", "📜", "▫️", "🏅", "▫️", "👑", "▫️", "🔚", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ストーリーテラー📖：自動生成『ゴブリンの侵略』。救出か急襲かの選択🔀で和平使者🕊️か覇者👑の結末へ。",
    ),
    (
        "scene_21_procedural_quests.html",
        "21. 自動生成クエスト",
        "8アーキ型×6難易度×5報酬表の連鎖クエスト",
        "📜",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🗡️", "▫️", "💎", "▫️", "🛡️", "▫️", "🚚", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "📋", "▫️", "🔗", "▫️", "🧱"],
            ["🧱", "▫️", "🎯", "▫️", "🏅", "▫️", "💰", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "自動生成クエスト📜：討伐/採取/護衛/探索/ボス/救出/配達/発掘の8型×序〜深淵6難易度、連鎖クエスト🔗に対応。",
    ),
    (
        "scene_22_save_migration.html",
        "22. セーブ＆マイグレーション",
        "SHA256+gzipの商用セーブと世代バックアップ",
        "💾",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "💾", "▫️", "🔐", "▫️", "🗜️", "▫️", "📦", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "♻️", "▫️", "📥", "▫️", "🧱"],
            ["🧱", "▫️", "🗂️", "▫️", "🔄", "▫️", "🛡️", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "セーブ💾はSHA256検証+gzip圧縮(v2.0.0)、世代バックアップ3つで破損時自動復旧。マイグレーション♻️で互換維持。",
    ),
    (
        "scene_23_balance_simulator.html",
        "23. バランス検証 (Balance Simulator)",
        "100試行の戦闘シミュレーションで自動検証",
        "📊",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "📊", "▫️", "🎲", "▫️", "⚔️", "▫️", "💥", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🍮", "▫️", "👹", "▫️", "🧱"],
            ["🧱", "▫️", "✅", "▫️", "📄", "▫️", "🌐", "▫️", "⭐", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "バランス検証📊：tests/balance_simulator.py で100試行シミュレーション、勝率を基準値と照合し balance_report.html を出力。",
    ),
    (
        "scene_24_ecs_architecture.html",
        "24. ECSアーキテクチャ・フィナーレ",
        "SystemManager/SystemCoordinator、登録30システム・デュアルUI",
        "🏗️",
        [
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
            ["🧱", "🧩", "▫️", "🔗", "▫️", "🧠", "▫️", "⚙️", "▫️", "🧱"],
            ["🧱", "▫️", "🧙", "👧", "▫️", "🖥️", "▫️", "🌐", "▫️", "🧱"],
            ["🧱", "▫️", "📐", "▫️", "🔧", "▫️", "🧩", "▫️", "🏆", "🧱"],
            ["🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱", "🧱"],
        ],
        "ECSアーキテクチャ🏗️：SystemManager/SystemCoordinator が30の疎結合システムを依存解決で管理。tcod🖥️とWeb🌐のデュアルUI。",
    ),
]


def build_grid_html(grid):
    cells = []
    for row in grid:
        for char in row:
            if char == "🧱":
                cells.append('<div class="tile tile-wall">🧱</div>')
            elif char == "▫️":
                cells.append('<div class="tile tile-floor">▫️</div>')
            else:
                cells.append(f'<div class="tile anim-pulse">{char}</div>')
    return "\n            ".join(cells)


SCENE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>naRou Scene Demo - {title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', 'Noto Sans JP', sans-serif;
            background: #070913;
            color: #ffffff;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
            background-image: radial-gradient(circle at top center, #1b2038, #070913);
        }}
        .stage-box {{
            width: 820px;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            overflow: hidden;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .grid-map {{
            display: grid;
            grid-template-columns: repeat(10, 1fr);
            gap: 4px;
            background: #030712;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.08);
            font-size: 32px;
            user-select: none;
        }}
        .tile {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 48px;
            border-radius: 6px;
        }}
        .tile-wall {{ background: rgba(50, 40, 40, 0.5); }}
        .tile-floor {{ color: #4b5563; font-size: 16px; }}
        .anim-pulse {{ animation: pop 1.2s infinite alternate ease-in-out; }}
        @keyframes pop {{
            0% {{ transform: scale(1.0); }}
            100% {{ transform: scale(1.2); }}
        }}
    </style>
</head>
<body>
    <div class="stage-box">
        <div class="flex justify-between items-center border-b border-slate-700 pb-3">
            <div class="flex items-center gap-3">
                <span class="text-3xl">{icon}</span>
                <div>
                    <h1 class="text-xl font-bold text-sky-400">{title}</h1>
                    <p class="text-xs text-slate-400">{desc}</p>
                </div>
            </div>
            <span class="bg-sky-500/20 text-sky-300 px-3 py-1 rounded-full text-xs font-semibold">Scene Demo</span>
        </div>

        <div class="grid-map">
            {grid_html}
        </div>

        <div class="bg-slate-900 border border-slate-800 rounded-lg p-3 text-sm flex items-center justify-between">
            <span class="text-yellow-300 font-medium">📜 {log}</span>
            <span class="text-xs text-slate-500">naRou: Masterpiece Edition</span>
        </div>
    </div>
</body>
</html>
"""


def generate_scene_files():
    os.makedirs(OUT_DIR, exist_ok=True)
    for filename, title, desc, icon, grid, log in SCENES:
        html = SCENE_TEMPLATE.format(
            title=title,
            desc=desc,
            icon=icon,
            grid_html=build_grid_html(grid),
            log=log,
        )
        with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Generated {len(SCENES)} scene HTML files in {OUT_DIR}/")


def gallery_scenes_js():
    data = [
        {
            "id": idx + 1,
            "title": title,
            "desc": desc,
            "icon": icon,
            "log": log,
            "grid": grid,
        }
        for idx, (_, title, desc, icon, grid, log) in enumerate(SCENES)
    ]
    return json.dumps(data, ensure_ascii=False)


GALLERY_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>naRou: Masterpiece Edition - 24 Scenes Grand Showcase</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', 'Noto Sans JP', sans-serif;
            background-color: #060810;
            color: #f8fafc;
            margin: 0;
            padding: var(--spacing-4);
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            background-image: radial-gradient(circle at top right, #1a1630, #060810);
        }}

        .gallery-container {{
            width: 1100px;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            box-shadow: 0 25px 70px rgba(0, 0, 0, 0.85);
            padding: var(--spacing-6);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .screen-preview {{
            background: #020617;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            height: 380px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            position: relative;
            box-shadow: inset 0 0 30px rgba(0,0,0,0.8);
        }}

        .grid-matrix {{
            display: grid;
            grid-template-columns: repeat(10, 1fr);
            gap: 6px;
            font-size: 32px;
            user-select: none;
        }}

        .cell {{
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}

        .cell-wall {{ background: rgba(50, 40, 40, 0.4); }}
        .cell-floor {{ color: #475569; font-size: 16px; }}
        .cell-anim {{
            transform: scale(1.1);
            filter: drop-shadow(0 0 8px rgba(255,255,255,0.4));
            animation: pulse 1.2s infinite alternate ease-in-out;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1.25); }}
        }}

        .scene-card-btn {{
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .scene-card-btn:hover, .scene-card-btn.active {{
            background: #38bdf8;
            color: #0f172a;
            font-weight: bold;
            border-color: #7dd3fc;
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>

    <div class="gallery-container">
        <!-- Header -->
        <div class="flex justify-between items-center border-b border-slate-700/80 pb-4">
            <div class="flex items-center gap-3">
                <span class="text-3xl">👑</span>
                <div>
                    <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-amber-300">
                        naRou: Masterpiece Edition — 全24シーン・グランドギャラリー
                    </h1>
                    <p class="text-xs text-slate-400">24種類の個別HTMLシーンを切り替えて鑑賞できるデモ展示（実装済みシステム紹介）</p>
                </div>
            </div>
            <div class="flex gap-2">
                <button id="btnAutoPlay" class="bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold px-4 py-2 rounded-xl text-xs shadow-lg hover:brightness-110 transition">
                    ▶️ オートツアー開始 (Auto Play)
                </button>
            </div>
        </div>

        <!-- Screen Preview -->
        <div class="screen-preview">
            <div class="absolute top-4 left-6 flex items-center gap-3">
                <span class="text-2xl" id="curIcon">🏡</span>
                <div>
                    <h2 class="text-lg font-bold text-sky-300" id="curTitle"></h2>
                    <p class="text-xs text-slate-400" id="curDesc"></p>
                </div>
            </div>
            <span class="absolute top-4 right-6 bg-sky-500/20 text-sky-300 text-xs px-3 py-1 rounded-full font-bold" id="curBadge">
                Scene 1 / 24
            </span>

            <div class="grid-matrix mt-6" id="matrix">
                <!-- Javascript fills matrix -->
            </div>

            <div class="absolute bottom-4 left-6 right-6 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2 flex justify-between items-center text-sm">
                <span class="text-yellow-300 font-medium" id="curLog"></span>
                <span class="text-xs text-slate-500 font-mono">naRou 24-Scene Engine</span>
            </div>
        </div>

        <!-- 24 Scene Selection Grid -->
        <div>
            <div class="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">シーン一覧 (全24シーンを選択して切り替え)</div>
            <div class="grid grid-cols-6 gap-2" id="sceneList">
                <!-- Javascript generates 24 scene buttons -->
            </div>
        </div>
    </div>

    <script>
        const scenes = {scenes_js};

        let currentIndex = 0;
        let autoPlayTimer = null;

        function renderScene(idx) {{
            currentIndex = idx;
            const s = scenes[idx];
            document.getElementById('curIcon').innerText = s.icon;
            document.getElementById('curTitle').innerText = s.title;
            document.getElementById('curDesc').innerText = s.desc;
            document.getElementById('curBadge').innerText = `Scene ${{s.id}} / 24`;
            document.getElementById('curLog').innerText = `📜 ${{s.log}}`;

            const matrix = document.getElementById('matrix');
            matrix.innerHTML = '';
            s.grid.forEach(row => {{
                row.forEach(char => {{
                    const div = document.createElement('div');
                    div.className = 'cell';
                    if (char === '🧱') div.classList.add('cell-wall');
                    else if (char === '▫️') div.classList.add('cell-floor');
                    else div.classList.add('cell-anim');
                    div.innerText = char;
                    matrix.appendChild(div);
                }});
            }});

            // Update active button
            document.querySelectorAll('.scene-card-btn').forEach((btn, i) => {{
                if (i === idx) btn.classList.add('active');
                else btn.classList.remove('active');
            }});
        }}

        // Initialize 24 buttons
        const list = document.getElementById('sceneList');
        scenes.forEach((s, idx) => {{
            const btn = document.createElement('button');
            btn.className = 'scene-card-btn';
            btn.innerHTML = `<span>${{s.icon}}</span> <span>${{s.title}}</span>`;
            btn.id = `btnScene_${{s.id}}`;
            btn.onclick = () => {{
                if (autoPlayTimer) clearInterval(autoPlayTimer);
                renderScene(idx);
            }};
            list.appendChild(btn);
        }});

        // Auto Play
        document.getElementById('btnAutoPlay').addEventListener('click', () => {{
            if (autoPlayTimer) {{
                clearInterval(autoPlayTimer);
                autoPlayTimer = null;
                document.getElementById('btnAutoPlay').innerText = "▶️ オートツアー開始 (Auto Play)";
            }} else {{
                document.getElementById('btnAutoPlay').innerText = "⏸️ 一時停止 (Pause)";
                autoPlayTimer = setInterval(() => {{
                    let nextIdx = (currentIndex + 1) % scenes.length;
                    renderScene(nextIdx);
                }}, 1500);
            }}
        }});

        renderScene(0);
    </script>
</body>
</html>
"""


def generate_gallery():
    os.makedirs(OUT_DIR, exist_ok=True)
    html = GALLERY_TEMPLATE.format(scenes_js=gallery_scenes_js())
    out_path = os.path.join(OUT_DIR, "gallery_24_scenes.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated {out_path}")


if __name__ == "__main__":
    generate_scene_files()
    generate_gallery()
