"""Unit tests for the small skill subsystem modules.

Covers:
- skill_evolution_system (registry + manager)
- skill_awakening_system (registry + manager)
- skill_specialization_system (registry + manager)
- skill_inheritance_system (registry + manager)
- skill_synergy_system (combo detection)
- skill_transfer_system (registry + manager)
- skill_resonance_system (registry + manager)
- legacy_skill_system (registry + manager)
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ecs.components import Skill

# =============================================================================
# Shared helpers
# =============================================================================


def fresh_registry(registry_cls):
    """Return a pristine registry instance, bypassing the module singleton."""
    registry_cls._instance = None
    return registry_cls()


def write_yaml(tmp_path, name: str, content: dict) -> str:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(content, allow_unicode=True), encoding="utf-8")
    return str(path)


class MockPlayer:
    """Plain object carrying every attribute the skill subsystems touch."""

    def __init__(self, **overrides):
        self.skills: dict[str, Skill] = {}
        self.level = 1
        self.attributes = types.SimpleNamespace(strength=10, magic=10, speed=10)
        self.skill_evolution: dict[str, str] = {}
        self.awakened_skills: list[str] = []
        self.monster_killed_types: dict[str, int] = {}
        self.piety = 0
        self.skill_specialization: dict[str, str] = {}
        self.inheritable_skills: list[str] = []
        self.recent_skills: list[tuple[str, int]] = []
        self.skill_points = 100
        self.gold = 10000
        self.skill_traits: dict[str, dict[str, float]] = {}
        self.equipped_skills: list[str] = []
        self.reincarnation_count = 0
        self.legacy_skills: list[str] = []
        for key, value in overrides.items():
            setattr(self, key, value)


@pytest.fixture
def player() -> MockPlayer:
    return MockPlayer()


@pytest.fixture
def engine() -> MagicMock:
    """Mock engine with a survival wallet, as the transfer system expects."""
    eng = MagicMock()
    eng.survival.gold = 50000
    return eng


# =============================================================================
# skill_evolution_system
# =============================================================================

from skill_evolution_system import (  # noqa: E402
    REGISTRY as EVOLUTION_REGISTRY,
)
from skill_evolution_system import (  # noqa: E402
    SkillEvolutionData,
    SkillEvolutionManager,
    SkillEvolutionRegistry,
)


def make_evolution_registry(tmp_path) -> SkillEvolutionRegistry:
    path = write_yaml(
        tmp_path,
        "evolution.yaml",
        {
            "evolution_chains": {
                "sword_mastery": {
                    "name": "剣術の進化の道",
                    "description": "sword chain",
                    "stages": [
                        {
                            "id": "s1",
                            "name": "剣術の心得",
                            "unlock_condition": {
                                "skill_level": {"swordsmanship": 10}
                            },
                            "bonuses": {"strength": 2},
                        },
                        {
                            "id": "s2",
                            "name": "百戦錬磨の刃",
                            "unlock_condition": {
                                "player_level": 20,
                                "skill_level": {"swordsmanship": 25},
                            },
                            "bonuses": {"strength": 5},
                        },
                        {"id": "s3", "name": "神速の剣聖"},
                    ],
                }
            }
        },
    )
    reg = fresh_registry(SkillEvolutionRegistry)
    reg.load(path)
    return reg


class TestSkillEvolutionData:
    def test_defaults(self):
        data = SkillEvolutionData(id="x")
        assert data.id == "x"
        assert data.name == ""
        assert data.stages == []


class TestSkillEvolutionRegistry:
    def test_load_parses_yaml_chains(self, tmp_path):
        reg = make_evolution_registry(tmp_path)
        chain = reg.get("sword_mastery")
        assert chain is not None
        assert chain.name == "剣術の進化の道"
        assert [s["id"] for s in chain.stages] == ["s1", "s2", "s3"]
        assert set(reg.all()) == {"sword_mastery"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillEvolutionRegistry)
        reg.load("no/such/file.yaml")
        chain = reg.get("sword_mastery")
        assert chain is not None
        assert chain.stages[0]["id"] == "sword_stage_1"

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillEvolutionRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_all_returns_copy(self, tmp_path):
        reg = make_evolution_registry(tmp_path)
        snapshot = reg.all()
        snapshot["junk"] = None
        assert "junk" not in reg.all()

    def test_singleton_returns_same_instance(self):
        SkillEvolutionRegistry._instance = None
        assert SkillEvolutionRegistry() is SkillEvolutionRegistry()


class TestSkillEvolutionManager:
    def test_first_stage_offered_when_no_progress(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skills["swordsmanship"] = Skill("swordsmanship", level=10)

        stage = manager.check_evolution(player, "sword_mastery")

        assert stage is not None
        assert stage["id"] == "s1"

    def test_next_stage_offered_when_requirements_met(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skill_evolution["sword_mastery"] = "s1"
        player.level = 20
        player.skills["swordsmanship"] = Skill("swordsmanship", level=25)

        stage = manager.check_evolution(player, "sword_mastery")

        assert stage is not None
        assert stage["id"] == "s2"

    def test_none_when_player_level_too_low(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skill_evolution["sword_mastery"] = "s1"
        player.level = 10
        player.skills["swordsmanship"] = Skill("swordsmanship", level=25)

        assert manager.check_evolution(player, "sword_mastery") is None

    def test_none_when_skill_level_too_low(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skills["swordsmanship"] = Skill("swordsmanship", level=5)

        assert manager.check_evolution(player, "sword_mastery") is None

    def test_none_when_required_skill_missing(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))

        assert manager.check_evolution(player, "sword_mastery") is None

    def test_none_when_final_stage_reached(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skill_evolution["sword_mastery"] = "s3"
        player.level = 99

        assert manager.check_evolution(player, "sword_mastery") is None

    def test_none_for_unknown_chain(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))

        assert manager.check_evolution(player, "unknown_chain") is None

    def test_none_for_missing_player(self, tmp_path):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))

        assert manager.check_evolution(None, "sword_mastery") is None

    def test_evolve_applies_bonuses_and_records_stage(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skills["swordsmanship"] = Skill("swordsmanship", level=10)

        assert manager.evolve_skill(player, "sword_mastery") is True
        assert player.skill_evolution["sword_mastery"] == "s1"
        assert player.attributes.strength == 12

    def test_evolve_fails_and_does_not_mutate_when_blocked(self, tmp_path, player):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skills["swordsmanship"] = Skill("swordsmanship", level=1)

        assert manager.evolve_skill(player, "sword_mastery") is False
        assert player.skill_evolution == {}
        assert player.attributes.strength == 10

    def test_evolve_with_engine_logs_and_plays_se(self, tmp_path, player, engine):
        manager = SkillEvolutionManager(make_evolution_registry(tmp_path))
        player.skills["swordsmanship"] = Skill("swordsmanship", level=10)

        with patch("sound_manager.SoundManager") as mock_sm:
            result = manager.evolve_skill(player, "sword_mastery", engine=engine)

        assert result is True
        mock_sm.play_se.assert_called_once_with("level_up")
        assert engine.log.called
        assert player.skill_evolution["sword_mastery"] == "s1"

    def test_default_registry_used_when_none_passed(self):
        manager = SkillEvolutionManager()
        assert manager.registry is EVOLUTION_REGISTRY


# =============================================================================
# skill_awakening_system
# =============================================================================

from skill_awakening_system import (  # noqa: E402
    SkillAwakeningData,
    SkillAwakeningManager,
    SkillAwakeningRegistry,
)


def make_awakening_registry(tmp_path) -> SkillAwakeningRegistry:
    path = write_yaml(
        tmp_path,
        "awakening.yaml",
        {
            "awakenings": {
                "dragon_slaying_awakening": {
                    "name": "竜殺しの覚醒",
                    "base_skill": "swordsmanship",
                    "requirements": {
                        "skill_level": {"swordsmanship": 30},
                        "dragon_kills": 5,
                    },
                    "awakened_skill": "true_dragon_slayer",
                    "visual_effect": "dragon_aura_crimson",
                    "passive_effects": {"dragon_dmg_multiplier": 2.0},
                },
                "divine_awakening": {
                    "name": "神聖魔導の覚醒",
                    "base_skill": "magic_cast",
                    "requirements": {
                        "skill_level": {"magic_cast": 30},
                        "piety": 100,
                    },
                    "awakened_skill": "divine_arcanum",
                },
            }
        },
    )
    reg = fresh_registry(SkillAwakeningRegistry)
    reg.load(path)
    return reg


class TestSkillAwakeningRegistry:
    def test_load_parses_yaml_awakenings(self, tmp_path):
        reg = make_awakening_registry(tmp_path)
        data = reg.get("dragon_slaying_awakening")
        assert data is not None
        assert data.base_skill == "swordsmanship"
        assert data.awakened_skill == "true_dragon_slayer"
        assert data.requirements["dragon_kills"] == 5
        assert data.passive_effects == {"dragon_dmg_multiplier": 2.0}
        assert set(reg.all()) == {"dragon_slaying_awakening", "divine_awakening"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillAwakeningRegistry)
        reg.load("no/such/file.yaml")
        data = reg.get("dragon_slaying_awakening")
        assert data is not None
        assert data.awakened_skill == "true_dragon_slayer"

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillAwakeningRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = SkillAwakeningData(id="x")
        assert data.requirements == {}
        assert data.passive_effects == {}
        assert data.awakened_skill == ""


class TestSkillAwakeningManager:
    def _eligible_player(self) -> MockPlayer:
        return MockPlayer(
            skills={"swordsmanship": Skill("swordsmanship", level=30)},
            monster_killed_types={"dragon": 5},
        )

    def test_can_awaken_true_when_all_requirements_met(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))

        assert manager.can_awaken(self._eligible_player(), "dragon_slaying_awakening") is True

    def test_can_awaken_false_when_already_awakened(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = self._eligible_player()
        player.awakened_skills.append("dragon_slaying_awakening")

        assert manager.can_awaken(player, "dragon_slaying_awakening") is False

    def test_can_awaken_false_when_skill_level_low(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer(
            skills={"swordsmanship": Skill("swordsmanship", level=10)},
            monster_killed_types={"dragon": 5},
        )

        assert manager.can_awaken(player, "dragon_slaying_awakening") is False

    def test_can_awaken_false_when_skill_missing(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer(monster_killed_types={"dragon": 5})

        assert manager.can_awaken(player, "dragon_slaying_awakening") is False

    def test_can_awaken_false_when_dragon_kills_short(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer(
            skills={"swordsmanship": Skill("swordsmanship", level=30)},
            monster_killed_types={"dragon": 2},
        )

        assert manager.can_awaken(player, "dragon_slaying_awakening") is False

    def test_can_awaken_false_when_piety_short(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer(
            skills={"magic_cast": Skill("magic_cast", level=30)},
            piety=50,
        )

        assert manager.can_awaken(player, "divine_awakening") is False

    def test_can_awaken_true_when_piety_met(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer(
            skills={"magic_cast": Skill("magic_cast", level=30)},
            piety=100,
        )

        assert manager.can_awaken(player, "divine_awakening") is True

    def test_can_awaken_false_for_unknown_id(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))

        assert manager.can_awaken(self._eligible_player(), "nope") is False

    def test_can_awaken_false_for_missing_player(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))

        assert manager.can_awaken(None, "dragon_slaying_awakening") is False

    def test_awaken_grants_skill_and_bridges_to_spellbook(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = self._eligible_player()
        player.character_state = MagicMock()

        assert manager.awaken_skill(player, "dragon_slaying_awakening") is True
        assert player.awakened_skills == ["dragon_slaying_awakening"]
        awakened = player.skills["true_dragon_slayer"]
        assert isinstance(awakened, Skill)
        assert awakened.level == 1
        slot = player.character_state.skills.__setitem__.call_args[0]
        assert slot[0] == "true_dragon_slayer"
        assert slot[1].skill_id == "true_dragon_slayer"
        player.character_state.calculate_memory_usage.assert_called_once()

    def test_awaken_blocked_when_requirements_unmet(self, tmp_path):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = MockPlayer()

        assert manager.awaken_skill(player, "dragon_slaying_awakening") is False
        assert player.awakened_skills == []
        assert "true_dragon_slayer" not in player.skills

    def test_awaken_with_engine_logs_and_plays_se(self, tmp_path, engine):
        manager = SkillAwakeningManager(make_awakening_registry(tmp_path))
        player = self._eligible_player()
        player.character_state = MagicMock()

        with patch("sound_manager.SoundManager") as mock_sm:
            result = manager.awaken_skill(
                player, "dragon_slaying_awakening", engine=engine
            )

        assert result is True
        mock_sm.play_se.assert_called_once_with("level_up")
        assert engine.log.called

    def test_default_registry_used_when_none_passed(self, tmp_path):
        manager = SkillAwakeningManager()
        reg = fresh_registry(SkillAwakeningRegistry)
        reg.load("no/such/file.yaml")
        other = SkillAwakeningManager(reg)
        assert other.registry is reg
        assert manager.registry is not reg


# =============================================================================
# skill_specialization_system
# =============================================================================

from skill_specialization_system import (  # noqa: E402
    SkillSpecializationData,
    SkillSpecializationManager,
    SkillSpecializationRegistry,
)


def make_specialization_registry(tmp_path) -> SkillSpecializationRegistry:
    path = write_yaml(
        tmp_path,
        "specialization.yaml",
        {
            "specialization_paths": {
                "fireball_specialization": {
                    "name": "火炎魔導専門化パス",
                    "description": "fire path",
                    "base_skill": "magic_cast",
                    "branches": [
                        {"id": "inferno", "name": "業火"},
                        {"id": "frost", "name": "氷結"},
                    ],
                }
            }
        },
    )
    reg = fresh_registry(SkillSpecializationRegistry)
    reg.load(path)
    return reg


class TestSkillSpecializationRegistry:
    def test_load_parses_yaml_paths(self, tmp_path):
        reg = make_specialization_registry(tmp_path)
        path = reg.get("fireball_specialization")
        assert path is not None
        assert path.base_skill == "magic_cast"
        assert [b["id"] for b in path.branches] == ["inferno", "frost"]
        assert set(reg.all()) == {"fireball_specialization"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillSpecializationRegistry)
        reg.load("no/such/file.yaml")
        path = reg.get("fireball_specialization")
        assert path is not None
        assert path.base_skill == "magic_cast"
        assert path.branches == []

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillSpecializationRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = SkillSpecializationData(id="x")
        assert data.base_skill == ""
        assert data.branches == []


class TestSkillSpecializationManager:
    def _player_with_base_skill(self) -> MockPlayer:
        return MockPlayer(skills={"magic_cast": Skill("magic_cast", level=20)})

    def test_can_specialize_true_for_known_branch(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))

        assert (
            manager.can_specialize(
                self._player_with_base_skill(), "fireball_specialization", "inferno"
            )
            is True
        )

    def test_can_specialize_false_when_base_skill_missing(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))

        assert (
            manager.can_specialize(MockPlayer(), "fireball_specialization", "inferno")
            is False
        )

    def test_can_specialize_false_for_unknown_branch(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))

        assert (
            manager.can_specialize(
                self._player_with_base_skill(), "fireball_specialization", "nope"
            )
            is False
        )

    def test_can_specialize_false_for_unknown_path(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))

        assert (
            manager.can_specialize(
                self._player_with_base_skill(), "unknown_path", "inferno"
            )
            is False
        )

    def test_can_specialize_false_for_missing_player(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))

        assert manager.can_specialize(None, "fireball_specialization", "inferno") is False

    def test_specialize_records_branch(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))
        player = self._player_with_base_skill()

        assert (
            manager.specialize_skill(player, "fireball_specialization", "inferno")
            is True
        )
        assert player.skill_specialization == {"fireball_specialization": "inferno"}

    def test_specialize_blocked_when_base_skill_missing(self, tmp_path):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))
        player = MockPlayer()

        assert (
            manager.specialize_skill(player, "fireball_specialization", "inferno")
            is False
        )
        assert player.skill_specialization == {}

    def test_specialize_with_engine_logs_and_plays_se(self, tmp_path, engine):
        manager = SkillSpecializationManager(make_specialization_registry(tmp_path))
        player = self._player_with_base_skill()

        with patch("sound_manager.SoundManager") as mock_sm:
            result = manager.specialize_skill(
                player, "fireball_specialization", "inferno", engine=engine
            )

        assert result is True
        mock_sm.play_se.assert_called_once_with("level_up")
        assert engine.log.called


# =============================================================================
# skill_inheritance_system
# =============================================================================

from skill_inheritance_system import (  # noqa: E402
    SkillInheritanceData,
    SkillInheritanceManager,
    SkillInheritanceRegistry,
)


def make_inheritance_registry(tmp_path) -> SkillInheritanceRegistry:
    path = write_yaml(
        tmp_path,
        "inheritance.yaml",
        {
            "inheritance_rules": {
                "bloodline_skills": {
                    "name": "血統スキル継承",
                    "inheritance_type": "bloodline",
                    "eligible_skills": ["martial_arts", "swordsmanship"],
                    "inheritance_rate": 0.75,
                    "level_bonus": 8,
                    "requirements": {"reincarnation": 1},
                }
            }
        },
    )
    reg = fresh_registry(SkillInheritanceRegistry)
    reg.load(path)
    return reg


class TestSkillInheritanceRegistry:
    def test_load_parses_yaml_rules(self, tmp_path):
        reg = make_inheritance_registry(tmp_path)
        rule = reg.get("bloodline_skills")
        assert rule is not None
        assert rule.eligible_skills == ["martial_arts", "swordsmanship"]
        assert rule.inheritance_rate == 0.75
        assert rule.level_bonus == 8
        assert rule.requirements == {"reincarnation": 1}
        assert set(reg.all()) == {"bloodline_skills"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillInheritanceRegistry)
        reg.load("no/such/file.yaml")
        rule = reg.get("bloodline_skills")
        assert rule is not None
        assert rule.inheritance_rate == 0.50
        assert rule.level_bonus == 5

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillInheritanceRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = SkillInheritanceData(id="x")
        assert data.inheritance_rate == 0.50
        assert data.level_bonus == 5
        assert data.eligible_skills == []


class TestSkillInheritanceManager:
    def test_get_inheritable_skills_returns_owned_subset(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))
        player = MockPlayer(
            skills={
                "martial_arts": Skill("martial_arts", level=12),
                "alchemy": Skill("alchemy", level=5),
            }
        )

        assert manager.get_inheritable_skills(player) == ["martial_arts"]

    def test_get_inheritable_skills_empty_when_none_owned(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))

        assert manager.get_inheritable_skills(MockPlayer()) == []

    def test_get_inheritable_skills_unknown_rule(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))

        assert manager.get_inheritable_skills(MockPlayer(), rule_id="nope") == []

    def test_get_inheritable_skills_missing_player(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))

        assert manager.get_inheritable_skills(None) == []

    def test_inherit_skill_appends_to_inheritable(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))
        player = MockPlayer()

        assert manager.inherit_skill(player, "swordsmanship") is True
        assert player.inheritable_skills == ["swordsmanship"]

    def test_inherit_skill_does_not_duplicate(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))
        player = MockPlayer()
        manager.inherit_skill(player, "swordsmanship")

        assert manager.inherit_skill(player, "swordsmanship") is True
        assert player.inheritable_skills == ["swordsmanship"]

    def test_inherit_skill_rejects_ineligible_skill(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))
        player = MockPlayer()

        assert manager.inherit_skill(player, "alchemy") is False
        assert player.inheritable_skills == []

    def test_inherit_skill_unknown_rule(self, tmp_path):
        manager = SkillInheritanceManager(make_inheritance_registry(tmp_path))
        player = MockPlayer()

        assert manager.inherit_skill(player, "swordsmanship", rule_id="nope") is False


# =============================================================================
# skill_synergy_system
# =============================================================================

from skill_synergy_system import (  # noqa: E402
    SkillSynergyManager,
    Synergy,
    SynergyEffect,
)


def make_synergy_manager(tmp_path) -> SkillSynergyManager:
    path = write_yaml(
        tmp_path,
        "synergy.yaml",
        {
            "synergies": {
                "fire_tornado": {
                    "name": "火炎竜巻",
                    "skills": ["fireball", "wind_blade"],
                    "window": 3,
                    "effect": [
                        {
                            "type": "aoe_damage",
                            "radius": 3,
                            "formula": "(int + dex) * 2",
                            "element": "fire_wind",
                        },
                        {"type": "status", "effect": "burn", "duration": 3},
                    ],
                }
            }
        },
    )
    return SkillSynergyManager(path)


class TestSkillSynergyManager:
    def test_load_parses_synergies_and_effects(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        syn = manager.all()["fire_tornado"]
        assert isinstance(syn, Synergy)
        assert syn.skills == ["fireball", "wind_blade"]
        assert syn.window == 3
        assert len(syn.effects) == 2
        first = syn.effects[0]
        assert isinstance(first, SynergyEffect)
        assert first.type == "aoe_damage"
        assert first.radius == 3
        assert first.element == "fire_wind"
        assert syn.effects[1].effect == "burn"
        assert syn.effects[1].duration == 3

    def test_load_missing_file_leaves_registry_empty(self, tmp_path):
        manager = SkillSynergyManager(str(tmp_path / "missing.yaml"))

        assert manager.all() == {}

    def test_load_broken_yaml_leaves_registry_empty(self, tmp_path):
        bad = tmp_path / "broken.yaml"
        bad.write_text("synergies: [unclosed", encoding="utf-8")

        manager = SkillSynergyManager(str(bad))

        assert manager.all() == {}

    def test_register_skill_use_appends_history(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        player = MockPlayer()

        manager.register_skill_use(player, "fireball", turn=10)

        assert player.recent_skills == [("fireball", 10)]

    def test_register_skill_use_creates_history_when_absent(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        player = types.SimpleNamespace()

        manager.register_skill_use(player, "fireball", turn=1)

        assert player.recent_skills == [("fireball", 1)]

    def test_evaluate_triggers_when_all_skills_in_window(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        player = MockPlayer()
        player.recent_skills = [("fireball", 10), ("wind_blade", 12)]

        triggered = manager.evaluate(player, turn=12)

        assert [s.id for s in triggered] == ["fire_tornado"]

    def test_evaluate_ignores_uses_outside_window(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        player = MockPlayer()
        player.recent_skills = [("fireball", 5), ("wind_blade", 12)]

        assert manager.evaluate(player, turn=12) == []

    def test_evaluate_ignores_partial_skill_sets(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        player = MockPlayer()
        player.recent_skills = [("fireball", 10)]

        assert manager.evaluate(player, turn=12) == []

    def test_evaluate_empty_without_history(self, tmp_path):
        manager = make_synergy_manager(tmp_path)

        assert manager.evaluate(MockPlayer(), turn=1) == []

    def test_evaluate_empty_without_synergies(self, tmp_path):
        manager = SkillSynergyManager(str(tmp_path / "missing.yaml"))
        player = MockPlayer()
        player.recent_skills = [("fireball", 1)]

        assert manager.evaluate(player, turn=1) == []

    def test_all_returns_copy(self, tmp_path):
        manager = make_synergy_manager(tmp_path)
        snapshot = manager.all()
        snapshot["junk"] = None
        assert "junk" not in manager.all()


# =============================================================================
# skill_transfer_system
# =============================================================================

from skill_transfer_system import (  # noqa: E402
    SkillTransferData,
    SkillTransferManager,
    SkillTransferRegistry,
)


def make_transfer_registry(tmp_path) -> SkillTransferRegistry:
    path = write_yaml(
        tmp_path,
        "transfer.yaml",
        {
            "transfer_traits": {
                "critical_boost": {
                    "name": "急所看破の転移",
                    "source_traits": ["crit_bonus"],
                    "target_skills": ["martial_arts", "swordsmanship"],
                    "transfer_ratio": 0.8,
                    "cost": {"skill_points": 20, "gold": 5000},
                    "irreversible": True,
                }
            }
        },
    )
    reg = fresh_registry(SkillTransferRegistry)
    reg.load(path)
    return reg


class TestSkillTransferRegistry:
    def test_load_parses_yaml_traits(self, tmp_path):
        reg = make_transfer_registry(tmp_path)
        data = reg.get("critical_boost")
        assert data is not None
        assert data.source_traits == ["crit_bonus"]
        assert data.target_skills == ["martial_arts", "swordsmanship"]
        assert data.transfer_ratio == 0.8
        assert data.cost == {"skill_points": 20, "gold": 5000}
        assert data.irreversible is True
        assert set(reg.all()) == {"critical_boost"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillTransferRegistry)
        reg.load("no/such/file.yaml")
        data = reg.get("critical_boost")
        assert data is not None
        assert data.transfer_ratio == 0.80
        assert data.irreversible is True

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillTransferRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = SkillTransferData(id="x")
        assert data.transfer_ratio == 0.80
        assert data.cost == {}
        assert data.irreversible is True


class TestSkillTransferManager:
    def _player_with_target(self, **overrides) -> MockPlayer:
        return MockPlayer(
            skills={"swordsmanship": Skill("swordsmanship", level=15)}, **overrides
        )

    def test_can_transfer_true_when_all_requirements_met(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert manager.can_transfer(self._player_with_target(), "critical_boost", "swordsmanship") is True

    def test_can_transfer_false_for_unknown_trait(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert manager.can_transfer(self._player_with_target(), "nope", "swordsmanship") is False

    def test_can_transfer_false_for_disallowed_target(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert manager.can_transfer(self._player_with_target(), "critical_boost", "alchemy") is False

    def test_can_transfer_false_when_target_not_owned(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert manager.can_transfer(MockPlayer(), "critical_boost", "swordsmanship") is False

    def test_can_transfer_false_when_skill_points_short(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert (
            manager.can_transfer(
                self._player_with_target(skill_points=5), "critical_boost", "swordsmanship"
            )
            is False
        )

    def test_can_transfer_false_when_gold_short(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert (
            manager.can_transfer(
                self._player_with_target(gold=100), "critical_boost", "swordsmanship"
            )
            is False
        )

    def test_can_transfer_uses_engine_wallet_when_available(self, tmp_path, engine):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert (
            manager.can_transfer(
                self._player_with_target(gold=0), "critical_boost", "swordsmanship", engine
            )
            is True
        )

    def test_can_transfer_false_for_missing_player(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))

        assert manager.can_transfer(None, "critical_boost", "swordsmanship") is False

    def test_transfer_trait_deducts_costs_and_records_ratio(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))
        player = self._player_with_target()

        assert manager.transfer_trait(player, "critical_boost", "swordsmanship") is True
        assert player.skill_points == 80
        assert player.gold == 5000
        assert player.skill_traits["swordsmanship"]["critical_boost"] == 0.8

    def test_transfer_trait_does_not_duplicate_entry(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))
        player = self._player_with_target(skill_points=40)
        manager.transfer_trait(player, "critical_boost", "swordsmanship")

        assert manager.transfer_trait(player, "critical_boost", "swordsmanship") is True
        assert player.skill_traits["swordsmanship"]["critical_boost"] == 0.8

    def test_transfer_trait_with_engine_deducts_both_wallets(self, tmp_path, engine):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))
        player = self._player_with_target()

        with patch("sound_manager.SoundManager"):
            assert (
                manager.transfer_trait(player, "critical_boost", "swordsmanship", engine)
                is True
            )

        assert player.gold == 5000
        assert engine.survival.gold == 45000
        assert engine.log.called

    def test_transfer_trait_blocked_leaves_wallets_intact(self, tmp_path):
        manager = SkillTransferManager(make_transfer_registry(tmp_path))
        player = self._player_with_target(gold=100)

        assert manager.transfer_trait(player, "critical_boost", "swordsmanship") is False
        assert player.gold == 100
        assert player.skill_points == 100
        assert player.skill_traits == {}

    def test_transfer_trait_zero_gold_cost_keeps_wallet(self, tmp_path):
        path = write_yaml(
            tmp_path,
            "transfer_free.yaml",
            {
                "transfer_traits": {
                    "free_boost": {
                        "name": "無償の転移",
                        "target_skills": ["swordsmanship"],
                        "transfer_ratio": 0.5,
                        "cost": {},
                    }
                }
            },
        )
        reg = fresh_registry(SkillTransferRegistry)
        reg.load(path)
        manager = SkillTransferManager(reg)
        player = self._player_with_target()

        assert manager.transfer_trait(player, "free_boost", "swordsmanship") is True
        assert player.gold == 10000
        assert player.skill_points == 100


# =============================================================================
# skill_resonance_system
# =============================================================================

from skill_resonance_system import (  # noqa: E402
    SkillResonanceData,
    SkillResonanceManager,
    SkillResonanceRegistry,
)


def make_resonance_registry(tmp_path) -> SkillResonanceRegistry:
    path = write_yaml(
        tmp_path,
        "resonance.yaml",
        {
            "resonance_sets": {
                "flame_knight_set": {
                    "name": "炎の騎士セット",
                    "required_skills": ["swordsmanship", "magic_cast"],
                    "min_count": 2,
                    "resonance_effects": {"fire_dmg_boost": 10},
                    "visual_effect": "flame_aura",
                },
                "trio_set": {
                    "name": "三重奏",
                    "required_skills": ["swordsmanship", "magic_cast", "holy_slash"],
                    "min_count": 3,
                    "resonance_effects": {"fire_dmg_boost": 3, "all_boost": 5},
                },
            }
        },
    )
    reg = fresh_registry(SkillResonanceRegistry)
    reg.load(path)
    return reg


class TestSkillResonanceRegistry:
    def test_load_parses_yaml_sets(self, tmp_path):
        reg = make_resonance_registry(tmp_path)
        data = reg.get("flame_knight_set")
        assert data is not None
        assert data.required_skills == ["swordsmanship", "magic_cast"]
        assert data.min_count == 2
        assert data.resonance_effects == {"fire_dmg_boost": 10}
        assert data.visual_effect == "flame_aura"
        assert set(reg.all()) == {"flame_knight_set", "trio_set"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(SkillResonanceRegistry)
        reg.load("no/such/file.yaml")
        data = reg.get("flame_knight_set")
        assert data is not None
        assert data.required_skills == ["swordsmanship", "magic_cast"]

    def test_get_unknown_returns_none(self):
        reg = fresh_registry(SkillResonanceRegistry)
        reg.load("no/such/file.yaml")
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = SkillResonanceData(id="x")
        assert data.min_count == 2
        assert data.required_skills == []
        assert data.resonance_effects == {}


class TestSkillResonanceManager:
    def test_check_resonance_active_when_min_count_met(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))
        player = MockPlayer(
            skills={
                "swordsmanship": Skill("swordsmanship", level=10),
                "magic_cast": Skill("magic_cast", level=10),
            }
        )

        active = manager.check_resonance(player)
        assert [s.id for s in active] == ["flame_knight_set"]

    def test_check_resonance_counts_equipped_skills(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))
        player = MockPlayer(equipped_skills=["swordsmanship", "magic_cast"])

        active = manager.check_resonance(player)
        assert [s.id for s in active] == ["flame_knight_set"]

    def test_check_resonance_inactive_below_min_count(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))
        player = MockPlayer(
            skills={"swordsmanship": Skill("swordsmanship", level=10)}
        )

        assert manager.check_resonance(player) == []

    def test_check_resonance_multiple_sets_when_all_skills_owned(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))
        player = MockPlayer(
            skills={
                "swordsmanship": Skill("swordsmanship", level=10),
                "magic_cast": Skill("magic_cast", level=10),
                "holy_slash": Skill("holy_slash", level=10),
            }
        )

        active = manager.check_resonance(player)
        assert {s.id for s in active} == {"flame_knight_set", "trio_set"}

    def test_check_resonance_missing_player(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))

        assert manager.check_resonance(None) == []

    def test_apply_resonance_effects_merges_and_sums(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))
        player = MockPlayer(
            skills={
                "swordsmanship": Skill("swordsmanship", level=10),
                "magic_cast": Skill("magic_cast", level=10),
                "holy_slash": Skill("holy_slash", level=10),
            }
        )

        merged = manager.apply_resonance_effects(player)
        assert merged == {"fire_dmg_boost": 13, "all_boost": 5}

    def test_apply_resonance_effects_empty_when_inactive(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))

        assert manager.apply_resonance_effects(MockPlayer()) == {}

    def test_remove_resonance_effects_is_safe_noop(self, tmp_path):
        manager = SkillResonanceManager(make_resonance_registry(tmp_path))

        assert manager.remove_resonance_effects(MockPlayer()) is None


# =============================================================================
# legacy_skill_system
# =============================================================================

from legacy_skill_system import (  # noqa: E402
    LegacySkillData,
    LegacySkillManager,
    LegacySkillRegistry,
)


def make_legacy_registry(tmp_path) -> LegacySkillRegistry:
    path = write_yaml(
        tmp_path,
        "legacy.yaml",
        {
            "legacy_skills": {
                "soul_memory": {
                    "min_reincarnation": 1,
                    "name": "魂の記憶",
                    "effect_type": "skill_exp_boost",
                    "effect_value": 0.15,
                    "unlock_condition": {"reincarnation_count": 1},
                },
                "iron_will": {
                    "min_reincarnation": 5,
                    "name": "鉄意志",
                    "effect_type": "skill_exp_boost",
                    "effect_value": 0.10,
                },
            }
        },
    )
    reg = fresh_registry(LegacySkillRegistry)
    reg.load(path)
    return reg


class TestLegacySkillRegistry:
    def test_load_parses_yaml_skills(self, tmp_path):
        reg = make_legacy_registry(tmp_path)
        data = reg.get("soul_memory")
        assert data is not None
        assert data.min_reincarnation == 1
        assert data.effect_type == "skill_exp_boost"
        assert data.effect_value == 0.15
        assert data.unlock_condition == {"reincarnation_count": 1}
        assert set(reg.all()) == {"soul_memory", "iron_will"}

    def test_load_missing_file_falls_back_to_default(self):
        reg = fresh_registry(LegacySkillRegistry)
        reg.load("no/such/file.yaml")
        assert set(reg.all()) == {"soul_memory"}
        assert reg.get("soul_memory").effect_value == 0.15

    def test_load_broken_yaml_falls_back_to_default(self, tmp_path):
        bad = tmp_path / "broken.yaml"
        bad.write_text("legacy_skills: [unclosed", encoding="utf-8")

        reg = fresh_registry(LegacySkillRegistry)
        reg.load(str(bad))

        assert set(reg.all()) == {"soul_memory"}

    def test_load_yaml_without_legacy_skills_key_falls_back(self, tmp_path):
        path = write_yaml(tmp_path, "other.yaml", {"something_else": {}})

        reg = fresh_registry(LegacySkillRegistry)
        reg.load(path)

        assert set(reg.all()) == {"soul_memory"}

    def test_singleton_returns_same_instance(self):
        LegacySkillRegistry._instance = None
        assert LegacySkillRegistry() is LegacySkillRegistry()

    def test_get_unknown_returns_none(self, tmp_path):
        reg = make_legacy_registry(tmp_path)
        assert reg.get("nope") is None

    def test_data_defaults(self):
        data = LegacySkillData(id="x", min_reincarnation=3)
        assert data.name == ""
        assert data.effect_type == ""
        assert data.effect_value is None


class TestLegacySkillManager:
    def test_apply_effects_returns_base_when_no_match(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=5)

        assert manager.apply_legacy_effects(player, effect_type="unknown_type") == 100.0

    def test_apply_effects_no_boost_below_min_reincarnation(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=0)

        assert manager.apply_legacy_effects(player) == 100.0

    def test_apply_effects_partial_boost(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=1)

        assert manager.apply_legacy_effects(player) == 115.0

    def test_apply_effects_stacks_all_unlocked_boosts(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=5)

        assert manager.apply_legacy_effects(player) == 125.0

    def test_apply_effects_custom_base_value(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=1)

        assert manager.apply_legacy_effects(player, base_val=200.0) == 230.0

    def test_check_unlocks_lists_eligible_new_skills(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=5)

        assert sorted(manager.check_unlocks(player)) == ["iron_will", "soul_memory"]

    def test_check_unlocks_skips_already_unlocked(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=5, legacy_skills=["soul_memory"])

        assert manager.check_unlocks(player) == ["iron_will"]

    def test_check_unlocks_respects_min_reincarnation(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(reincarnation_count=1)

        assert manager.check_unlocks(player) == ["soul_memory"]

    def test_check_unlocks_none_when_maxed(self, tmp_path):
        manager = LegacySkillManager(make_legacy_registry(tmp_path))
        player = MockPlayer(
            reincarnation_count=5, legacy_skills=["soul_memory", "iron_will"]
        )

        assert manager.check_unlocks(player) == []

    def test_default_registry_used_when_none_passed(self):
        manager = LegacySkillManager()
        reg = fresh_registry(LegacySkillRegistry)
        other = LegacySkillManager(reg)
        assert other.registry is reg
        assert manager.registry is not reg
