"""
Skill Eater Phase 5: Epilogue, Artifact & World Transition System (Steps 20-33)
遺産スコアに応じたマルチエンディングテキスト、残滓アーティファクトの生成、次世界へのシームレス移行を管理。
"""

from typing import Dict, Any, List, Optional

class EpilogueAndTransitionManager:
    """
    エピローグ・後日談および世界移行トランジションマネージャー
    """
    def __init__(self):
        self.global_account_artifacts: List[Dict[str, Any]] = []
        self.is_world_a_closed = False
        self.transition_event_triggered = False

    def generate_epilogue_story(self, bequest_scores: Dict[str, int], donated_count: int) -> Dict[str, Any]:
        """Step 21, 22, 23, 24, 25, 26, 27: 遺産スコアに応じた後日談とNPCメッセージの生成"""
        if donated_count == 0:
            story = "【過酷なる独立】スキルをほとんど残さず去ったため、スラムの民は自力で過酷なゼロからの復興を歩み始めた。"
            npc_farewell = "NPC一同: 「……行ってしまったか。だが、自由をもらっただけで十分だ。俺たちの足で歩いてみせるさ。」"
        else:
            dominant = max(bequest_scores, key=bequest_scores.get)
            if dominant == "Combat":
                story = "【覇道の鉄塞】遺された強力な武力スキルにより、スラム街は侵略者を一切寄せ付けない最強の軍事自治都市へと発展した。"
                npc_farewell = "バルバロッサ: 「お前がくれた力で、二度と誰にも支配されない街を作ってみせる。達者でな、相棒！」"
            elif dominant == "Recovery":
                story = "【博愛の聖域】豊富な治癒と防衛スキルにより、スラム街は傷ついた全ての民を受け入れる奇跡の癒しの都となった。"
                npc_farewell = "シスター・エレナ: 「あなたの慈愛は永遠に受け継がれます。どうか次の世界でも、光があらんことを。」"
            else: # Production
                story = "【理知の魔導都市】生産と解析の遺産により、旧来の独占銀行に代わるオープンな知識と技術の学術都市が誕生した。"
                npc_farewell = "技術長クラフト: 「解析コードの遺産は全て解読したぜ！ここは世界一の魔導都市になる。見ててくれよな！」"

        return {
            "epilogue_story": story,
            "npc_farewell": npc_farewell,
            "epilogue_completed": True
        }

    def generate_remnant_artifact(self, bosses_defeated: int = 4) -> Dict[str, Any]:
        """Step 28, 29, 30: Aの世界の残滓（記念パッシブアーティファクト）の生成とグローバル登録"""
        artifact = {
            "artifact_id": "art_broken_golden_coin",
            "name": "ミダスの砕けた金貨 (Broken Midas Coin)",
            "origin_world": "W4: スキル喰いの異世界倒産",
            "passive_effect": "全異世界における資金・リソース獲得量 +10%",
            "flavor_text": "スキル独占資本主義を打倒した証。世界の理を越えて価値を呼び込む。"
        }
        self.global_account_artifacts.append(artifact)
        return {
            "success": True,
            "artifact": artifact,
            "message": f"ACQUIRED REMNANT ARTIFACT: [{artifact['name']}] registered to Global Account!"
        }

    def trigger_world_transition(self, target_world_id: str = "W1_Magic_Dominant") -> Dict[str, Any]:
        """Step 31, 32, 33: セーブデータクローズと次世界への落下トランジション"""
        self.is_world_a_closed = True
        self.transition_event_triggered = True

        transition_log = [
            "==================================================",
            "【次元ゲート開放】Aの世界（W4）の境界線が溶解します...",
            "【世界データ保存】持ち込みスキル・時空金庫・残滓アーティファクトを固定完了。",
            f"【落下開始】次元の裂け目を超え、[{target_world_id}] の空へと放り出されます！",
            "=================================================="
        ]

        return {
            "success": True,
            "world_a_closed": True,
            "target_world": target_world_id,
            "transition_log": "\n".join(transition_log),
            "phase5_completed": True,
            "game_loop_status": "NEXT_WORLD_INITIALIZATION_READY"
        }
