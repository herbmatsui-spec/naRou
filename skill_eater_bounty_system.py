"""
Skill Eater Phase 2: Bounty & Heist System (Steps 49-54)
ミダス商会幹部10人に対する指名手配、情報収集、罠設置、スキル強奪を管理。
"""

from typing import Dict, Any, List, Optional

class MidasBountyManager:
    """
    ミダス商会幹部 指名手配・ハイストマネージャー
    """
    def __init__(self):
        # Step 50: ターゲット幹部定義（10人抜粋・主要幹部）
        self.executives: Dict[str, Dict[str, Any]] = {
            "exec_01_valerius": {
                "name": "徴税卿ヴァレリウス",
                "title": "ミダス商会 第10執行役員",
                "unique_skill": "Skill Taxation (スキル課税)",
                "base_hp": 3000,
                "base_atk": 180,
                "intel_gathered": False,
                "intel_detail": "Weakness: Short-circuit traps disrupt his gold barrier.",
                "trap_set": False,
                "is_defeated": False
            },
            "exec_02_morgan": {
                "name": "投機狂モーガン",
                "title": "ミダス商会 第9執行役員",
                "unique_skill": "Risk Hedge (絶対損切り結界)",
                "base_hp": 4500,
                "base_atk": 220,
                "intel_gathered": False,
                "intel_detail": "Weakness: Rapid multi-hit attacks overload hedge capacity.",
                "trap_set": False,
                "is_defeated": False
            }
        }
        self.defeated_count = 0

    def gather_intel(self, exec_id: str, hacker_cost_junk: int = 100) -> Dict[str, Any]:
        """Step 51: 情報収集フェーズ（弱点アンロック）"""
        if exec_id not in self.executives:
            return {"success": False, "message": "Executive target not found."}
        
        target = self.executives[exec_id]
        if target["intel_gathered"]:
            return {"success": True, "message": "Intel already gathered.", "intel": target["intel_detail"]}
        
        target["intel_gathered"] = True
        return {
            "success": True,
            "message": f"Intelligence acquired on [{target['name']}]!",
            "target": target["name"],
            "intel": target["intel_detail"]
        }

    def set_ambush_trap(self, exec_id: str, trap_type: str = "EMP_ShortCircuit") -> Dict[str, Any]:
        """Step 52: 襲撃前の罠設置（事前デバフ準備）"""
        if exec_id not in self.executives:
            return {"success": False, "message": "Executive target not found."}
        
        target = self.executives[exec_id]
        target["trap_set"] = True
        return {
            "success": True,
            "message": f"Ambush trap [{trap_type}] rigged for {target['name']}.",
            "trap_type": trap_type
        }

    def initiate_combat(self, exec_id: str) -> Dict[str, Any]:
        """Step 53: 幹部との戦闘突入（情報・罠の有無で弱体化）"""
        if exec_id not in self.executives:
            return {"error": "Target not found"}
        
        target = self.executives[exec_id]
        if target["is_defeated"]:
            return {"error": "Target already eliminated"}

        hp_multiplier = 1.0
        atk_multiplier = 1.0
        applied_debuffs = []

        if target["intel_gathered"]:
            atk_multiplier -= 0.20
            applied_debuffs.append("Weakness Exploited (ATK -20%)")
        if target["trap_set"]:
            hp_multiplier -= 0.30
            applied_debuffs.append("Ambush Trap Triggered (HP -30%)")

        effective_hp = int(target["base_hp"] * hp_multiplier)
        effective_atk = int(target["base_atk"] * atk_multiplier)

        return {
            "target_name": target["name"],
            "unique_skill": target["unique_skill"],
            "effective_hp": effective_hp,
            "effective_atk": effective_atk,
            "debuffs": applied_debuffs,
            "message": "Heist combat initiated!"
        }

    def eliminate_executive(self, exec_id: str) -> Dict[str, Any]:
        """Step 54: 幹部討伐時のスキル強奪・マイルストーン報酬"""
        if exec_id not in self.executives:
            return {"success": False, "message": "Executive not found."}
        
        target = self.executives[exec_id]
        if target["is_defeated"]:
            return {"success": False, "message": "Already defeated."}
        
        target["is_defeated"] = True
        self.defeated_count += 1
        stolen_skill = target["unique_skill"]

        return {
            "success": True,
            "message": f"EXECUTIVE ELIMINATED: {target['name']} has fallen!",
            "stolen_skill": stolen_skill,
            "defeated_count": self.defeated_count,
            "resistance_milestone_reward": "5000 Junk & Corporate Security Token"
        }
