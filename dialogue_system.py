"""
Dialogue System Module - Dialogue Management and NPC interaction
"""

from __future__ import annotations

import random
from typing import Any

from rich_content import NPCS_CATALOG


class DialogueManager:
    """NPC対話管理クラス"""

    CIEL_DIALOGUES = [
        "「お兄ちゃん、無理しちゃダメだよ！シエルが守るから！」",
        "「グウェンちゃん可愛いよね〜！でも塩は投げちゃダメだよ？」",
        "「シエル、お兄ちゃんといられるだけで幸せだよ。えへへ。」",
    ]

    DEFAULT_NPC_DIALOGUE = "「……（こちらを警戒している）」"

    @classmethod
    def get_dialogue(cls, speaker: Any, player: Any, engine: Any | None = None) -> tuple[str, str]:
        """NPCまたはペットとプレイヤーの間の対話テキストを生成"""
        speaker_name = getattr(speaker, "name", "誰か")

        # ワールドフェーズに基づく特殊台詞の判定 (設計書 2.2)
        if engine and hasattr(engine, "world_state_manager"):
            from world_state_system import WorldPhase

            phase = engine.world_state_manager.get_phase()

            # 村の長などの重要NPCの場合
            if "村の長" in speaker_name:
                if phase == WorldPhase.BEGINNING:
                    return (
                        speaker_name,
                        "「若き旅人よ、この古文書を読み解き、世界の異変を止めてくれぬか。」",
                    )
                elif phase == WorldPhase.AWAKENING:
                    return (
                        speaker_name,
                        "「古の守護者を倒したか！ さすがじゃ。次は各地に散らばる断片を集めるのじゃ。」",
                    )
                elif phase == WorldPhase.EXPLORATION:
                    return (
                        speaker_name,
                        "「世界の真実が見えてきたな。だが、闇の勢力も動き出しておるぞ。」",
                    )

        # ペットの場合
        if hasattr(engine, "pet") and speaker == engine.pet:
            return speaker_name, random.choice(cls.CIEL_DIALOGUES)

        # カタログNPCの場合（例: グウェン）
        if "グウェン" in speaker_name and "gwen" in NPCS_CATALOG:
            return speaker_name, random.choice(NPCS_CATALOG["gwen"].dialogues)

        # 関係性システムによる動的判定（もしあれば）
        if hasattr(engine, "relationship_manager") and hasattr(player, "character_relationships"):
            rel_dict = getattr(player, "character_relationships", {})
            if speaker_name in rel_dict:
                trust = rel_dict[speaker_name].get("trust", 0)
                if trust >= 50:
                    return (
                        speaker_name,
                        f"「{player.name}さん、いつも頼りにしていますよ！」",
                    )
                elif trust <= -30:
                    return speaker_name, "「……お前に関わる気はない。立ち去れ。」"

        # T43 案A: NPC の記憶・噂を会話へ反映 (記憶も噂も無ければ既定台詞のまま)
        memory_line = cls._social_memory_line(speaker, player, speaker_name, engine)
        if memory_line is not None:
            return speaker_name, memory_line

        return speaker_name, cls.DEFAULT_NPC_DIALOGUE

    @classmethod
    def _social_memory_line(
        cls, speaker: Any, player: Any, speaker_name: str, engine: Any | None
    ) -> str | None:
        """NPC の記憶・噂から会話の一言を生成する (どちらも無ければ None)

        記憶を持つ NPC はプレイヤーの過去の行動に言及し、噂を知る NPC は
        それを話題にする。どちらも知らない NPC は何も語らない (情報非対称)。
        """
        player_id = getattr(player, "name", "player")
        try:
            from npc_memory_system import build_memory_dialogue_line

            line = build_memory_dialogue_line(speaker, player_id=player_id)
        except Exception:
            line = None
        if line:
            return line

        rumor_engine = getattr(engine, "rumor_engine", None) if engine is not None else None
        if rumor_engine is None:
            return None
        try:
            from rumor_propagation_system import build_rumor_dialogue_line

            return build_rumor_dialogue_line(rumor_engine, speaker_name, player_name=player_id)
        except Exception:
            return None
