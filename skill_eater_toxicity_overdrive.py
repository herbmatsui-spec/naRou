"""
Skill Eater Phase 2: Toxicity Overdrive System
Phase 1の拒絶反応(Toxicity)システムを拡張し、リミッター解除による超絶バフと反動(確定気絶・HP減少)を管理するモジュール。
"""

from typing import Any, Dict


class ToxicityOverdriveManager:
    """
    Toxicity Overdrive Manager
    - リミッター解除判定 (Toxicity 100以上 または 緊急トリガー)
    - オーバードライブ中のバフ付与 (ATK, SPD 大幅上昇)
    - 効果終了後の確定気絶 (Stun) と HP反動ダメージ
    - Phase 1 ToxicityManager との連携フック
    """

    def __init__(self, trigger_threshold: float = 100.0, duration_turns: int = 3):
        self.trigger_threshold = trigger_threshold
        self.duration_turns = duration_turns
        self.is_active = False
        self.remaining_turns = 0
        self.recoil_hp_percent = 0.30  # 終了時に最大HPの30%ダメージ
        self.is_stunned = False
        self.stun_remaining_turns = 0

    def can_trigger_overdrive(self, current_toxicity: float) -> bool:
        """Step 2: オーバードライブ発動可能か判定"""
        return (
            (not self.is_active)
            and (not self.is_stunned)
            and (current_toxicity >= self.trigger_threshold)
        )

    def trigger_overdrive(self, current_toxicity: float) -> Dict[str, Any]:
        """Step 2: オーバードライブを発動"""
        if not self.can_trigger_overdrive(current_toxicity):
            return {
                "success": False,
                "message": f"Overdrive condition not met (Toxicity: {current_toxicity}/{self.trigger_threshold}, Active: {self.is_active}, Stunned: {self.is_stunned})",
            }
        self.is_active = True
        self.remaining_turns = self.duration_turns
        return {
            "success": True,
            "message": "LIMITER RELEASED: Toxicity Overdrive Activated!",
            "duration": self.duration_turns,
            "buffs": self.get_overdrive_buffs(),
        }

    def get_overdrive_buffs(self) -> Dict[str, float]:
        """Step 3: オーバードライブ中のバフ効果（攻撃力3倍、速度2.5倍、クリティカル率+50%）"""
        if not self.is_active:
            return {"atk_multiplier": 1.0, "speed_multiplier": 1.0, "crit_rate_bonus": 0.0}
        return {"atk_multiplier": 3.0, "speed_multiplier": 2.5, "crit_rate_bonus": 0.50}

    def end_overdrive(self, current_hp: int, max_hp: int) -> Dict[str, Any]:
        """Step 4: 効果終了後の確定気絶（行動不能ペナルティ）とHP減少の実装"""
        self.is_active = False
        self.remaining_turns = 0
        self.is_stunned = True
        self.stun_remaining_turns = 2  # 2ターン行動不能

        recoil_damage = int(max_hp * self.recoil_hp_percent)
        new_hp = max(1, current_hp - recoil_damage)  # 反動で即死はしない(最低1残る)

        return {
            "message": "Overdrive ended. Severe toxic recoil: Stunned for 2 turns!",
            "recoil_damage": recoil_damage,
            "remaining_hp": new_hp,
            "stun_turns": self.stun_remaining_turns,
        }

    def tick_turn(self, current_hp: int, max_hp: int) -> Dict[str, Any]:
        """ターン経過の処理"""
        result = {}
        if self.is_active:
            self.remaining_turns -= 1
            result["remaining_turns"] = self.remaining_turns
            if self.remaining_turns <= 0:
                end_res = self.end_overdrive(current_hp, max_hp)
                result.update(end_res)
        elif self.is_stunned:
            self.stun_remaining_turns -= 1
            result["stun_remaining_turns"] = self.stun_remaining_turns
            if self.stun_remaining_turns <= 0:
                self.is_stunned = False
                result["message"] = "Recovered from toxic stun."
        result["is_active"] = self.is_active
        result["is_stunned"] = self.is_stunned
        return result

    def hook_with_phase1_toxicity(
        self, phase1_toxicity_manager: Any, current_hp: int, max_hp: int
    ) -> Dict[str, Any]:
        """Step 5: Phase 1 ToxicityManagerと連動するためのフック"""
        tox = getattr(phase1_toxicity_manager, "toxicity", 0.0)
        if self.can_trigger_overdrive(tox):
            res = self.trigger_overdrive(tox)
            # オーバードライブ発動時は毒性を一旦全消費
            phase1_toxicity_manager.toxicity = 0.0
            return res
        return {"success": False, "message": "Hook: Toxicity not enough for overdrive"}
