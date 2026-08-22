"""
Skill Eater Phase 5: Legacy Bequest System (Steps 16-19)
持ち込み枠や金庫に選ばれなかった全スキルをスラム街（レジスタンス）に寄付し、復興傾向スコアを算出。
"""

from typing import Any, Dict, List


class LegacyBequestManager:
    """
    レジスタンスへの遺産譲渡マネージャー
    """

    def __init__(self):
        self.donated_skills: List[Dict[str, Any]] = []
        self.bequest_scores: Dict[str, int] = {
            "Combat": 0,  # 武力
            "Recovery": 0,  # 治癒・防衛
            "Production": 0,  # 生産・魔力
        }

    def donate_leftover_skills(
        self, all_inventory: List[Dict[str, Any]], excluded_skill_names: List[str]
    ) -> Dict[str, Any]:
        """Step 17, 18, 19: 余剰スキルの抽出、寄付、スコアリング"""
        excluded_set = set(excluded_skill_names)
        leftovers = [s for s in all_inventory if s.get("name") not in excluded_set]

        self.donated_skills.extend(leftovers)

        # Step 19: タグに基づくスコアリング
        for skill in leftovers:
            tags = skill.get("tags", [])
            power = skill.get("power", 50)

            if any(t in ["Combat", "Sword", "Fire", "Destruction", "Physical"] for t in tags):
                self.bequest_scores["Combat"] += power
            if any(t in ["Recovery", "Heal", "Defense", "Barrier", "Shield"] for t in tags):
                self.bequest_scores["Recovery"] += power
            if any(t in ["Production", "Craft", "Magic", "Analysis", "Cyber"] for t in tags):
                self.bequest_scores["Production"] += power

        dominant_type = max(self.bequest_scores, key=self.bequest_scores.get)

        return {
            "success": True,
            "donated_count": len(leftovers),
            "bequest_scores": self.bequest_scores,
            "dominant_reconstruction_type": dominant_type,
            "message": f"BEQUEST DONATION COMPLETE: Donated {len(leftovers)} skills to the Slum Resistance.",
        }
