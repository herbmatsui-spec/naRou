"""
Skill Eater Phase 4: Concept Crystallization System (Steps 7-10)
同系統のスキル3つを消費して1つの「上位概念スキル（Concept）」に圧縮・統合し、持ち込み枠を節約する。
"""

from typing import Dict, Any, List, Optional

class ConceptCrystallizer:
    """
    概念結晶化マネージャー
    """
    def __init__(self):
        pass

    def crystallize_skills(self, category: str, skills_to_fuse: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 8, 9, 10: 3つのスキルを消費して1つの上位概念スキルを生成"""
        if len(skills_to_fuse) != 3:
            return {"success": False, "message": "Exactly 3 skills are required for Concept Crystallization."}

        # カテゴリの一致チェック
        for s in skills_to_fuse:
            if category not in s.get("tags", []):
                return {"success": False, "message": f"All 3 skills must share the [{category}] tag."}

        # パッシブ効果と威力の合算
        total_power = sum(s.get("power", 0) for s in skills_to_fuse)
        combined_passives = []
        for s in skills_to_fuse:
            if "passive" in s:
                combined_passives.append(s["passive"])

        concept_skill_name = f"Concept of Absolute {category} (純粋なる{category}の概念)"
        concept_skill = {
            "name": concept_skill_name,
            "category": category,
            "is_concept_crystal": True,
            "power": total_power + 100, # 結晶化ボーナス
            "tags": [category, "Concept", "Mastery", "Inherited"],
            "passives": combined_passives,
            "description": f"Three {category} skills compressed into a singular world-defying concept."
        }

        return {
            "success": True,
            "concept_skill": concept_skill,
            "message": f"CRYSTALLIZATION COMPLETE: Synthesized [{concept_skill_name}]!"
        }
