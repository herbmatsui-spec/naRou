"""
Skill Eater Phase 3: Slum Finale System (Steps 49-53)
本部襲撃と同時進行する、拠点NPCと育成ペットたちによるスラム街最終防衛戦を管理。
"""

from typing import Any, Dict, List


class SlumFinaleManager:
    """
    スラム街最終防衛戦（同時進行イベント）マネージャー
    """

    def __init__(self, base_power: int = 500):
        self.slum_defensive_power = base_power
        self.total_raid_waves = 3
        self.current_raid_wave = 1
        self.is_base_destroyed = False
        self.fallen_sectors: List[str] = []

    def simulate_concurrent_defense(self, enemy_assault_power: int) -> Dict[str, Any]:
        """Step 50, 51, 52: ダンジョン進行度に応じた自動防衛判定と被害計算"""
        if self.is_base_destroyed:
            return {"status": "BASE_ALREADY_DESTROYED"}

        defense_margin = self.slum_defensive_power - enemy_assault_power

        if defense_margin >= 0:
            result = "WAVE_REPELLED_PERFECTLY"
            sector_lost = None
            msg = f"Resistance forces successfully defended against Wave {self.current_raid_wave}!"
        else:
            # 防衛劣勢によるスラムの一部区画喪失
            sector_lost = f"Sector-{self.current_raid_wave} (Slum Market)"
            self.fallen_sectors.append(sector_lost)
            result = "SECTOR_BREACHED"
            msg = f"Heavy casualties! {sector_lost} was breached by Midas forces."
            if len(self.fallen_sectors) >= 3:
                self.is_base_destroyed = True
                result = "SLUM_ANNIHILATED"

        self.current_raid_wave += 1
        return {
            "wave": self.current_raid_wave - 1,
            "result": result,
            "fallen_sectors": self.fallen_sectors,
            "is_base_destroyed": self.is_base_destroyed,
            "message": msg,
        }

    def trigger_final_stand_boost(self, player_encouragement_buff: int = 300) -> Dict[str, Any]:
        """Step 53: 本部最深部到達時の総力戦トリガーと士気ブースト"""
        self.slum_defensive_power += player_encouragement_buff
        return {
            "success": True,
            "boosted_defensive_power": self.slum_defensive_power,
            "message": "FINAL STAND: The entire Slum rallied for the ultimate defense!",
        }
