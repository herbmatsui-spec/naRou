from __future__ import annotations

from data.generated.skill.skill import SkillDefinition
from data.generated.skill.skill_fusion import SkillFusion
from data.generated.skill.skill_trees import SkillTier, SkillTree
from data.generated.skill.spells import Spell
from data.repositories.base import CachedRepository


class SkillRepository(CachedRepository[SkillDefinition, str]):
    """スキル・リポジトリ"""
    
    def __init__(self, skills: dict[str, SkillDefinition]):
        super().__init__(skills)
        self._by_category: dict[str, list[SkillDefinition]] = {}
        self._by_tree: dict[str, list[SkillDefinition]] = {}
        self._prerequisite_index: dict[str, list[SkillDefinition]] = {}
        self._build_indexes()
    
    def _build_indexes(self):
        for skill in self._data.values():
            self._by_category.setdefault(skill.category, []).append(skill)
            if skill.tree_id:
                self._by_tree.setdefault(skill.tree_id, []).append(skill)
            for prereq in skill.prerequisites:
                self._prerequisite_index.setdefault(prereq.root, []).append(skill)
    
    def get_by_category(self, category: str) -> list[SkillDefinition]:
        return self._by_category.get(category, [])
    
    def get_by_tree(self, tree_id: str) -> list[SkillDefinition]:
        return self._by_tree.get(tree_id, [])
    
    def get_dependents(self, skill_id: str) -> list[SkillDefinition]:
        """このスキルを前提条件とするスキル一覧"""
        return self._prerequisite_index.get(skill_id, [])
    
    def get_available_skills(self, learned_skills: set[str]) -> list[SkillDefinition]:
        """習得可能なスキル一覧 (前提条件を満たすもの)"""
        available = []
        for skill in self._data.values():
            if skill.id in learned_skills:
                continue
            if all(p.root in learned_skills for p in skill.prerequisites):
                available.append(skill)
        return available
    
    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_category.clear()
        self._by_tree.clear()
        self._prerequisite_index.clear()
        self._build_indexes()


class SkillTreeRepository(CachedRepository[SkillTree, str]):
    """スキルツリー・リポジトリ"""
    
    def __init__(self, trees: dict[str, SkillTree]):
        super().__init__(trees)
    
    def get_tree_skills(self, tree_id: str) -> list[SkillTier]:
        """ツリー内の全スキル取得 (フラット化)"""
        tree = self.get(tree_id)
        if not tree:
            return []
        skills = []
        for tier in tree.tiers:
            skills.append(tier)
        return skills


class SpellRepository(CachedRepository[Spell, str]):
    """呪文・リポジトリ"""

    def __init__(self, spells: dict[str, Spell]):
        super().__init__(spells)
        self._by_element: dict[str, list[Spell]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for spell in self._data.values():
            if spell.element:
                self._by_element.setdefault(spell.element, []).append(spell)

    def get_by_element(self, element: str) -> list[Spell]:
        return self._by_element.get(element, [])

    def get_by_target_type(self, target_type: str) -> list[Spell]:
        return [s for s in self._data.values() if s.target_type == target_type]

    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_element.clear()
        self._build_indexes()


class SkillFusionRepository(CachedRepository[SkillFusion, str]):
    """スキル融合・リポジトリ"""

    def __init__(self, fusions: dict[str, SkillFusion]):
        super().__init__(fusions)
        self._by_result: dict[str, list[SkillFusion]] = {}
        self._build_indexes()

    def _build_indexes(self):
        for fusion in self._data.values():
            for result in fusion.result_skills:
                key = result.root if hasattr(result, "root") else str(result)
                self._by_result.setdefault(key, []).append(fusion)

    def get_fusions_for_result(self, result_skill_id: str) -> list[SkillFusion]:
        return [f for f in self._by_result.get(result_skill_id, [])
                if any((getattr(r, "root", r) == result_skill_id) for r in f.result_skills)]

    def get_fusions_using_skill(self, skill_id: str) -> list[SkillFusion]:
        return [f for f in self._data.values()
                if any((getattr(s, "root", s) == skill_id) for s in f.required_skills)]


    def invalidate_cache(self):
        super().invalidate_cache()
        self._by_result.clear()
        self._build_indexes()


__all__ = ["SkillFusionRepository", "SkillRepository", "SkillTreeRepository", "SpellRepository"]