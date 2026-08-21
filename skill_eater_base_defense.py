"""
Skill Eater Phase 2: Base Defense System (Steps 55-61)
ミダス商会の警戒度上昇に伴う拠点防衛戦（タワーディフェンス）、トラップ配置、拠点耐久値管理。
"""

from typing import Dict, Any, List

class BaseDefenseManager:
    """
    レジスタンス拠点防衛戦マネージャー
    """
    def __init__(self, base_max_hp: int = 1000):
        self.alert_level = 0  # 0 to 100
        self.base_max_hp = base_max_hp
        self.base_hp = base_max_hp
        self.placed_traps: List[Dict[str, Any]] = []
        self.is_defense_active = False
        self.current_raid_wave = 0
        self.max_raid_waves = 3

    def increase_alert(self, amount: int = 25) -> Dict[str, Any]:
        """Step 56: 警戒度上昇"""
        self.alert_level = min(100, self.alert_level + amount)
        raid_triggered = (self.alert_level >= 100)
        return {
            "current_alert": self.alert_level,
            "raid_triggered": raid_triggered
        }

    def place_defense_trap(self, trap_name: str, damage: int, junk_cost: int = 100) -> Dict[str, Any]:
        """Step 58: 防衛トラップの配置"""
        trap_info = {
            "name": trap_name,
            "damage": damage,
            "used": False
        }
        self.placed_traps.append(trap_info)
        return {
            "success": True,
            "message": f"Deployed defense trap [{trap_name}] (Damage: {damage})",
            "total_traps": len(self.placed_traps)
        }

    def start_defense_battle(self) -> Dict[str, Any]:
        """Step 57: 拠点防衛戦トリガー発動"""
        self.is_defense_active = True
        self.current_raid_wave = 1
        self.alert_level = 0  # リセット
        return {
            "success": True,
            "message": "EMERGENCY: Midas Security Forces are raiding the Underground Base!",
            "base_hp": f"{self.base_hp}/{self.base_max_hp}",
            "traps_ready": len(self.placed_traps)
        }

    def process_raid_wave(self, enemy_power: int) -> Dict[str, Any]:
        """Step 59 & 60: ウェーブ進行、トラップ発動、拠点ダメージ計算"""
        if not self.is_defense_active:
            return {"error": "No defense battle active."}

        trap_damage_total = 0
        used_traps_count = 0
        for trap in self.placed_traps:
            if not trap["used"]:
                trap_damage_total += trap["damage"]
                trap["used"] = True
                used_traps_count += 1

        effective_enemy_power = max(0, enemy_power - trap_damage_total)
        self.base_hp = max(0, self.base_hp - effective_enemy_power)

        is_base_destroyed = (self.base_hp <= 0)
        
        result = {
            "wave": self.current_raid_wave,
            "enemy_raw_power": enemy_power,
            "trap_damage_mitigated": trap_damage_total,
            "base_damage_taken": effective_enemy_power,
            "base_hp_remaining": self.base_hp,
            "is_base_destroyed": is_base_destroyed
        }

        if is_base_destroyed:
            self.is_defense_active = False
            result["result"] = "BASE_FALLEN"
        else:
            if self.current_raid_wave < self.max_raid_waves:
                self.current_raid_wave += 1
                result["result"] = "WAVE_DEFENDED"
            else:
                # Step 61: 防衛成功リザルト
                self.is_defense_active = False
                result["result"] = "RAID_REPELLED_VICTORY"
                result["message"] = "Midas forces retreated! Slum base secured."

        return result
