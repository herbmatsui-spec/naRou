"""
Skill Eater Phase 3: Real-time Deck Combat System (Steps 7-14)
山札（デッキ）から手札を引き、即席合成・破棄・疲労リロードを管理するデッキ構築型バトルシステム。
"""

import random
from typing import Any, Dict, List


class CombatDeckSystem:
    """
    リアルタイム構築戦・デッキバトルエンジン
    """

    def __init__(self, initial_skills: List[str]):
        # Step 8: 山札の生成
        self.draw_pile: List[str] = list(initial_skills)
        self.discard_pile: List[str] = []
        self.hand: List[str] = []
        self.hand_limit: int = 4
        self.mana: int = 3
        self.max_mana: int = 3
        self.fatigue_damage: int = 0
        random.shuffle(self.draw_pile)

    def start_turn(self, draw_count: int = 4) -> Dict[str, Any]:
        """Step 9 & 12: ターン開始時ドローとリロード・疲労処理"""
        self.mana = self.max_mana
        drawn = []
        fatigue_taken = 0

        for _ in range(draw_count):
            if len(self.hand) >= self.hand_limit:
                break
            if not self.draw_pile:
                # Step 12: 山札切れ時のリロード＆疲労ダメージ
                if self.discard_pile:
                    self.draw_pile = list(self.discard_pile)
                    self.discard_pile = []
                    random.shuffle(self.draw_pile)
                    self.fatigue_damage += 5
                    fatigue_taken += self.fatigue_damage
                else:
                    break  # 引くカードが全くない
            if self.draw_pile:
                card = self.draw_pile.pop()
                self.hand.append(card)
                drawn.append(card)

        return {
            "hand": self.hand,
            "drawn_cards": drawn,
            "current_mana": self.mana,
            "draw_pile_count": len(self.draw_pile),
            "discard_pile_count": len(self.discard_pile),
            "fatigue_damage_taken": fatigue_taken,
        }

    def instant_synthesize(self, skill_a: str, skill_b: str) -> Dict[str, Any]:
        """Step 10: 手札内の2つのスキルを戦闘中に即席合成"""
        if skill_a not in self.hand or skill_b not in self.hand:
            return {"success": False, "message": "Both skills must be in hand to synthesize."}
        if skill_a == skill_b and self.hand.count(skill_a) < 2:
            return {"success": False, "message": "Cannot synthesize same card without duplicate."}

        self.hand.remove(skill_a)
        self.hand.remove(skill_b)

        fused_skill = f"Instant Fusion: [{skill_a} + {skill_b}]"
        self.hand.append(fused_skill)

        return {
            "success": True,
            "fused_skill": fused_skill,
            "hand": self.hand,
            "message": f"Synthesized [{fused_skill}] in real-time!",
        }

    def discard_for_mana(self, skill_name: str) -> Dict[str, Any]:
        """Step 11: 不要な手札を破棄してマナ回復"""
        if skill_name not in self.hand:
            return {"success": False, "message": "Skill not in hand."}

        self.hand.remove(skill_name)
        self.discard_pile.append(skill_name)
        self.mana += 1

        return {
            "success": True,
            "discarded": skill_name,
            "current_mana": self.mana,
            "message": f"Discarded [{skill_name}] for +1 Mana.",
        }

    def execute_skill_attack(
        self, skill_name: str, base_power: int = 100, mana_cost: int = 1
    ) -> Dict[str, Any]:
        """Step 14: スキル使用と攻撃判定"""
        if skill_name not in self.hand:
            return {"success": False, "message": "Skill not in hand."}
        if self.mana < mana_cost:
            return {"success": False, "message": "Not enough mana."}

        self.hand.remove(skill_name)
        self.discard_pile.append(skill_name)
        self.mana -= mana_cost

        damage = base_power
        if "Instant Fusion" in skill_name:
            damage = int(base_power * 2.5)  # 即席合成スキルは2.5倍威力

        return {
            "success": True,
            "skill_used": skill_name,
            "damage_dealt": damage,
            "remaining_mana": self.mana,
            "message": f"Executed [{skill_name}] dealing {damage} damage!",
        }

    def get_enemy_intent(self, turn_number: int) -> Dict[str, Any]:
        """Step 13: 敵の行動予約（インテント）表示"""
        intents = [
            {"action": "ATTACK", "power": 120, "description": "敵は強烈な斬撃を構えている！"},
            {"action": "DEFEND", "power": 80, "description": "敵はバリアを展開しようとしている！"},
            {"action": "SPECIAL", "power": 250, "description": "警告：大技チャージ中！"},
        ]
        return intents[(turn_number - 1) % len(intents)]
