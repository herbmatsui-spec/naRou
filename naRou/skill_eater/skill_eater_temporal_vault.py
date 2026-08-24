"""
Skill Eater Phase 4: Temporal Vault & Final Selection System (Steps 11-15)
時空金庫（最大3枠）へのスキル保管と、次世界への最終持ち込み5枠の登録・確定を管理。
"""

from typing import Any, Dict, List


class TemporalVaultManager:
    """
    時空金庫および最終持ち込みスロットマネージャー
    """

    def __init__(self, max_carry_slots: int = 5, max_vault_slots: int = 3):
        self.max_carry_slots = max_carry_slots
        self.max_vault_slots = max_vault_slots
        self.carry_over_slots: List[Dict[str, Any]] = []
        self.vault_slots: List[Dict[str, Any]] = []
        self.is_selection_locked = False

    def add_to_carry_over(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """Step 13: 持ち込み枠（最大5枠）への登録"""
        if self.is_selection_locked:
            return {"success": False, "message": "Selection is already locked."}
        if len(self.carry_over_slots) >= self.max_carry_slots:
            return {
                "success": False,
                "message": f"Carry-over slots full (Max {self.max_carry_slots}).",
            }

        self.carry_over_slots.append(skill)
        return {
            "success": True,
            "carried_count": len(self.carry_over_slots),
            "remaining_slots": self.max_carry_slots - len(self.carry_over_slots),
            "message": f"Added [{skill.get('name')}] to carry-over slots.",
        }

    def remove_from_carry_over(self, skill_name: str) -> Dict[str, Any]:
        """Step 13: 持ち込み枠からの解除"""
        if self.is_selection_locked:
            return {"success": False, "message": "Selection is already locked."}

        for i, s in enumerate(self.carry_over_slots):
            if s.get("name") == skill_name:
                removed = self.carry_over_slots.pop(i)
                return {"success": True, "removed": removed, "message": f"Removed [{skill_name}]."}

        return {"success": False, "message": f"Skill [{skill_name}] not found in carry-over slots."}

    def deposit_to_vault(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """Step 12: 時空金庫（最大3枠）への保管"""
        if len(self.vault_slots) >= self.max_vault_slots:
            return {"success": False, "message": f"Vault is full (Max {self.max_vault_slots})."}

        self.vault_slots.append(skill)
        return {
            "success": True,
            "vault_count": len(self.vault_slots),
            "message": f"Stored [{skill.get('name')}] into Temporal Vault.",
        }

    def withdraw_from_vault(self, skill_name: str) -> Dict[str, Any]:
        """Step 12: 時空金庫からの引き出し"""
        for i, s in enumerate(self.vault_slots):
            if s.get("name") == skill_name:
                withdrawn = self.vault_slots.pop(i)
                return {
                    "success": True,
                    "withdrawn": withdrawn,
                    "message": f"Withdrew [{skill_name}] from Vault.",
                }

        return {"success": False, "message": f"Skill [{skill_name}] not found in Vault."}

    def lock_and_finalize_selection(self) -> Dict[str, Any]:
        """Step 14 & 15: 持ち込み枠の確定とPhase 4完了フラグ発行"""
        if len(self.carry_over_slots) == 0:
            return {"success": False, "message": "Cannot finalize with 0 skills selected."}

        self.is_selection_locked = True
        return {
            "success": True,
            "phase4_completed": True,
            "final_carry_skills": [s.get("name") for s in self.carry_over_slots],
            "vaulted_skills": [s.get("name") for s in self.vault_slots],
            "message": "SELECTION LOCKED: Ready for inheritance transition.",
        }
