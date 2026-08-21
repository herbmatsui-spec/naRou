"""
Skill Eater Phase 2: Underground Arena System (Steps 24-30)
安全に極端な壊れスキルやビルドをテストできるシミュレータ＆闘技場。
ウェーブ制バトル、DPS計測、制約付きチャレンジ、スコアリングを管理する。
"""

from typing import Dict, Any, List, Optional

class UndergroundArenaManager:
    """
    地下闘技場（ビルド検証シミュレータ）マネージャー
    """
    def __init__(self):
        self.current_wave = 0
        self.max_wave = 10
        self.is_in_arena = False
        self.active_challenge: Optional[str] = None
        self.total_damage_dealt = 0
        self.total_turns_taken = 0
        self.high_score = 0
        self.unlocked_ranks = ["Bronze"]

    def start_arena_session(self, challenge_mode: Optional[str] = None) -> Dict[str, Any]:
        """Step 25 & 27: 闘技場セッション開始とチャレンジモード適用"""
        self.is_in_arena = True
        self.current_wave = 1
        self.active_challenge = challenge_mode  # 例: "NO_MAGIC", "TIME_ATTACK", "HEAVY_TOXICITY"
        self.total_damage_dealt = 0
        self.total_turns_taken = 0
        
        return {
            "success": True,
            "message": "Arena simulation started. Safe-mode enabled (No death penalty).",
            "wave": self.current_wave,
            "challenge": self.active_challenge or "STANDARD_PRACTICE"
        }

    def spawn_wave_enemies(self) -> Dict[str, Any]:
        """Step 25: ウェーブごとの仮想敵スポーン"""
        if not self.is_in_arena:
            return {"error": "Not in arena"}
        
        enemy_hp = 500 * self.current_wave
        enemy_def = 10 * self.current_wave
        
        return {
            "wave": self.current_wave,
            "target_dummy": {
                "name": f"Simulation Drone MK-{self.current_wave}",
                "hp": enemy_hp,
                "defense": enemy_def,
                "type": "Holographic Target"
            }
        }

    def simulate_attack(self, player_damage: int, skill_type: str = "Physical") -> Dict[str, Any]:
        """Step 26 & 28: ダメージシミュレートとDPS計測（制約チェック付き）"""
        if not self.is_in_arena:
            return {"success": False, "message": "Arena session not active."}
        
        # Step 27: 制約チェック
        if self.active_challenge == "NO_MAGIC" and skill_type == "Magic":
            return {
                "success": False,
                "message": "Challenge Violation: Magic is forbidden in NO_MAGIC challenge!"
            }
            
        actual_damage = max(1, player_damage)
        self.total_damage_dealt += actual_damage
        self.total_turns_taken += 1
        
        current_dps = self.total_damage_dealt / max(1, self.total_turns_taken)
        
        return {
            "success": True,
            "damage_dealt": actual_damage,
            "total_damage": self.total_damage_dealt,
            "turns": self.total_turns_taken,
            "current_dps": round(current_dps, 2)
        }

    def complete_wave(self) -> Dict[str, Any]:
        """Step 29 & 30: ウェーブクリア処理、報酬付与、ランク認定"""
        if not self.is_in_arena:
            return {"success": False, "message": "Not in arena"}
            
        reward_junk = 100 * self.current_wave
        score_gain = (self.total_damage_dealt // max(1, self.total_turns_taken)) * self.current_wave
        self.high_score = max(self.high_score, score_gain)
        
        # ランク判定
        if self.current_wave >= 5 and "Silver" not in self.unlocked_ranks:
            self.unlocked_ranks.append("Silver")
        if self.current_wave >= 10 and "Gold" not in self.unlocked_ranks:
            self.unlocked_ranks.append("Gold")
            
        completed_wave = self.current_wave
        if self.current_wave < self.max_wave:
            self.current_wave += 1
            has_next = True
        else:
            self.is_in_arena = False
            has_next = False

        return {
            "success": True,
            "cleared_wave": completed_wave,
            "has_next_wave": has_next,
            "reward_junk": reward_junk,
            "score": score_gain,
            "current_ranks": self.unlocked_ranks
        }

    def exit_arena(self) -> Dict[str, Any]:
        """Step 26: デスペナルティなしで退出"""
        self.is_in_arena = False
        return {
            "success": True,
            "message": "Safely exited underground arena. No HP lost or item lost.",
            "final_dps": round(self.total_damage_dealt / max(1, self.total_turns_taken), 2) if self.total_turns_taken > 0 else 0,
            "high_score": self.high_score
        }
