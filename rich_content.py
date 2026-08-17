"""
Elona Roguelike Clone - Rich Game Content, Items, Unique NPCs, & Dialogue
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import random


# アイテムエンチャント (Elona名物)
ENCHANT_FIRE_DMG = "それは火炎属性の追加ダメージを与える"
ENCHANT_RESIST_COLD = "それは冷気への耐性を授ける"
ENCHANT_CHAOS = "それは混沌の渦を巻き起こす"
ENCHANT_LUCK = "それは幸運の女神の加護をもたらす"
ENCHANT_LIFE = "それは生命力を吸い取る"


@dataclass
class NPCData:
    """NPCの詳細定義 (ユニークNPC・商人・ガードなど)"""
    name: str
    char: str
    color: Tuple[int, int, int]
    role: str
    dialogues: List[str]
    shop_inventory: Optional[List[str]] = None


# Elonaを象徴するNPCたち
NPCS_CATALOG = {
    "gwen": NPCData(
        name="かたつむり少女『グウェン』",
        char="g",
        color=(255, 180, 220),
        role="unique",
        dialogues=[
            "「あ、冒険者さん！こんにちは〜！」",
            "「グウェン、お散歩中なの！」",
            "「塩…塩だけは投げないでね…？」",
            "「えへへ、お花きれいだね！」"
        ]
    ),
    "beggar": NPCData(
        name="乞食",
        char="b",
        color=(180, 150, 100),
        role="neutral",
        dialogues=[
            "「金貨を…恵んでくだせぇ…」",
            "「酒が…酒が飲みたい…」",
            "「へへっ、ありがとよ…ゲフッ」"
        ]
    ),
    "guard": NPCData(
        name="街のガード",
        char="G",
        color=(100, 200, 255),
        role="guard",
        dialogues=[
            "「治安維持中だ。怪しい真似はするなよ。」",
            "「罪を犯した奴には鉄槌を下す！」",
            "「街の平和は我々が守る！」"
        ]
    ),
    "blackmarket": NPCData(
        name="ブラックマーケットの商人",
        char="$",
        color=(200, 50, 255),
        role="shop",
        dialogues=[
            "「ヘッヘッヘ…上玉が揃ってるぜ。」",
            "「金さえ出せば、どんなアーティファクトでも手に入るのさ。」",
            "「おいおい、手ぶらで帰る気じゃないだろうな？」"
        ],
        shop_inventory=["rubynus_blade", "ether_dagger", "scroll_wish", "potion_cure_ether"]
    ),
    "bartender": NPCData(
        name="バーテンダー",
        char="B",
        color=(220, 180, 120),
        role="inn",
        dialogues=[
            "「いらっしゃい。酒にするかい？それとも仲間を復活させるかい？」",
            "「ダンジョンの噂ならいくらでもあるぜ。」"
        ]
    )
}


# 面白いランダムイベント (Elonaの狂気とユーモア)
RANDOM_EVENTS = [
    "突然空から【カボチャ】が降ってきた！頭に直撃したが無傷だった。",
    "遠くで誰かが「うみみゃぁ！」と叫ぶ声が聞こえた…",
    "どこからか香ばしいパンを焼く匂いが漂ってきた。",
    "足元に落ちていた金貨の小袋を見つけた！ (+120G)",
    "通りすがりの吟遊詩人があなたの美しさを讃える歌を歌い始めた。",
    "風が緑色に揺らめいた気がしたが、気のせいだったようだ…",
    "背後に気配を感じて振り返ったが、誰もいなかった。"
]
