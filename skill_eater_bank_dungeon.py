"""
Skill Eater Phase 3: Bank Dungeon & Hazard Erosion System (Steps 17-22)
世界スキル銀行本部の多層ダンジョン探索と「概念の侵食（ハザードレベル）」による動的マップ変化を管理。
"""

from typing import Dict, Any, List, Optional

class BankDungeonManager:
    """
    世界スキル銀行本部 多層要塞ダンジョンマネージャー
    """
    def __init__(self):
        # Step 18: 階層データ
        self.floors: List[Dict[str, Any]] = [
            {"floor": 1, "name": "投資信託部門 (Investment Sector)", "cleared": False},
            {"floor": 2, "name": "負債回収部門 (Debt Collection Wing)", "cleared": False},
            {"floor": 3, "name": "特権階級データ保管庫 (Elite Vault)", "cleared": False},
            {"floor": 4, "name": "世界コア制御室 (World Core Sanctuary)", "cleared": False}
        ]
        self.current_floor_index = 0
        self.hazard_level = 0  # 0 to 100
        self.active_debuffs: List[str] = []
        self.is_shortcut_blocked = False

    def advance_exploration_step(self) -> Dict[str, Any]:
        """Step 19, 20, 21: 探索進行、ハザード上昇、環境デバフとマップ変化"""
        self.hazard_level = min(100, self.hazard_level + 15)
        
        # Step 20: ハザードに応じたデバフ適用
        self.active_debuffs = []
        if self.hazard_level >= 30:
            self.active_debuffs.append("Concept Leaking: MP Cost +20%")
        if self.hazard_level >= 60:
            self.active_debuffs.append("Gravity Distortion: Turn Time -30%")
        if self.hazard_level >= 90:
            self.active_debuffs.append("Total Reality Breakdown: Continuous HP Erosion")

        # Step 21: マップ構造変化
        if self.hazard_level >= 50 and not self.is_shortcut_blocked:
            self.is_shortcut_blocked = True
            map_event = "ALERT: Spatial collapse blocked the central shortcut!"
        else:
            map_event = "Path stable."

        return {
            "current_floor": self.floors[self.current_floor_index]["name"],
            "hazard_level": self.hazard_level,
            "active_debuffs": self.active_debuffs,
            "map_event": map_event,
            "is_shortcut_blocked": self.is_shortcut_blocked
        }

    def clear_current_floor(self) -> Dict[str, Any]:
        """Step 22: 階層クリアとハザード一時鎮圧・報酬付与"""
        current_floor_data = self.floors[self.current_floor_index]
        current_floor_data["cleared"] = True
        
        # ハザードの鎮圧
        self.hazard_level = max(0, self.hazard_level - 50)
        self.is_shortcut_blocked = False
        
        cleared_name = current_floor_data["name"]
        has_next = False
        if self.current_floor_index < len(self.floors) - 1:
            self.current_floor_index += 1
            has_next = True

        return {
            "success": True,
            "cleared_floor": cleared_name,
            "next_floor": self.floors[self.current_floor_index]["name"] if has_next else "None (Final Boss Floor)",
            "hazard_level_after_purge": self.hazard_level,
            "rewards": "High-Grade Concept Shard & Floor Clearance Token",
            "has_next_floor": has_next
        }
