"""
Skill Eater Phase 2: Skill Rampage Events System (Steps 40-46)
極端に強力なスキル合成の失敗時、スキルが暴走して実体化・逃亡し、フィールドでミニボスとして徘徊するカオスイベントを管理。
"""

import random
from typing import Any, Dict, List


class SkillRampageManager:
    """
    スキル暴走（カオス・ネメシス）マネージャー
    """

    def __init__(self):
        self.active_rampages: Dict[str, Dict[str, Any]] = {}

    def calculate_rampage_chance(self, skill_tier: int, player_crafting_buff: float = 1.0) -> float:
        """Step 41: スキル合成時の暴走確率計算"""
        # 高Tierスキルほど暴走しやすい（Tier 3なら30%が基準、バフで軽減）
        base_chance = 0.10 * skill_tier
        effective_chance = max(0.02, base_chance * (2.0 - player_crafting_buff))
        return round(effective_chance, 3)

    def trigger_synthesis_with_rampage_check(
        self,
        skill_name: str,
        skill_tier: int,
        player_crafting_buff: float = 1.0,
        force_rampage: bool = False,
    ) -> Dict[str, Any]:
        """Step 42: 合成実行と暴走発生時のミニボススポーン予約"""
        chance = self.calculate_rampage_chance(skill_tier, player_crafting_buff)
        is_rampage = force_rampage or (random.random() < chance)

        if not is_rampage:
            return {
                "success": True,
                "rampage": False,
                "created_skill": skill_name,
                "message": f"Synthesis successful! Created [{skill_name}].",
            }

        # 暴走発生
        boss_id = f"rampage_{skill_name.lower().replace(' ', '_')}_{random.randint(100, 999)}"
        rampage_boss = {
            "boss_id": boss_id,
            "origin_skill": skill_name,
            "name": f"暴走変異体: 《{skill_name}の化身》",
            "hp": 1500 * skill_tier,
            "atk": 120 * skill_tier,
            "special_action": f"Uncontrolled Burst: {skill_name}",
            "location": "Slum Lower Depths",
            "time_limit_turns": 10,
            "is_defeated": False,
        }
        self.active_rampages[boss_id] = rampage_boss

        return {
            "success": False,
            "rampage": True,
            "message": f"CRITICAL HAZARD: Skill [{skill_name}] went out of control and materialized!",
            "spawned_boss": rampage_boss,
        }

    def wander_and_tick(self) -> List[Dict[str, Any]]:
        """Step 44 & 46: ミニボスの徘徊と時間制限による消滅"""
        expired = []
        for boss_id, boss in list(self.active_rampages.items()):
            boss["time_limit_turns"] -= 1
            if boss["time_limit_turns"] <= 0:
                expired.append(boss)
                del self.active_rampages[boss_id]
        return expired

    def defeat_rampage_boss(self, boss_id: str) -> Dict[str, Any]:
        """Step 45: ミニボス討伐時の安定化レアスキル獲得"""
        if boss_id not in self.active_rampages:
            return {"success": False, "message": "Rampage boss not found or already expired."}

        boss = self.active_rampages.pop(boss_id)
        stabilized_skill = f"Stabilized {boss['origin_skill']} (Pure Edition)"

        return {
            "success": True,
            "message": f"Defeated {boss['name']}! The chaotic energy condensed into a perfect form.",
            "reward_skill": stabilized_skill,
            "stat_bonus": "100% Stability Guarantee",
        }
