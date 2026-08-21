"""
Skill Eater Phase 3: World Law Override System (Steps 38-48)
概念の鍵を消費してRoot Accessを獲得し、ダメージ上限撤廃や属性反転などの世界法則をハックするシステム。
"""

from typing import Dict, Any, List, Optional

class WorldLawOverrideManager:
    """
    世界法則書き換え (Root Access) マネージャー
    """
    def __init__(self):
        # Step 39: 世界法則パラメーターツリー
        self.root_access_granted = False
        self.laws: Dict[str, Any] = {
            "damage_limit": 9999,
            "elemental_inversion": False,  # 属性耐性を反転
            "fatal_damage_survive": False, # 食いしばり
            "crit_multiplier": 1.5
        }
        self.system_alerts: List[str] = []

    def grant_root_access(self, key_count: int) -> Dict[str, Any]:
        """Step 40: 概念の鍵によるRoot Access獲得"""
        if key_count < 2:
            return {"success": False, "message": "Root Access Denied: Need at least 2 Concept Keys."}
        
        self.root_access_granted = True
        return {
            "success": True,
            "message": "ROOT ACCESS GRANTED: World kernel laws are now editable.",
            "editable_laws": list(self.laws.keys())
        }

    def override_damage_limit(self, new_limit: int = 999999) -> Dict[str, Any]:
        """Step 41: ダメージ上限の撤廃ハック"""
        if not self.root_access_granted:
            return {"success": False, "message": "Root access required."}
        
        self.laws["damage_limit"] = new_limit
        self.system_alerts.append("SYSTEM OVERRIDE: Damage cap removed (set to 999,999).")
        return {"success": True, "damage_limit": new_limit}

    def override_elemental_inversion(self, enable: bool = True) -> Dict[str, Any]:
        """Step 42: 属性相性の反転ハック"""
        if not self.root_access_granted:
            return {"success": False, "message": "Root access required."}
        
        self.laws["elemental_inversion"] = enable
        self.system_alerts.append(f"SYSTEM OVERRIDE: Elemental resistance inversion = {enable}.")
        return {"success": True, "elemental_inversion": enable}

    def override_fatal_survive(self, enable: bool = True) -> Dict[str, Any]:
        """Step 43: 致死ダメージ時のHP1ミリ残し（食いしばり）強制付与"""
        if not self.root_access_granted:
            return {"success": False, "message": "Root access required."}
        
        self.laws["fatal_damage_survive"] = enable
        self.system_alerts.append(f"SYSTEM OVERRIDE: Fatal survival kernel hook = {enable}.")
        return {"success": True, "fatal_damage_survive": enable}

    def calculate_modified_damage(self, raw_damage: int, is_fatal: bool = False, current_hp: int = 100) -> Dict[str, Any]:
        """Step 45 & 47: 他戦闘システムへの法則適用とバリデーション"""
        # ダメージ制限適用
        capped_damage = min(self.laws["damage_limit"], raw_damage)
        
        survived_fatal = False
        remaining_hp = current_hp - capped_damage
        
        if is_fatal and self.laws["fatal_damage_survive"] and remaining_hp <= 0:
            remaining_hp = 1
            survived_fatal = True

        return {
            "effective_damage": capped_damage,
            "remaining_hp": remaining_hp,
            "survived_fatal_by_hack": survived_fatal,
            "laws_applied": self.laws
        }
