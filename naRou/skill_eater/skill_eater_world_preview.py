"""
Skill Eater Phase 4: World Preview & Solver Recommendation System (Steps 1-6)
次世界（W1魔法世界やW5サイバー世界等）の環境予兆を提示し、ソルバーが所持スキルに推奨タグを付与する。
"""

from typing import Any, Dict, List, Optional


class WorldPreviewManager:
    """
    次世界予兆と世界間ソルバー推奨システム
    """

    def __init__(self):
        # Step 2: 次世界候補の環境メタデータ定義
        self.next_worlds: Dict[str, Dict[str, Any]] = {
            "W1_Magic_Dominant": {
                "world_name": "W1: 魔法絶対主義の帝国",
                "preview_text": "【高魔力警報】魔力濃度が通常の10倍。物理攻撃が著しく減衰し、魔法障壁が主流。",
                "recommended_tags": ["Magic", "Barrier", "Anti-Magic", "Energy"],
                "disadvantaged_tags": ["Physical", "Heavy Armor"],
            },
            "W5_Cyber_Anarchy": {
                "world_name": "W5: 電脳無秩序スラム",
                "preview_text": "【電磁妨害警報】肉体改造とハッキングが必須。純粋な魔法詠唱は妨害される。",
                "recommended_tags": ["Hack", "Cyber", "Speed", "Analysis"],
                "disadvantaged_tags": ["Chant", "Spirit"],
            },
        }
        self.selected_target_world = "W1_Magic_Dominant"

    def get_world_preview(self, world_id: Optional[str] = None) -> Dict[str, Any]:
        """Step 3: 次世界の環境予兆テキストを抽出"""
        if world_id and world_id in self.next_worlds:
            self.selected_target_world = world_id

        world_info = self.next_worlds[self.selected_target_world]
        return {
            "world_id": self.selected_target_world,
            "name": world_info["world_name"],
            "preview": world_info["preview_text"],
            "recommended_tags": world_info["recommended_tags"],
        }

    def analyze_and_tag_skills(self, player_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 4 & 5: 所持スキルと次世界環境を照合し、推奨タグを付与"""
        target_info = self.next_worlds[self.selected_target_world]
        recommended_tags = set(target_info["recommended_tags"])
        disadvantaged_tags = set(target_info["disadvantaged_tags"])

        tagged_skills = []
        for skill in player_skills:
            skill_copy = dict(skill)
            skill_tags = set(skill.get("tags", []))

            # 推奨タグの判定
            is_recommended = bool(skill_tags.intersection(recommended_tags))
            is_disadvantaged = bool(skill_tags.intersection(disadvantaged_tags))

            skill_copy["solver_recommended"] = is_recommended
            skill_copy["solver_warning"] = is_disadvantaged

            if is_recommended:
                skill_copy["recommendation_badge"] = "[★次世界推奨]"
            elif is_disadvantaged:
                skill_copy["recommendation_badge"] = "[▲非推奨]"
            else:
                skill_copy["recommendation_badge"] = "[標準]"

            tagged_skills.append(skill_copy)

        return tagged_skills

    def generate_ui_skill_list(self, player_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 6: UI表示用スキルリスト生成"""
        tagged = self.analyze_and_tag_skills(player_skills)
        preview = self.get_world_preview()

        return {
            "target_world": preview["name"],
            "preview_description": preview["preview"],
            "skills": tagged,
            "recommended_count": sum(1 for s in tagged if s.get("solver_recommended")),
        }
