"""
Skill Eater Phase 2: Anti-Meta Boss Battle System (Steps 62-67)
プレイヤーの壊れビルド・メタ知識を妨害する対メタ中ボス（《最適化阻害》《運命観測》）との特殊バトル。
弱点スキルの看破、フェーズ移行、Phase 3へのフラグ管理を行う。
"""

from typing import Any, Dict


class AntiMetaBossBattleManager:
    """
    対メタ能力者ボス戦マネージャー
    """

    def __init__(self):
        self.boss_name = "監査官オプティマス (Auditor Optimus)"
        self.max_hp = 10000
        self.current_hp = 10000
        self.phase = 1  # 1: 最適化阻害 (High DPS無効), 2: 運命観測 (予知・カウンター)
        self.is_defeated = False
        self.meta_barriers: Dict[str, bool] = {
            "high_dps_nullification": True,  # 500以上の単発ダメージを1にする
            "future_prediction": False,
        }
        self.required_counter_skill = "Glitched Junk Shot"  # 意図的な低Tierジャンク攻撃が弱点

    def process_player_attack(self, raw_damage: int, used_skill: str) -> Dict[str, Any]:
        """Step 63, 64, 65, 66: パッシブ妨害、防御ロジック、弱点看破、フェーズ移行"""
        if self.is_defeated:
            return {"error": "Boss is already defeated"}

        effective_damage = raw_damage
        barrier_triggered = False
        message = ""

        # Step 65: 弱点スキルの判定（メタを外したジャンク攻撃でバリア破壊）
        if used_skill == self.required_counter_skill:
            self.meta_barriers["high_dps_nullification"] = False
            effective_damage = raw_damage * 3
            message = f"CRITICAL BREACH: {used_skill} bypassed Optimus's Optimization Barrier!"
        else:
            # Step 64: 高DPS無効化ロジック
            if self.meta_barriers["high_dps_nullification"] and raw_damage > 300:
                effective_damage = 1
                barrier_triggered = True
                message = "OPTIMIZATION NULLIFIED: Raw overpowered attack converted to 1 damage by boss passive!"

        self.current_hp = max(0, self.current_hp - effective_damage)

        # Step 66: フェーズ2への移行判定 (HP 50%以下)
        if self.current_hp <= 5000 and self.phase == 1:
            self.phase = 2
            self.meta_barriers["future_prediction"] = True
            message += " [PHASE 2 TRIGGERED: Optimus activated 《運命観測 (Fate Prediction)》!]"

        # 撃破判定
        if self.current_hp <= 0:
            self.is_defeated = True
            return self.conclude_boss_battle()

        return {
            "boss_name": self.boss_name,
            "phase": self.phase,
            "damage_taken": effective_damage,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "barrier_triggered": barrier_triggered,
            "message": message,
        }

    def conclude_boss_battle(self) -> Dict[str, Any]:
        """Step 67: Phase 2ボス撃破とPhase 3移行フラグ管理"""
        return {
            "boss_defeated": True,
            "phase2_completed": True,
            "unlocked_phase": 3,
            "message": "Auditor Optimus fell! The route to Midas World Skill Bank Core is now exposed (Phase 3 Unlocked).",
            "dropped_mastery_core": "Concept Key: Meta Bypass Core",
        }
