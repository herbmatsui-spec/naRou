#!/usr/bin/env python3
"""
Skill Tree System for naRou
Manages skill trees, tiers, effects, and player progression.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

try:
    from components import SkillTreeJobComponent
except Exception:  # pragma: no cover - optional dependency
    SkillTreeJobComponent = None


logger = logging.getLogger(__name__)


@dataclass
class SkillTreeEffect:
    """Represents a single effect from a skill tree tier."""

    type: str
    value: int | float | str
    target: str | None = None


@dataclass
class SkillTreeTier:
    """Represents a single tier in a skill tree."""

    id: str
    name: str
    description: str
    cost: int
    prerequisites: list[str] = field(default_factory=list)
    effects: list[SkillTreeEffect] = field(default_factory=list)


@dataclass
class SkillTree:
    """Represents a complete skill tree with multiple tiers."""

    id: str
    name: str
    icon: str
    tiers: list[SkillTreeTier] = field(default_factory=list)


class SkillTreeRegistry:
    """Singleton registry for loading and accessing skill trees."""

    _instance: Optional["SkillTreeRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._trees: dict[str, SkillTree] = {}
        self._initialized = True

    def load(self, path: str = "data/skill_trees.yaml") -> None:
        """Load skill trees from YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Skill tree file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load skill trees: {e}")
            return

        if not data or "skill_trees" not in data:
            logger.warning("No skill_trees key found in YAML")
            return

        self._trees.clear()
        for tree_id, tree_data in data["skill_trees"].items():
            if not isinstance(tree_data, dict):
                continue

            tiers = []
            for tier_data in tree_data.get("tiers", []):
                effects = []
                for eff_data in tier_data.get("effects", []):
                    effects.append(
                        SkillTreeEffect(
                            type=eff_data.get("type", ""),
                            value=eff_data.get("value", 0),
                            target=eff_data.get("target"),
                        )
                    )

                tiers.append(
                    SkillTreeTier(
                        id=tier_data.get("id", ""),
                        name=tier_data.get("name", ""),
                        description=tier_data.get("description", ""),
                        cost=tier_data.get("cost", 0),
                        prerequisites=tier_data.get("prerequisites", []),
                        effects=[
                            SkillTreeEffect(
                                type=e.get("type", ""),
                                value=e.get("value", 0),
                                target=e.get("target"),
                            )
                            for e in tier_data.get("effects", [])
                        ],
                    )
                )

            tree = SkillTree(
                id=tree_id,
                name=tree_data.get("name", ""),
                icon=tree_data.get("icon", ""),
                tiers=tiers,
            )
            self._trees[tree_id] = tree

        logger.info(f"Loaded {len(self._trees)} skill trees")

    def all(self) -> dict[str, "SkillTree"]:
        """Return all loaded skill trees."""
        return self._trees.copy()

    def get(self, tree_id: str) -> Optional["SkillTree"]:
        """Get a specific skill tree by ID."""
        return self._trees.get(tree_id)


class SkillTreeManager:
    """Manages player skill tree progression and learning."""

    def __init__(self, registry: SkillTreeRegistry):
        self.registry = registry

    def check_prerequisites(self, player, tier) -> bool:
        """
        Check if player meets all prerequisites for a tier.

        Args:
            player: Player entity with skill_tree_progress
            tier: SkillTreeTier to check

        Returns:
            True if all prerequisites are met, False otherwise
        """
        if not tier.prerequisites:
            return True

        tree_id = None
        for tree in self.registry.all().values():
            if tier in tree.tiers:
                tree_id = tree.id
                break

        if not tree_id:
            return False

        learned = player.skill_tree_progress.get(tree_id, [])
        return all(prereq in learned for prereq in tier.prerequisites)

    def learn_skill(self, player, tree_id: str, tier_id: str) -> bool:
        """
        Learn a skill tier.

        Args:
            player: Player entity
            tree_id: Skill tree ID
            tier_id: Tier ID to learn

        Returns:
            True if learned successfully, False otherwise
        """
        tree = self.registry.get(tree_id)
        if not tree:
            return False

        tier = next((t for t in tree.tiers if t.id == tier_id), None)
        if not tier:
            return False

        # Check prerequisites
        if not self.check_prerequisites(player, tier):
            return False

        # Check skill points
        if player.skill_points < tier.cost:
            return False

        # Check already learned
        learned = player.skill_tree_progress.get(tree_id, [])
        if tier.id in learned:
            return False

        # Learn the skill
        if tree_id not in player.skill_tree_progress:
            player.skill_tree_progress[tree_id] = []
        player.skill_tree_progress[tree_id].append(tier.id)
        player.skill_points -= tier.cost
        player.total_skill_points_earned += tier.cost

        # Apply effects (could be expanded)
        self._apply_tier_effects(player, tier)

        return True

    def _apply_tier_effects(self, player, tier):
        """Apply tier effects to player (placeholder for future expansion)."""
        pass

    def get_available_skills(self, player) -> list[dict]:
        """Get list of available (learnable) skills for player."""
        available = []

        for tree_id, tree in self.registry.all().items():
            learned = player.skill_tree_progress.get(tree_id, [])

            for tier in tree.tiers:
                if tier.id in learned:
                    continue

                if self.check_prerequisites(player, tier):
                    if player.skill_points >= tier.cost:
                        available.append(
                            {
                                "tree": tree.name,
                                "tree_id": tree.id,
                                "tier": tier.name,
                                "tier_id": tier.id,
                                "cost": tier.cost,
                                "effects": [
                                    {
                                        "type": e.type,
                                        "value": e.value,
                                        "target": e.target,
                                    }
                                    for e in tier.effects
                                ],
                            }
                        )

        return available

    def get_learned_skills(self, player) -> list[str]:
        """Get flat list of all learned skill IDs."""
        learned = []
        for tree_id, skills in player.skill_tree_progress.items():
            for skill_id in skills:
                if skill_id not in learned:
                    learned.append(skill_id)
                prefixed = f"{tree_id}:{skill_id}"
                if prefixed not in learned:
                    learned.append(prefixed)
        return learned

    def check_exclusive_learnable(self, player, skill_data: dict[str, Any]) -> bool:
        """Check if player can learn exclusive skill."""
        req_job = skill_data.get("job")
        if req_job and getattr(player, "job", None) != req_job:
            return False
        return True

    def learn_exclusive_skill(self, player, skill_id: str, cost: int = 5) -> bool:
        """Learn an exclusive skill."""
        if not hasattr(player, "mastered_exclusive_skills"):
            player.mastered_exclusive_skills = []
        if skill_id in player.mastered_exclusive_skills:
            return False
        if player.skill_points < cost:
            return False
        player.skill_points -= cost
        player.mastered_exclusive_skills.append(skill_id)
        return True


# Module-level registry instance
_skill_tree_registry: SkillTreeRegistry | None = None


def get_skill_tree_registry(path: str = "data/skill_trees.yaml") -> SkillTreeRegistry:
    """Get or create the default SkillTreeRegistry instance."""
    global _skill_tree_registry
    if _skill_tree_registry is None:
        _skill_tree_registry = SkillTreeRegistry()
        _skill_tree_registry.load(path)
    return _skill_tree_registry


def get_skill_tree_manager() -> SkillTreeManager:
    """Get a SkillTreeManager with the default registry."""
    registry = get_skill_tree_registry()
    return SkillTreeManager(registry)


# ============================================================
# Proposal 6: Passive Skills System
# ============================================================


@dataclass
class PassiveSkill:
    """A passive skill that applies constant effects when learned."""

    id: str
    name: str
    tree: str
    tier: int
    cost: int
    prerequisites: list[str] = field(default_factory=list)
    effects: list[SkillTreeEffect] = field(default_factory=list)


class PassiveSkillRegistry:
    """Loads and stores passive skill definitions from YAML."""

    _instance: Optional["PassiveSkillRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._skills: dict[str, PassiveSkill] = {}
        self._initialized = True

    def load(self, path: str = "data/passive_skills.yaml") -> None:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Passive skill file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load passive skills: {e}")
            return

        if not data or "passive_skills" not in data:
            logger.warning("No passive_skills key found in YAML")
            return

        self._skills.clear()
        for sid, sdata in data["passive_skills"].items():
            effects = [
                SkillTreeEffect(
                    type=e.get("type", ""),
                    value=e.get("value", 0),
                    target=e.get("target"),
                )
                for e in sdata.get("effects", [])
            ]
            self._skills[sid] = PassiveSkill(
                id=sid,
                name=sdata.get("name", ""),
                tree=sdata.get("tree", ""),
                tier=sdata.get("tier", 1),
                cost=sdata.get("cost", 0),
                prerequisites=sdata.get("prerequisites", []),
                effects=effects,
            )
        logger.info(f"Loaded {len(self._skills)} passive skills")

    def all(self) -> dict[str, PassiveSkill]:
        return self._skills.copy()

    def get(self, skill_id: str) -> PassiveSkill | None:
        return self._skills.get(skill_id)


class PassiveSkillManager:
    """Manages learning passive skills and aggregating their effects."""

    def __init__(self, registry: PassiveSkillRegistry):
        self.registry = registry

    def can_learn(self, player, skill_id: str) -> bool:
        skill = self.registry.get(skill_id)
        if skill is None:
            return False
        if skill_id in player.learned_passive_skills:
            return False
        if player.skill_points < skill.cost:
            return False
        comp = self._get_component(player)
        for prereq in skill.prerequisites:
            if prereq not in comp.learned_passive_skills:
                return False
        return True

    def learn(self, player, skill_id: str) -> bool:
        if not self.can_learn(player, skill_id):
            return False
        skill = self.registry.get(skill_id)
        comp = self._get_component(player)
        comp.learned_passive_skills.append(skill_id)
        player.skill_points -= skill.cost
        player.total_skill_points_earned += skill.cost
        return True

    def _get_component(self, player):
        # Entity exposes learned_passive_skills via SkillTreeJobComponent delegation
        if hasattr(player, "learned_passive_skills"):
            return player
        raise AttributeError("player has no learned_passive_skills")

    def aggregate_bonuses(self, player) -> dict[str, float]:
        """Sum all numeric passive effects for the player.

        Returns a dict of effect_type -> summed value. For chance-style
        effects (auto_revive), the value/sum is accumulated under its own key.
        """
        bonuses: dict[str, float] = {}
        learned = getattr(player, "learned_passive_skills", [])
        for sid in learned:
            skill = self.registry.get(sid)
            if skill is None:
                continue
            for eff in skill.effects:
                key = eff.type
                try:
                    val = float(eff.value)
                except (TypeError, ValueError):
                    continue
                bonuses[key] = bonuses.get(key, 0.0) + val
        return bonuses


_passive_registry: PassiveSkillRegistry | None = None


def get_passive_skill_registry(
    path: str = "data/passive_skills.yaml",
) -> PassiveSkillRegistry:
    global _passive_registry
    if _passive_registry is None:
        _passive_registry = PassiveSkillRegistry()
        _passive_registry.load(path)
    return _passive_registry


def get_passive_skill_manager() -> PassiveSkillManager:
    return PassiveSkillManager(get_passive_skill_registry())


# ============================================================
# Proposal 7: Skill Inheritance / Reincarnation Bonuses
# ============================================================


@dataclass
class InheritanceRule:
    """A single reincarnation inheritance rule."""

    id: str
    name: str
    description: str
    inheritance_type: str
    eligible_skills: list[str] = field(default_factory=list)
    inheritance_rate: float = 0.0
    level_bonus: int = 0
    requirements: dict[str, Any] = field(default_factory=dict)


class SkillInheritanceManager:
    """Loads inheritance rules and computes reincarnation bonuses."""

    def __init__(self, path: str = "data/skill_inheritance.yaml"):
        self._rules: dict[str, InheritanceRule] = {}
        self._path = path
        self.load(path)

    def load(self, path: str = "data/skill_inheritance.yaml") -> None:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Inheritance file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load inheritance rules: {e}")
            return

        self._rules.clear()
        for rid, rdata in (data or {}).get("inheritance_rules", {}).items():
            self._rules[rid] = InheritanceRule(
                id=rid,
                name=rdata.get("name", ""),
                description=rdata.get("description", ""),
                inheritance_type=rdata.get("inheritance_type", ""),
                eligible_skills=rdata.get("eligible_skills", []),
                inheritance_rate=float(rdata.get("inheritance_rate", 0.0)),
                level_bonus=int(rdata.get("level_bonus", 0)),
                requirements=rdata.get("requirements", {}) or {},
            )
        logger.info(f"Loaded {len(self._rules)} inheritance rules")

    def all_rules(self) -> dict[str, InheritanceRule]:
        return self._rules.copy()

    def available_rules(self, reincarnation_count: int) -> list[InheritanceRule]:
        """Rules whose reincarnation requirement is met."""
        out = []
        for rule in self._rules.values():
            req = rule.requirements.get("reincarnation_count", 0)
            if reincarnation_count >= int(req):
                out.append(rule)
        return out

    def compute_inheritance_points(
        self, level: int, mastered_jobs: int, awakened_skills: int
    ) -> int:
        """Compute total inheritance points (mirrors proposal formula)."""
        points = 10
        points += (level // 10) * 2
        points += mastered_jobs * 5
        points += awakened_skills * 10
        return points

    def apply_rule(self, player, rule_id: str) -> bool:
        """Apply an inheritance rule's starting bonus to a (new) player.

        Returns True if applied. Effects supported:
          - base_stat_bonus: adds level_bonus to a base stat (default 'level')
          - start_with_skill / start_with_job: recorded in inherited_skills
        """
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        comp = (
            player.get_component(SkillTreeJobComponent)
            if hasattr(player, "get_component")
            else player
        )
        if rule.inheritance_type == "potential_retention":
            # level_bonus becomes an inherited skill level head-start
            for sid in rule.eligible_skills:
                if sid not in comp.inherited_skills:
                    comp.inherited_skills.append(sid)
        elif rule.inheritance_type == "passive_traits":
            for sid in rule.eligible_skills:
                if sid not in comp.inherited_skills:
                    comp.inherited_skills.append(sid)
        # generic base stat bonus
        if rule.level_bonus:
            comp.inherited_stat_bonus = (
                getattr(comp, "inherited_stat_bonus", 0) + rule.level_bonus
            )
        return True


__all__ = [
    "SkillTreeEffect",
    "SkillTreeTier",
    "SkillTree",
    "SkillTreeRegistry",
    "SkillTreeManager",
    "PassiveSkill",
    "PassiveSkillRegistry",
    "PassiveSkillManager",
    "get_passive_skill_registry",
    "get_passive_skill_manager",
    "InheritanceRule",
    "SkillInheritanceManager",
]
