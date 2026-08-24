"""
Skill Eater Phase 2: Pet Dispatch System (Steps 17-23)
ペット（従属者）に専用スキルビルドを装着させ、自動で探索・素材収集を行わせるシステム。
"""

import random
from typing import Any, Dict, Optional


class PetDispatchManager:
    """
    従属者（ペット）自動探索・派遣マネージャー
    """

    def __init__(self):
        # Step 18: ペットステータスと装備スキル枠
        self.pets: Dict[str, Dict[str, Any]] = {
            "husk_hound_01": {
                "name": "ハスク・ハウンド (改造魔獣)",
                "level": 1,
                "exp": 0,
                "is_injured": False,
                "equipped_skills": ["Physical Attack", "Stealth Digging"],
                "max_skill_slots": 3,
            },
            "cyber_homunculus_01": {
                "name": "魔導ホムンクルス",
                "level": 1,
                "exp": 0,
                "is_injured": False,
                "equipped_skills": ["Analysis Helper"],
                "max_skill_slots": 3,
            },
        }

        # Step 19: 探索先ダンジョン定義
        self.dungeon_targets: Dict[str, Dict[str, Any]] = {
            "midas_scrap_dump": {
                "name": "ミダス廃棄物処分場",
                "difficulty": 1,
                "required_skill_types": ["Physical Attack"],
                "rewards": {"junk": 150, "skill_fragments": 2},
                "base_success_rate": 0.85,
            },
            "abandoned_reactor": {
                "name": "旧地下魔導炉跡地",
                "difficulty": 2,
                "required_skill_types": ["Stealth Digging", "Analysis Helper"],
                "rewards": {"junk": 400, "skill_fragments": 5, "rare_core": 1},
                "base_success_rate": 0.65,
            },
            "black_market_recon": {
                "name": "闇市場インテリジェンス偵察",
                "difficulty": 2,
                "required_skill_types": ["Analysis Helper"],
                "rewards": {"junk": 200, "market_forecast": ["Fire", "Ice"]},
                "base_success_rate": 0.75,
            },
            "rumor_manipulation": {
                "name": "情報操作（相場つり上げ工作）",
                "difficulty": 3,
                "required_skill_types": ["Stealth Digging", "Analysis Helper"],
                "rewards": {
                    "junk": 100,
                    "market_manipulation_applied": True,
                    "target_tag": "Combat",
                },
                "base_success_rate": 0.60,
            },
        }

        self.active_dispatches: Dict[str, Dict[str, Any]] = {}
        self.market_manipulation_cooldown: int = 0  # Step 47: クールダウン制御

    def equip_pet_skill(self, pet_id: str, skill_name: str) -> Dict[str, Any]:
        """ペットにスキルを装備"""
        if pet_id not in self.pets:
            return {"success": False, "message": f"Pet {pet_id} not found."}
        pet = self.pets[pet_id]
        if len(pet["equipped_skills"]) >= pet["max_skill_slots"]:
            return {"success": False, "message": "Skill slots are full."}
        pet["equipped_skills"].append(skill_name)
        return {"success": True, "pet": pet}

    def check_dispatch_suitability(self, pet_id: str, dungeon_id: str) -> Dict[str, Any]:
        """Step 20: 派遣に必要なスキル構成の適合度チェック"""
        if pet_id not in self.pets or dungeon_id not in self.dungeon_targets:
            return {"can_dispatch": False, "reason": "Invalid pet or dungeon"}

        pet = self.pets[pet_id]
        if pet["is_injured"]:
            return {"can_dispatch": False, "reason": "Pet is currently injured"}

        dungeon = self.dungeon_targets[dungeon_id]
        req_skills = dungeon["required_skill_types"]

        matched_skills = [s for s in req_skills if s in pet["equipped_skills"]]
        match_rate = len(matched_skills) / max(1, len(req_skills))

        return {
            "can_dispatch": True,
            "match_rate": match_rate,
            "matched_skills": matched_skills,
            "required_skills": req_skills,
        }

    def start_dispatch(
        self, pet_id: str, dungeon_id: str, duration_turns: int = 3
    ) -> Dict[str, Any]:
        """Step 21: 派遣開始と成功率計算"""
        suitability = self.check_dispatch_suitability(pet_id, dungeon_id)
        if not suitability.get("can_dispatch", False):
            return {"success": False, "message": suitability.get("reason", "Cannot dispatch")}

        if pet_id in self.active_dispatches:
            return {"success": False, "message": f"Pet {pet_id} is already on dispatch."}

        dungeon = self.dungeon_targets[dungeon_id]
        pet = self.pets[pet_id]

        # 成功率 = 基本成功率 + 適合度ボーナス + レベル補正
        success_rate = min(
            0.95,
            dungeon["base_success_rate"]
            + (suitability["match_rate"] * 0.20)
            + (pet["level"] * 0.02),
        )

        self.active_dispatches[pet_id] = {
            "dungeon_id": dungeon_id,
            "remaining_turns": duration_turns,
            "success_rate": success_rate,
            "total_duration": duration_turns,
        }
        return {
            "success": True,
            "pet_id": pet_id,
            "dungeon_name": dungeon["name"],
            "turns": duration_turns,
            "calculated_success_rate": success_rate,
        }

    def resolve_dispatch(self, pet_id: str, force_success: Optional[bool] = None) -> Dict[str, Any]:
        """Step 22 & 23: 探索完了時の報酬獲得または怪我ペナルティ"""
        if pet_id not in self.active_dispatches:
            return {"success": False, "message": "No active dispatch for this pet."}

        dispatch_info = self.active_dispatches.pop(pet_id)
        dungeon = self.dungeon_targets[dispatch_info["dungeon_id"]]
        pet = self.pets[pet_id]

        is_success = (
            force_success
            if force_success is not None
            else (random.random() <= dispatch_info["success_rate"])
        )

        if is_success:
            # 報酬獲得 & 経験値
            pet["exp"] += 50
            if pet["exp"] >= 100:
                pet["level"] += 1
                pet["exp"] -= 100

            return {
                "success": True,
                "result": "MISSION_ACCOMPLISHED",
                "rewards": dungeon["rewards"],
                "pet_level": pet["level"],
                "pet_exp": pet["exp"],
            }
        else:
            # 失敗と怪我
            pet["is_injured"] = True
            return {
                "success": False,
                "result": "MISSION_FAILED",
                "message": "Pet encountered heavy resistance and returned injured.",
                "pet_injured": True,
            }

    def treat_pet(self, pet_id: str, medical_junk_cost: int = 50) -> Dict[str, Any]:
        """Step 23: 怪我の治療"""
        if pet_id not in self.pets:
            return {"success": False, "message": "Pet not found."}
        pet = self.pets[pet_id]
        if not pet["is_injured"]:
            return {"success": False, "message": "Pet is not injured."}

        pet["is_injured"] = False
        return {
            "success": True,
            "message": f"{pet['name']} has been successfully treated and ready for dispatch.",
        }
