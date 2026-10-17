"""
Skill Eater Phase 3: Final Boss Causality Battle System (Steps 54-62)
ドン・ミダスとの多段階決戦、因果律操作（行動キャンセル）、論理矛盾によるフリーズ誘発、世界崩壊・Phase 4移行フラグを管理。
"""

from typing import Any, Dict, List


class FinalBossCausalityManager:
    """
    最終ボス「ドン・ミダス」因果律バトルマネージャー
    """

    def __init__(self):
        # Step 55: 第一形態
        self.boss_name = "ドン・ミダス (Don Midas)"
        self.phase = 1  # 1: 通常形態, 2: 世界コア融合・因果律形態
        self.hp = 15000
        self.max_hp = 15000
        self.is_defeated = False
        self.is_frozen = False
        self.freeze_turns = 0
        self.stolen_player_actions: List[str] = []

    def attack_don_midas(
        self, action_name: str, damage: int, is_paradox_combo: bool = False
    ) -> Dict[str, Any]:
        """Step 56, 57, 58, 59: 第一・第二形態遷移、因果律キャンセル、論理矛盾フリーズ"""
        if self.is_defeated:
            return {"status": "BOSS_ALREADY_DEFEATED"}

        # フリーズ中の攻撃
        if self.is_frozen:
            self.hp = max(0, self.hp - (damage * 3))
            self.freeze_turns -= 1
            if self.freeze_turns <= 0:
                self.is_frozen = False

            if self.hp <= 0:
                return self.conclude_battle()
            return {
                "phase": self.phase,
                "boss_frozen": True,
                "damage_dealt": damage * 3,
                "boss_hp": self.hp,
                "message": f"CRITICAL EXTRACTION: Exploited causality freeze for {damage * 3} damage!",
            }

        # Step 56: 第一形態 -> 第二形態（世界コア融合）
        if self.phase == 1:
            self.hp = max(0, self.hp - damage)
            if self.hp <= 7500:
                self.phase = 2
                self.hp = 25000
                self.max_hp = 25000
                return {
                    "phase": 2,
                    "transition": True,
                    "message": "PHASE 2 TRIGGERED: Don Midas merged with the World Core! Causality manipulation active!",
                }
            return {"phase": 1, "boss_hp": self.hp, "damage_dealt": damage}

        # Step 57 & 59: 第二形態の因果律バトル
        if is_paradox_combo:
            # Step 59: 論理矛盾行動によるボスの因果律エラー（フリーズ）誘発
            self.is_frozen = True
            self.freeze_turns = 2
            return {
                "phase": 2,
                "paradox_triggered": True,
                "boss_frozen": True,
                "message": "LOGIC PARADOX ERROR: Causality engine crashed! Don Midas is completely frozen for 2 turns!",
            }
        else:
            # Step 57 & 58: 因果律操作によるプレイヤー行動キャンセル
            self.stolen_player_actions.append(action_name)
            return {
                "phase": 2,
                "action_cancelled": True,
                "cancelled_action": action_name,
                "damage_dealt": 0,
                "boss_hp": self.hp,
                "message": f"CAUSALITY REVERSAL: Don Midas erased the causality of [{action_name}]! Damage nullified.",
            }

    def execute_core_extraction(self) -> Dict[str, Any]:
        """Step 60: ボスフリーズ中の「強制抽出（コアぶっこ抜き）」コマンド"""
        if not self.is_frozen:
            return {
                "success": False,
                "message": "Cannot extract core unless boss causality is frozen.",
            }

        self.hp = 0
        return self.conclude_battle()

    def conclude_battle(self) -> Dict[str, Any]:
        """Step 61 & 62: ボス撃破、世界崩壊ログ、Phase 4移行フラグ"""
        self.is_defeated = True
        return {
            "boss_defeated": True,
            "phase3_completed": True,
            "unlocked_phase": 4,
            "message": "WORLD CORE SHATTERED: The Midas Skill Monopoly has collapsed entirely. Moving to Phase 4 (Inheritance Preparation).",
            "system_log": "KERNEL CRITICAL: System world shutdown imminent. Select skills to carry over.",
        }
