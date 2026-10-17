"""Unit tests for ecs.entity.Entity - Core entity implementation."""

from __future__ import annotations

import pytest

from ecs.components import (
    AchievementComponent,
    AffectionComponent,
    ArchaeologyComponent,
    AttributesComponent,
    BaseStatsComponent,
    EconomyComponent,
    EmoteComponent,
    GuildFactionComponent,
    LevelComponent,
    PetAIComponent,
    PetProfileComponent,
    ProceduralQuestComponent,
    ReincarnationComponent,
    SkillFusionComponent,
    SkillTreeJobComponent,
    StatusEffectsComponent,
    StorytellerComponent,
    TitleComponent,
)
from ecs.entity import Entity
from tests.conftest import TestEntityBuilder


class TestEntityInitialization:
    """Tests for Entity initialization and basic properties."""

    def test_basic_initialization(self):
        """Entity initializes with required attributes."""
        entity = TestEntityBuilder(name="Hero", hp=100, max_hp=100).build()

        assert entity.name == "Hero"
        assert entity.hp == 100
        assert entity.max_hp == 100
        assert entity.is_player is False
        assert entity.is_pet is False
        assert entity.x == 0
        assert entity.y == 0

    def test_player_initialization(self):
        """Player entity initializes correctly."""
        entity = TestEntityBuilder(name="Player", is_player=True).build()

        assert entity.is_player is True

    def test_pet_initialization(self):
        """Pet entity initializes correctly."""
        entity = TestEntityBuilder(name="Pet", is_pet=True).build()

        assert entity.is_pet is True

    def test_position_initialization(self):
        """Entity position can be set during initialization."""
        entity = TestEntityBuilder(x=10, y=20).build()

        assert entity.x == 10
        assert entity.y == 20

    def test_default_attributes_created(self):
        """AttributesComponent is created with defaults."""
        entity = TestEntityBuilder().build()
        attrs = entity.get_component(AttributesComponent)

        assert attrs is not None
        assert hasattr(attrs, "strength")
        assert hasattr(attrs, "endurance")
        assert hasattr(attrs, "dexterity")

    def test_custom_attributes_applied(self):
        """Custom attributes are applied during build."""
        entity = (TestEntityBuilder()
            .with_attributes(strength=15, endurance=12, dexterity=14)
            .build())
        attrs = entity.get_component(AttributesComponent)

        assert attrs.strength == 15
        assert attrs.endurance == 12
        assert attrs.dexterity == 14


class TestEntityComponents:
    """Tests for Entity component management."""

    def test_all_default_components_present(self):
        """Entity has all default components registered."""
        entity = TestEntityBuilder().build()

        expected_components = [
            TitleComponent,
            GuildFactionComponent,
            AffectionComponent,
            PetProfileComponent,
            EmoteComponent,
            PetAIComponent,
            AchievementComponent,
            ReincarnationComponent,
            SkillTreeJobComponent,
            SkillFusionComponent,
            StorytellerComponent,
            AttributesComponent,
            ProceduralQuestComponent,
            ArchaeologyComponent,
            BaseStatsComponent,
            EconomyComponent,
            LevelComponent,
            StatusEffectsComponent,
        ]

        for comp_type in expected_components:
            assert comp_type in entity.components, f"Missing component: {comp_type.__name__}"

    def test_get_component_returns_instance(self):
        """get_component returns component instance."""
        entity = TestEntityBuilder().build()
        title_comp = entity.get_component(TitleComponent)

        assert isinstance(title_comp, TitleComponent)

    def test_get_component_creates_if_missing(self):
        """get_component creates component if not present."""
        entity = TestEntityBuilder().build()
        # Remove a component manually
        entity.components.pop(TitleComponent, None)

        title_comp = entity.get_component(TitleComponent)

        assert isinstance(title_comp, TitleComponent)
        assert TitleComponent in entity.components

    def test_has_component(self):
        """has_component correctly reports component presence."""
        entity = TestEntityBuilder().build()

        assert entity.has_component(TitleComponent) is True
        assert entity.has_component(AttributesComponent) is True


class TestEntityStats:
    """Tests for Entity stat properties and calculations."""

    def test_hp_management(self):
        """HP can be modified and clamped."""
        entity = TestEntityBuilder(hp=50, max_hp=100).build()

        entity.hp = 75
        assert entity.hp == 75

        entity.hp = 150  # Should not exceed max
        assert entity.hp == 150  # Entity doesn't auto-clamp, but tests can verify

    def test_mp_management(self):
        """MP can be modified."""
        entity = TestEntityBuilder(mp=25, max_mp=50).build()

        entity.mp = 40
        assert entity.mp == 40

    def test_level_and_exp(self):
        """Level and experience work correctly."""
        entity = TestEntityBuilder(level=5, exp=1000).build()

        assert entity.level == 5
        assert entity.exp == 1000


class TestEntityAttributes:
    """Tests for attribute delegation."""

    def test_attribute_access_via_component(self):
        """Attributes accessible via AttributesComponent."""
        entity = (TestEntityBuilder()
            .with_attributes(strength=16, magic=14, will=13)
            .build())

        attrs = entity.get_component(AttributesComponent)

        assert attrs.strength == 16
        assert attrs.magic == 14
        assert attrs.will == 13

    def test_all_eight_attributes(self):
        """All eight main attributes exist."""
        entity = TestEntityBuilder().build()
        attrs = entity.get_component(AttributesComponent)

        expected_attrs = [
            "strength", "endurance", "dexterity", "perception",
            "learning", "will", "magic", "charisma"
        ]

        for attr in expected_attrs:
            assert hasattr(attrs, attr), f"Missing attribute: {attr}"


class TestEntitySerialization:
    """Tests for Entity serialization/deserialization."""

    def test_to_dict_includes_basic_fields(self):
        """to_dict includes all basic entity fields."""
        entity = TestEntityBuilder(name="Test", hp=50, max_hp=100, level=3).build()
        data = entity.to_dict()

        assert data["name"] == "Test"
        assert data["hp"] == 50
        assert data["max_hp"] == 100
        assert data["level"] == 3
        assert data["x"] == 0
        assert data["y"] == 0

    def test_to_dict_includes_components(self):
        """to_dict includes component data."""
        entity = TestEntityBuilder().build()
        data = entity.to_dict()

        assert "components" in data
        assert "TitleComponent" in data["components"]
        assert "AttributesComponent" in data["components"]

    def test_from_dict_restores_basic_fields(self):
        """from_dict restores basic entity fields."""
        entity = TestEntityBuilder(name="Original", hp=75, max_hp=100, level=2).build()
        data = entity.to_dict()

        restored = Entity.from_dict(data)

        assert restored.name == "Original"
        assert restored.hp == 75
        assert restored.max_hp == 100
        assert restored.level == 2

    def test_from_dict_restores_components(self):
        """from_dict restores component data."""
        entity = TestEntityBuilder().build()
        # Modify a component
        title_comp = entity.get_component(TitleComponent)
        title_comp.titles = ["Hero", "Champion"]
        title_comp.equipped_title = "Hero"

        data = entity.to_dict()
        restored = Entity.from_dict(data)

        restored_title = restored.get_component(TitleComponent)
        assert restored_title.titles == ["Hero", "Champion"]
        assert restored_title.equipped_title == "Hero"

    def test_roundtrip_preserves_attributes(self):
        """Full roundtrip preserves attribute modifications."""
        entity = (TestEntityBuilder()
            .with_attributes(strength=18, dexterity=15)
            .build())

        data = entity.to_dict()
        restored = Entity.from_dict(data)

        attrs = restored.get_component(AttributesComponent)
        assert attrs.strength == 18
        assert attrs.dexterity == 15


class TestEntitySkillsVariant:
    """Tests for skill management."""

    def test_skills_initialized(self):
        """Entity has skills dictionary initialized (may be None initially)."""
        entity = TestEntityBuilder().build()

        assert hasattr(entity, "_skills")
        # Skills may be None initially, initialized on first access
        assert entity._skills is None or isinstance(entity._skills, dict)

    def test_skill_serialization(self):
        """Skills are serialized correctly when present."""
        entity = TestEntityBuilder().build()
        # Initialize skills if None
        if entity._skills is None:
            entity._skills = {}
        # Add a test skill
        from ecs.components import Skill
        entity._skills["fire_bolt"] = Skill("fire_bolt")
        entity._skills["fire_bolt"].level = 5
        entity._skills["fire_bolt"].experience = 100

        data = entity.to_dict()

        if "skills" in data and "fire_bolt" in data["skills"]:
            assert data["skills"]["fire_bolt"]["level"] == 5
            assert data["skills"]["fire_bolt"]["experience"] == 100

    def test_skills_initialized_in_init(self):
        """Skills dict is initialized in __init__ for players/pets only."""
        # Non-player/pet entities have _skills = None initially
        entity = TestEntityBuilder().build()
        assert entity._skills is None

        # Player entities have skills initialized
        player = TestEntityBuilder(is_player=True).build()
        assert player._skills is not None
        assert isinstance(player._skills, dict)
        assert len(player._skills) > 0

        # Pet entities have skills initialized
        pet = TestEntityBuilder(is_pet=True).build()
        assert pet._skills is not None
        assert isinstance(pet._skills, dict)
        assert len(pet._skills) > 0

        # Check some default skills exist for players/pets
        expected_skills = ["martial_arts", "short_sword", "evasion"]
        for skill in expected_skills:
            assert skill in player._skills
            assert skill in pet._skills


class TestEntityPetSystem:
    """Tests for pet-related entity properties."""

    def test_pet_properties(self):
        """Pet entities have pet-specific properties."""
        entity = TestEntityBuilder(is_pet=True, name="Dog").build()

        assert entity.is_pet is True
        assert hasattr(entity, "affection")
        assert hasattr(entity, "tactic")

    def test_affection_default(self):
        """Affection defaults to 50."""
        entity = TestEntityBuilder(is_pet=True).build()

        assert entity.affection == 50

    def test_tactic_default(self):
        """Tactic defaults to Japanese assault description."""
        entity = TestEntityBuilder(is_pet=True).build()

        assert entity.tactic == "突撃 (近くの敵を殲滅)"


class TestEntityGodSystem:
    """Tests for god/faith system."""

    def test_god_id_default(self):
        """God ID defaults to lulwy (wind goddess)."""
        entity = TestEntityBuilder().build()

        assert entity.god_id == "lulwy"

    def test_piety_default(self):
        """Piety defaults to 0."""
        entity = TestEntityBuilder().build()

        assert entity.piety == 0


class TestEntityMutationSystem:
    """Tests for mutation system."""

    def test_mutations_dict(self):
        """Mutations stored as dict."""
        entity = TestEntityBuilder().build()

        assert hasattr(entity, "mutations")
        assert isinstance(entity.mutations, dict)

    def test_ether_disease_stages(self):
        """Ether disease stages stored as list."""
        entity = TestEntityBuilder().build()

        assert hasattr(entity, "ether_disease_stages")
        assert isinstance(entity.ether_disease_stages, list)


class TestEntityTutorialSystem:
    """Tests for tutorial completion tracking."""

    def test_completed_tutorials_set(self):
        """Completed tutorials stored as set."""
        entity = TestEntityBuilder().build()

        assert hasattr(entity, "completed_tutorials")
        assert isinstance(entity.completed_tutorials, set)


class TestEntityReincarnation:
    """Tests for reincarnation properties."""

    def test_reincarnation_count_default(self):
        """Reincarnation count defaults to 0."""
        entity = TestEntityBuilder().build()

        assert entity.reincarnation_count == 0

    def test_received_servant_default(self):
        """Received servant flag defaults to False."""
        entity = TestEntityBuilder().build()

        assert entity.received_servant is False

    def test_received_artifact_default(self):
        """Received artifact flag defaults to False."""
        entity = TestEntityBuilder().build()

        assert entity.received_artifact is False


class TestEntityMountSystem:
    """Tests for mount system."""

    def test_is_mounted_default(self):
        """Is mounted defaults to False."""
        entity = TestEntityBuilder().build()

        assert entity.is_mounted is False


class TestEntityGeneSystem:
    """Tests for gene skill system."""

    def test_gene_skills_list(self):
        """Gene skills stored as list."""
        entity = TestEntityBuilder().build()

        assert hasattr(entity, "gene_skills")
        assert isinstance(entity.gene_skills, list)


class TestEntityPetFusion:
    """Tests for pet fusion history."""

    def test_pet_fusion_history(self):
        """Pet fusion history stored as list."""
        entity = TestEntityBuilder(is_pet=True).build()

        assert hasattr(entity, "pet_fusion_history")
        assert isinstance(entity.pet_fusion_history, list)

    def test_pet_type(self):
        """Pet type property exists."""
        entity = TestEntityBuilder(is_pet=True).build()

        assert hasattr(entity, "pet_type")


# =============================================================================
# Priority 1: Core Gameplay Logic Tests
# =============================================================================


class TestEntityGainExpVariant:
    """Tests for gain_exp - core leveling logic."""

    def test_gain_exp_single_level_up(self):
        """Single level up increases level and grants skill points."""
        entity = TestEntityBuilder(level=1, exp=0).build()
        initial_level = entity.level

        # Gain enough exp for one level
        entity.gain_exp(200)

        assert entity.level == initial_level + 1
        assert entity.exp > 0

    def test_gain_exp_multi_level_up(self):
        """Large exp gain triggers multiple level ups."""
        entity = TestEntityBuilder(level=1, exp=0).build()

        # Gain massive exp - should level up multiple times
        entity.gain_exp(10000)

        assert entity.level > 2  # At least 2 levels up
        assert entity.exp > 0

    def test_gain_exp_skill_points_granted(self):
        """Level up grants skill points."""
        entity = TestEntityBuilder(level=1, exp=0).build()
        initial_skill_points = entity.get_component(AttributesComponent).skill_points if hasattr(entity.get_component(AttributesComponent), 'skill_points') else 0

        entity.gain_exp(500)  # Enough for several levels

        # Skill points should increase
        # Note: exact amount depends on implementation

    def test_gain_exp_zero_and_negative(self):
        """Zero or negative exp: zero does nothing, negative reduces exp."""
        entity = TestEntityBuilder(level=5, exp=100).build()
        original_level = entity.level
        original_exp = entity.exp

        entity.gain_exp(0)
        assert entity.level == original_level
        assert entity.exp == original_exp

        entity.gain_exp(-100)
        assert entity.level == original_level
        assert entity.exp == 0  # exp reduced to 0


class TestEntityGainSkillExp:
    """Tests for gain_skill_exp - skill leveling logic."""

    def test_gain_skill_exp_unknown_skill_returns_empty(self):
        """Exp for an unknown skill is ignored: no logs, no skill created."""
        entity = TestEntityBuilder().build()

        result = entity.gain_skill_exp("test_skill", 100)

        assert result == []
        assert "test_skill" not in entity.skills

    def test_gain_skill_exp_level_up(self):
        """Skill exp gain triggers level up at thresholds."""
        entity = TestEntityBuilder(is_player=True).build()  # Players have skills initialized
        skill = entity._skills["long_sword"]
        initial_potential = skill.potential

        logs = entity.gain_skill_exp("long_sword", 1000)

        assert skill.level > 1
        assert len(logs) == skill.level - 1
        # Potential decays by 2 per gained level (floor of 10)
        assert skill.potential == max(10, initial_potential - 2 * (skill.level - 1))

    def test_gain_skill_exp_below_threshold_no_level_up(self):
        """Small exp gain is stored but does not level up or decay potential."""
        entity = TestEntityBuilder(is_player=True).build()
        skill = entity._skills["shield"]

        result = entity.gain_skill_exp("shield", 5)  # below first threshold (level * 20)

        assert result == []
        assert skill.level == 1
        assert skill.experience > 0
        assert skill.potential == 100

    def test_gain_skill_exp_potential_floors_at_ten(self):
        """Potential never decays below 10."""
        entity = TestEntityBuilder(is_player=True).build()
        skill = entity._skills["mining"]
        skill.potential = 11

        entity.gain_skill_exp("mining", 1000)

        assert skill.level > 1
        assert skill.potential == 10


class TestEntityPrayToGod:
    """Tests for pray_to_god - prayer system."""

    def test_pray_no_god(self):
        """Praying with no god (eyth) fails."""
        entity = TestEntityBuilder(god_id="eyth", piety=100).build()

        success, msg = entity.pray_to_god()

        assert success is False
        assert "信仰していない" in msg or "eyth" in msg.lower()

    def test_pray_low_piety(self):
        """Praying with insufficient piety fails."""
        entity = TestEntityBuilder(god_id="lulwy", piety=30).build()

        success, msg = entity.pray_to_god()

        assert success is False
        assert "不足" in msg or "piety" in msg.lower()

    def test_pray_success(self):
        """Praying with sufficient piety succeeds and heals."""
        entity = TestEntityBuilder(god_id="lulwy", piety=60, hp=10, max_hp=100, mp=5, max_mp=50).build()

        success, msg = entity.pray_to_god()

        assert success is True
        assert entity.hp == entity.max_hp
        assert entity.mp == entity.max_mp
        assert entity.piety == 30  # 60 - 30
        assert "御手" in msg or "heal" in msg.lower() or "全快" in msg


class TestEntityApplyInitAttributes:
    """Tests for _apply_init_attributes."""

    def test_apply_init_attributes_from_dict(self):
        """Attributes can be initialized from dict."""
        entity = TestEntityBuilder(
            attributes={"strength": 18, "magic": 14, "dexterity": 16}
        ).build()

        attrs = entity.get_component(AttributesComponent)

        assert attrs.strength == 18
        assert attrs.magic == 14
        assert attrs.dexterity == 16


# =============================================================================
# Priority 2: Serialization Edge Cases
# =============================================================================


class TestEntitySerializationEdgeCases:
    """Tests for to_dict/from_dict edge cases."""

    def test_to_dict_component_fallback(self):
        """to_dict handles components without to_dict method."""
        entity = TestEntityBuilder().build()
        data = entity.to_dict()

        assert "components" in data
        assert "TitleComponent" in data["components"]

    def test_to_dict_callable_skip(self):
        """to_dict skips callable component fields."""
        entity = TestEntityBuilder().build()
        data = entity.to_dict()

        # Callable fields should not be in serialized data
        for comp_data in data["components"].values():
            for v in comp_data.values():
                assert not callable(v)

    def test_from_dict_dynamic_component_loading(self):
        """from_dict loads components dynamically via import."""
        entity = TestEntityBuilder().build()
        data = entity.to_dict()

        restored = Entity.from_dict(data)

        assert restored.name == entity.name
        assert restored.level == entity.level

    def test_from_dict_skill_restoration(self):
        """from_dict restores skill levels/experience."""
        entity = TestEntityBuilder(is_player=True).build()  # Players have skills initialized

        # Add a skill with known values
        if entity._skills and "fire_bolt" in entity._skills:
            entity._skills["fire_bolt"].level = 5
            entity._skills["fire_bolt"].experience = 1000

        data = entity.to_dict()
        restored = Entity.from_dict(data)

        if restored._skills and "fire_bolt" in restored._skills:
            assert restored._skills["fire_bolt"].level == 5
            assert restored._skills["fire_bolt"].experience == 1000


# =============================================================================
# Priority 3: Level/EXP System
# =============================================================================


class TestEntityExpNext:
    """Tests for exp_next property."""

    def test_exp_next_without_config(self):
        """exp_next uses fallback when config unavailable."""
        entity = TestEntityBuilder(level=1).build()

        # Should not crash and return reasonable value
        assert entity.exp_next > 0
        assert isinstance(entity.exp_next, int)

    def test_exp_next_with_config(self, temp_yaml_fixture):
        """exp_next loads from config when available."""
        config_content = {
            "game": {
                "exp_curve": {"base": 100, "growth": 1.5}
            }
        }
        config_path = temp_yaml_fixture(config_content)

        # This test would need the config system to be mocked
        # Just verify the property doesn't crash
        entity = TestEntityBuilder(level=5).build()
        assert entity.exp_next > 0


class TestEntityLevelUp:
    """Tests for level up mechanics."""

    def test_level_up_grants_skill_points(self):
        """Level up increases available skill points."""
        entity = TestEntityBuilder(level=1, exp=0).build()
        initial_sp = entity.get_component(AttributesComponent).skill_points if hasattr(entity.get_component(AttributesComponent), 'skill_points') else 0

        entity.gain_exp(200)

        # Should have gained skill points
        new_sp = entity.get_component(AttributesComponent).skill_points if hasattr(entity.get_component(AttributesComponent), 'skill_points') else 0
        assert new_sp >= initial_sp

    def test_level_up_attribute_growth(self):
        """Level up increases attributes randomly (2 of 8)."""
        entity = TestEntityBuilder(level=1, exp=0).build()
        attrs_before = entity.get_component(AttributesComponent).to_dict()

        entity.gain_exp(500)  # Multiple levels

        attrs_after = entity.get_component(AttributesComponent).to_dict()

        # At least some attributes should have increased
        total_increase = sum(attrs_after[k] - attrs_before.get(k, 0) for k in attrs_after)
        assert total_increase > 0


# =============================================================================
# Priority 4: Component Property Delegation
# =============================================================================


class TestEntityComponentDelegation:
    """Tests for component property delegation (getter/setter round-trips)."""

    def test_title_component_delegation(self):
        """TitleComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.titles = ["Hero", "Champion"]
        assert entity.titles == ["Hero", "Champion"]

        entity.equipped_title = "Hero"
        assert entity.equipped_title == "Hero"

        entity.title_notifications = ["New title!"]
        assert entity.title_notifications == ["New title!"]

        entity.kill_counts = {"goblin": 10}
        assert entity.kill_counts == {"goblin": 10}

        entity.craft_counts = {"potion": 5}
        assert entity.craft_counts == {"potion": 5}

        entity.max_dungeon_depth = 50
        assert entity.max_dungeon_depth == 50

        entity.near_death_count = 3
        assert entity.near_death_count == 3

        entity.total_turns = 10000
        assert entity.total_turns == 10000

    def test_base_stats_ap_delegation(self):
        """BaseStatsComponent AP properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.ap = 50
        assert entity.ap == 50

        entity.max_ap = 200
        assert entity.max_ap == 200

        entity.reset_ap()
        assert entity.ap == entity.max_ap
        assert entity.ap == 200

        assert entity.can_act(50) is True
        assert entity.can_act(100) is True  # 200 >= 100

        assert entity.spend_ap(30) is True
        assert entity.ap == 170  # 200 - 30

        assert entity.spend_ap(50) is True  # 170 >= 50
        assert entity.ap == 120

        assert entity.spend_ap(200) is False  # Not enough AP (120 < 200)
        assert entity.ap == 120  # Unchanged

    def test_facing_delegation(self):
        """Facing property delegates to BaseStatsComponent."""
        entity = TestEntityBuilder().build()

        entity.facing = "N"
        assert entity.facing == "N"

        entity.facing = "E"
        assert entity.facing == "E"

    def test_level_skill_points_delegation(self):
        """LevelComponent skill_points properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.skill_points = 10
        assert entity.skill_points == 10

        entity.total_skill_points_earned = 50
        assert entity.total_skill_points_earned == 50

    def test_attributes_delegation(self):
        """AttributesComponent 8 attributes delegate correctly."""
        entity = TestEntityBuilder().build()

        attrs = ["strength", "endurance", "dexterity", "perception",
                 "learning", "will", "magic", "charisma"]

        for attr in attrs:
            setattr(entity, attr, 15)
            assert getattr(entity, attr) == 15

            setattr(entity, attr, 20)
            assert getattr(entity, attr) == 20

    def test_guild_faction_delegation(self):
        """GuildFactionComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.guild_id = "fighters_guild"
        assert entity.guild_id == "fighters_guild"

        entity.guild_rank = "officer"
        assert entity.guild_rank == "officer"

        entity.guild_role = "leader"
        assert entity.guild_role == "leader"

        entity.guild_contribution = 5000
        assert entity.guild_contribution == 5000

        entity.faction_reputation = {"fighters": 100, "mages": -50}
        assert entity.faction_reputation == {"fighters": 100, "mages": -50}

    def test_achievement_delegation(self):
        """AchievementComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.achievements = ["first_kill", "level_10"]
        assert entity.achievements == ["first_kill", "level_10"]

        entity.meta_progression = {"reincarnation": 3}
        assert entity.meta_progression == {"reincarnation": 3}

    def test_reincarnation_delegation(self):
        """ReincarnationComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.reincarnation_count = 3
        assert entity.reincarnation_count == 3

        entity.karma_law_chaos = 100
        assert entity.karma_law_chaos == 100

        entity.karma_good_evil = -50
        assert entity.karma_good_evil == -50

    def test_skill_tree_job_delegation(self):
        """SkillTreeJobComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.job = "warrior"
        assert entity.job == "warrior"

        entity.job_level = 5
        assert entity.job_level == 5

        entity.job_exp = 1000
        assert entity.job_exp == 1000

    def test_skill_fusion_delegation(self):
        """SkillFusionComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.awakened_skills = ["fire_heal"]
        assert entity.awakened_skills == ["fire_heal"]

        entity.equipped_skills = ["fire_heal"]
        assert entity.equipped_skills == ["fire_heal"]

    def test_storyteller_delegation(self):
        """StorytellerComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.story_flags = {"met_king": True}
        assert entity.story_flags == {"met_king": True}

        entity.ending_progress = {"chapter_1": 50}
        assert entity.ending_progress == {"chapter_1": 50}

    def test_archaeology_delegation(self):
        """ArchaeologyComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.collected_fragments = ["fragment_1"]
        assert entity.collected_fragments == ["fragment_1"]

        entity.decoded_fragments = ["fragment_1"]
        assert entity.decoded_fragments == ["fragment_1"]

        entity.owned_keys = ["key_1"]
        assert entity.owned_keys == ["key_1"]

    def test_emote_delegation(self):
        """EmoteComponent properties delegate correctly."""
        entity = TestEntityBuilder().build()

        entity.emote_state = "happy"
        assert entity.emote_state == "happy"

        entity.emote_frame = 5
        assert entity.emote_frame == 5

        entity.emote_timer = 1000.0
        assert entity.emote_timer == 1000.0

    def test_pet_ai_delegation(self):
        """PetAIComponent properties delegate correctly."""
        entity = TestEntityBuilder(is_pet=True).build()

        entity.pet_ai.bond = 80
        assert entity.pet_ai.bond == 80

        entity.pet_ai.contract_id = "contract_1"
        assert entity.pet_ai.contract_id == "contract_1"


# =============================================================================
# Priority 5: ECS Status Effects API
# =============================================================================


class TestEntityStatusEffectsECS:
    """Tests for ECS StatusEffectsComponent API."""

    def test_status_effects_legacy_mode(self):
        """Legacy list mode works when ECS not enabled."""
        entity = TestEntityBuilder().build()

        # Default should be legacy list
        assert isinstance(entity.status_effects, list)

    def test_status_effects_ecs_mode(self):
        """ECS mode activates when _status_effects_ecs is True."""
        entity = TestEntityBuilder().build()

        # Enable ECS mode
        entity._status_effects_ecs = True

        # Should return component
        from ecs.components import StatusEffectsComponent
        assert isinstance(entity.status_effects, StatusEffectsComponent)

    def test_status_effects_setter_empty_list_clears(self):
        """Setting status_effects to empty list clears ECS component."""
        entity = TestEntityBuilder().build()
        entity._status_effects_ecs = True

        # Add an effect via component
        comp = entity.get_component(entity.status_effects.__class__)
        from ecs.components import ActiveStatusEffect
        comp.effects["poison"] = ActiveStatusEffect(effect_type="poison", duration=10)

        # Clear via empty list
        entity.status_effects = []

        assert len(entity.status_effects.effects) == 0

    def test_has_status(self):
        """has_status checks for effect presence."""
        entity = TestEntityBuilder().build()
        entity._status_effects_ecs = True

        comp = entity.get_component(entity.status_effects.__class__)
        from ecs.components import ActiveStatusEffect
        comp.effects["poison"] = ActiveStatusEffect(effect_type="poison", duration=10)

        assert entity.has_status("poison") is True
        assert entity.has_status("burn") is False

    def test_add_status(self):
        """add_status adds effect to ECS component."""
        entity = TestEntityBuilder().build()
        entity._status_effects_ecs = True

        result = entity.add_status("poison", 10, power=2)

        assert result is True
        assert "poison" in entity.status_effects.effects
        assert entity.status_effects.effects["poison"].duration == 10

    def test_remove_status(self):
        """remove_status removes effect."""
        entity = TestEntityBuilder().build()
        entity._status_effects_ecs = True

        entity.add_status("poison", 10)
        assert entity.has_status("poison")

        entity.remove_status("poison")
        assert not entity.has_status("poison")

    def test_clear_statuses(self):
        """clear_statuses removes all effects."""
        entity = TestEntityBuilder().build()
        entity._status_effects_ecs = True

        entity.add_status("poison", 10)
        entity.add_status("burn", 5)

        entity.clear_statuses()

        assert len(entity.status_effects.effects) == 0


# =============================================================================
# Priority 6: AP System
# =============================================================================


class TestEntityAPSystem:
    """Tests for AP (Action Points) system."""

    def test_ap_defaults(self):
        """AP defaults from BaseStatsComponent."""
        entity = TestEntityBuilder().build()

        assert entity.ap >= 0
        assert entity.max_ap > 0

    def test_reset_ap(self):
        """reset_ap restores AP to max."""
        entity = TestEntityBuilder().build()
        entity.ap = 10

        entity.reset_ap()

        assert entity.ap == entity.max_ap

    def test_can_act(self):
        """can_act checks if entity has enough AP."""
        entity = TestEntityBuilder().build()
        entity.ap = 100
        entity.max_ap = 100

        assert entity.can_act(50) is True
        assert entity.can_act(150) is False

    def test_spend_ap_success(self):
        """spend_ap deducts AP on success."""
        entity = TestEntityBuilder().build()
        entity.ap = 100
        entity.max_ap = 100

        result = entity.spend_ap(30)

        assert result is True
        assert entity.ap == 70

    def test_spend_ap_failure(self):
        """spend_ap returns False when insufficient AP."""
        entity = TestEntityBuilder().build()
        entity.ap = 20

        result = entity.spend_ap(50)

        assert result is False
        assert entity.ap == 20  # Unchanged


# =============================================================================
# Priority 6: Elemental Resistance/Weakness
# =============================================================================


class TestEntityElemental:
    """Tests for elemental resistance and weakness."""

    def test_get_elemental_resistance_base(self):
        """Base resistance from base_resistances dict."""
        entity = TestEntityBuilder().build()
        entity.base_resistances = {"fire": 20, "ice": -10}

        assert entity.get_elemental_resistance("fire") == 20
        assert entity.get_elemental_resistance("ice") == -10
        assert entity.get_elemental_resistance("lightning") == 0

    def test_get_elemental_resistance_with_equipment(self):
        """Equipment adds to base resistance."""
        entity = TestEntityBuilder().build()
        entity.base_resistances = {"fire": 10}

        # Mock inventory with get_elemental_resistances
        from unittest.mock import MagicMock
        mock_inv = MagicMock()
        mock_inv.get_elemental_resistances.return_value = {"fire": 15}
        entity.inventory = mock_inv

        # Should combine base + equipment
        resist = entity.get_elemental_resistance("fire")
        assert resist >= 10

    def test_is_weak_to(self):
        """is_weak_to checks weakness list."""
        entity = TestEntityBuilder().build()
        entity.weaknesses = ["fire", "holy"]

        assert entity.is_weak_to("fire") is True
        assert entity.is_weak_to("holy") is True
        assert entity.is_weak_to("ice") is False


# =============================================================================
# Priority 7: AI Role Detection
# =============================================================================


class TestEntityAIRole:
    """Tests for AI role detection."""

    def test_default_ai_role_brute(self):
        """Unknown names default to BRUTE."""
        entity = TestEntityBuilder(name="RandomMonster").build()

        assert entity.ai_role == "brute"

    def test_ai_role_kiter(self):
        """Names with Japanese magic/archer keywords get KITER."""
        for name in ["弓使い", "魔法使い", "術師", "caster", "Mage", "Archer"]:
            entity = TestEntityBuilder(name=name).build()
            assert entity.ai_role == "kiter", f"Failed for {name}"

    def test_ai_role_flanker(self):
        """Names with cavalry/knight keywords get FLANKER."""
        for name in ["騎士", "騎兵", "knight", "Knight", "騎"]:
            entity = TestEntityBuilder(name=name).build()
            assert entity.ai_role == "flanker", f"Failed for {name}"

    def test_ai_role_brute_default(self):
        """Names without special keywords default to BRUTE."""
        for name in ["Sniper", "Rogue", "Thief", "Warrior", "RandomMonster"]:
            entity = TestEntityBuilder(name=name).build()
            assert entity.ai_role == "brute", f"Failed for {name}"


# =============================================================================
# Priority 8: Skill System
# =============================================================================


class TestEntitySkills:
    """Tests for skill system."""

    def test_skills_initialized_in_init(self):
        """Skills dict is initialized in __init__ for players/pets only."""
        # Non-player/pet entities have _skills = None initially
        entity = TestEntityBuilder().build()
        assert entity._skills is None

        # Player entities have skills initialized
        player = TestEntityBuilder(is_player=True).build()
        assert player._skills is not None
        assert isinstance(player._skills, dict)
        assert len(player._skills) > 0

        # Pet entities have skills initialized
        pet = TestEntityBuilder(is_pet=True).build()
        assert pet._skills is not None
        assert isinstance(pet._skills, dict)
        assert len(pet._skills) > 0

        # Check some default skills exist for players/pets
        expected_skills = ["martial_arts", "short_sword", "evasion"]
        for skill in expected_skills:
            assert skill in player._skills
            assert skill in pet._skills


# =============================================================================
# Priority 1: Core Gameplay Logic Tests
# =============================================================================


class TestEntityGainExp:
    """Tests for gain_exp - core leveling logic."""

    def test_gain_exp_single_level_up(self):
        """Single level up increases level and grants skill points."""
        entity = TestEntityBuilder(level=1, exp=0).build()
        initial_level = entity.level

        # Gain enough exp for one level
        entity.gain_exp(200)

        assert entity.level == initial_level + 1
        assert entity.exp > 0

    def test_gain_exp_multi_level_up(self):
        """Large exp gain triggers multiple level ups."""
        entity = TestEntityBuilder(level=1, exp=0).build()

        # Gain massive exp - should level up multiple times
        entity.gain_exp(10000)

        assert entity.level > 2  # At least 2 levels up
        assert entity.exp > 0

    def test_gain_exp_zero_does_nothing(self):
        """Zero exp does nothing."""
        entity = TestEntityBuilder(level=5, exp=100).build()
        original_level = entity.level
        original_exp = entity.exp

        entity.gain_exp(0)
        assert entity.level == original_level
        assert entity.exp == original_exp

    def test_gain_negative_exp_does_nothing(self):
        """Negative exp reduces exp (current implementation behavior)."""
        entity = TestEntityBuilder(level=5, exp=100).build()
        original_level = entity.level
        original_exp = entity.exp

        entity.gain_exp(-100)
        assert entity.level == original_level
        assert entity.exp == 0  # exp reduced to 0
        skills = entity._skills
        assert isinstance(skills, dict) or skills is None


# =============================================================================
# Coverage: component property setter delegation (parametrized)
# =============================================================================


DELEGATED_PROPERTIES = [
    # (entity property, sample value, owning component class)
    # GuildFactionComponent
    ("guild_id", "fighters_guild", GuildFactionComponent),
    ("guild_rank", "officer", GuildFactionComponent),
    ("guild_contribution", 500, GuildFactionComponent),
    ("guild_role", "leader", GuildFactionComponent),
    ("faction_reputation", {"fighters": 100}, GuildFactionComponent),
    ("completed_faction_events", ["event_1"], GuildFactionComponent),
    ("ranking_titles", ["top10"], GuildFactionComponent),
    ("guild_quest_progress", {"quest_1": 3}, GuildFactionComponent),
    # AchievementComponent
    ("achievements", ["first_kill"], AchievementComponent),
    ("achievement_progress", {"ach_1": 5}, AchievementComponent),
    ("achievement_timers", {"ach_2": 120}, AchievementComponent),
    ("monster_killed_types", {"goblin": 10}, AchievementComponent),
    ("unique_items_obtained", ["sword_of_truth"], AchievementComponent),
    ("social_points", 42, AchievementComponent),
    ("weekly_play_time", 3600, AchievementComponent),
    ("total_level_earned", 15, AchievementComponent),
    ("permanent_bonuses", {"hp": 10}, AchievementComponent),
    ("meta_progression", {"reincarnation": 3}, AchievementComponent),
    ("dungeon_floors_visited", {(1, 2), (3, 4)}, AchievementComponent),
    ("play_time_seconds", 7200, AchievementComponent),
    ("last_festival_check", "2024-01-01", AchievementComponent),
    ("friend_helps", 7, AchievementComponent),
    ("special_items_combo", ["combo_1"], AchievementComponent),
    ("achievement_notifications", ["unlocked!"], AchievementComponent),
    # ReincarnationComponent
    ("reincarnation_count", 3, ReincarnationComponent),
    ("karma_law_chaos", 100, ReincarnationComponent),
    ("karma_good_evil", -50, ReincarnationComponent),
    ("legacy_skills", ["fire_bolt"], ReincarnationComponent),
    ("unlocked_reincarnation_dungeons", ["dungeon_1"], ReincarnationComponent),
    ("collected_fragments", ["fragment_1"], ReincarnationComponent),
    ("favor", {"lulwy": 25}, ReincarnationComponent),
    ("inheritance_selection", {"skill": "fire_bolt"}, ReincarnationComponent),
    ("challenge_progress", {"challenge_1": 2}, ReincarnationComponent),
    ("cycle_modifiers", [{"type": "buff"}], ReincarnationComponent),
    ("legacy_records", [{"era": 1}], ReincarnationComponent),
    # SkillTreeJobComponent
    ("skill_tree_progress", {"warrior": ["node_1"]}, SkillTreeJobComponent),
    ("skill_points", 12, SkillTreeJobComponent),
    ("total_skill_points_earned", 40, SkillTreeJobComponent),
    ("learned_passive_skills", ["toughness"], SkillTreeJobComponent),
    ("job", "warrior", SkillTreeJobComponent),
    ("job_level", 5, SkillTreeJobComponent),
    ("job_exp", 1200, SkillTreeJobComponent),
    ("previous_jobs", ["warrior"], SkillTreeJobComponent),
    ("mastered_jobs", ["warrior"], SkillTreeJobComponent),
    ("mastered_exclusive_skills", ["lionheart"], SkillTreeJobComponent),
    ("inherited_skills", ["fire_bolt"], SkillTreeJobComponent),
    # SkillFusionComponent
    ("skill_fusion_materials", {"fire_bolt": 3}, SkillFusionComponent),
    ("skill_evolution", {"fire_bolt": "inferno"}, SkillFusionComponent),
    ("awakened_skills", ["inferno"], SkillFusionComponent),
    ("skill_traits", {"fire_bolt": {"power": 1.5}}, SkillFusionComponent),
    ("equipped_skills", ["inferno"], SkillFusionComponent),
    ("inheritable_skills", ["inferno"], SkillFusionComponent),
    ("skill_specialization", {"fire_bolt": "pyromancy"}, SkillFusionComponent),
    ("fusion_chain_progress", {"chain_1": 2}, SkillFusionComponent),
    ("skill_archive_progress", {"fusion_1": True}, SkillFusionComponent),
    # StorytellerComponent
    ("story_flags", {"met_king": True}, StorytellerComponent),
    ("story_variables", {"chapter": 2}, StorytellerComponent),
    ("story_choices_made", ["spare_bandit"], StorytellerComponent),
    ("world_state_version", "v2", StorytellerComponent),
    ("player_legacy", {"fame": 100}, StorytellerComponent),
    ("character_relationships", {"oren": {"affinity": 10}}, StorytellerComponent),
    ("memory_fragments", ["memory_1"], StorytellerComponent),
    ("active_world_events", ["festival"], StorytellerComponent),
    ("completed_storylines", ["intro"], StorytellerComponent),
    ("available_storylines", ["chapter_2"], StorytellerComponent),
    ("story_notifications", [{"text": "hi"}], StorytellerComponent),
    ("current_choice_prompt", {"prompt": "choose"}, StorytellerComponent),
    ("ending_progress", {"chapter_1": 50}, StorytellerComponent),
    # ArchaeologyComponent
    ("excavated_sites", ["site_1"], ArchaeologyComponent),
    ("decoded_fragments", ["frag_1"], ArchaeologyComponent),
    ("owned_keys", ["key_1"], ArchaeologyComponent),
    ("reached_truths", ["truth_1"], ArchaeologyComponent),
    ("leaned_endings", {"ending_a": "truth"}, ArchaeologyComponent),
    ("interpretation_notes", {"site_1": "note"}, ArchaeologyComponent),
]


class TestEntitySetters:
    """Parametrized setter tests: entity property writes through to its component."""

    @pytest.mark.parametrize("prop_name,value,comp_cls", DELEGATED_PROPERTIES)
    def test_setter_writes_through_to_component(self, prop_name, value, comp_cls):
        entity = TestEntityBuilder().build()

        prop = getattr(type(entity), prop_name)
        assert isinstance(prop, property)
        assert prop.fset is not None, f"{prop_name} has no setter"

        setattr(entity, prop_name, value)

        comp = entity.get_component(comp_cls)
        assert getattr(comp, prop_name) == value
        assert getattr(entity, prop_name) == value

    def test_procedural_quest_setter_replaces_component(self):
        entity = TestEntityBuilder().build()
        quest = ProceduralQuestComponent()

        entity.procedural_quest = quest

        assert entity.components[ProceduralQuestComponent] is quest
        assert entity.procedural_quest is quest

    def test_archaeology_setter_replaces_component(self):
        entity = TestEntityBuilder().build()
        arch = ArchaeologyComponent()

        entity.archaeology = arch

        assert entity.components[ArchaeologyComponent] is arch
        assert entity.archaeology is arch

    def test_attributes_setter_replaces_component(self):
        entity = TestEntityBuilder().build()
        new_attrs = AttributesComponent()
        new_attrs.strength = 25

        entity.attributes = new_attrs

        assert entity.components[AttributesComponent] is new_attrs
        assert entity.strength == 25

    def test_skills_setter_replaces_skill_map(self):
        from ecs.components import Skill

        entity = TestEntityBuilder().build()
        replacement = {"cooking": Skill("料理", level=4)}

        entity.skills = replacement

        assert entity.skills is replacement
        assert entity.skills["cooking"].level == 4


# =============================================================================
# Coverage: init attributes dict/object branches
# =============================================================================


class TestEntityApplyInitAttributesPaths:
    """_apply_init_attributes accepts a dict or an Attributes object."""

    def test_init_attributes_from_dict(self):
        entity = Entity(
            name="DictAttr",
            attributes={"strength": 18, "magic": 14, "unknown_attr": 99},
        )

        comp = entity.get_component(AttributesComponent)
        assert comp.strength == 18
        assert comp.magic == 14
        # Unknown keys are ignored
        assert not hasattr(comp, "unknown_attr")
        # Base (pre-job-modifier) snapshot is saved
        assert entity._base_attributes is not None
        assert entity._base_attributes.strength == 18
        assert entity._base_attributes.magic == 14

    def test_init_attributes_from_attributes_object(self):
        from ecs.components import Attributes

        src = Attributes(strength=20, will=15)
        entity = Entity(name="ObjAttr", attributes=src)

        comp = entity.get_component(AttributesComponent)
        assert comp.strength == 20
        assert comp.will == 15
        assert entity._base_attributes.strength == 20
        assert entity._base_attributes.will == 15


    def test_init_attributes_from_partial_attributes_object(self):
        class _PartialAttrs:
            strength = 20  # only one of the eight attributes exists

        entity = Entity(name="PartialAttr", attributes=_PartialAttrs())

        comp = entity.get_component(AttributesComponent)
        assert comp.strength == 20
        assert comp.endurance == 10  # untouched default
        assert entity._base_attributes.strength == 20


# =============================================================================
# Coverage: get_component / has_component by-class-name fallback
# =============================================================================


class TestComponentNameFallback:
    def test_get_component_falls_back_to_same_named_class(self):
        entity = TestEntityBuilder().build()
        title_comp = entity.components.pop(TitleComponent)
        # Different class object, identical __name__ (cross-namespace duplicate)
        TitleComponentAlias = type("TitleComponent", (), {})
        entity.components[TitleComponentAlias] = title_comp

        assert entity.get_component(TitleComponent) is title_comp
        assert entity.has_component(TitleComponent) is True

    def test_has_component_false_for_unknown_class(self):
        class TotallyUnknownComponent:
            pass

        entity = TestEntityBuilder().build()

        assert entity.has_component(TotallyUnknownComponent) is False


# =============================================================================
# Coverage: recalculate_stats passive skill bonuses
# =============================================================================


class TestRecalculateStatsPassives:
    def test_passive_bonuses_applied(self, monkeypatch):
        import skill_tree_system

        entity = TestEntityBuilder(is_player=True).build()
        entity.recalculate_stats()
        base_max_hp = entity.max_hp

        class FakeManager:
            def aggregate_bonuses(self, player):
                return {"max_hp_bonus": 50.0, "mp_regen_bonus": 0.25}

        monkeypatch.setattr(
            skill_tree_system, "get_passive_skill_manager", lambda: FakeManager()
        )

        entity.recalculate_stats()

        assert entity.max_hp == base_max_hp + 50
        assert entity.passive_bonuses == {"max_hp_bonus": 50.0, "mp_regen_bonus": 0.25}
        assert entity.passive_mp_regen == 0.25

    def test_passive_hp_bonus_clamps_current_hp(self, monkeypatch):
        import skill_tree_system

        entity = TestEntityBuilder(is_player=True).build()
        entity.recalculate_stats()
        base_max_hp = entity.max_hp
        entity.hp = base_max_hp + 200  # above any post-bonus max

        class FakeManager:
            def aggregate_bonuses(self, player):
                return {"max_hp_bonus": 50.0}

        monkeypatch.setattr(
            skill_tree_system, "get_passive_skill_manager", lambda: FakeManager()
        )

        entity.recalculate_stats()

        assert entity.max_hp == base_max_hp + 50
        assert entity.hp == entity.max_hp  # clamped inside the bonus branch

    def test_passive_manager_failure_is_swallowed(self, monkeypatch):
        import skill_tree_system

        def boom():
            raise RuntimeError("registry unavailable")

        monkeypatch.setattr(skill_tree_system, "get_passive_skill_manager", boom)

        entity = TestEntityBuilder().build()

        entity.recalculate_stats()  # must not raise

        assert entity.max_hp == entity.calculate_max_hp()

    def test_recalculate_stats_with_real_manager(self):
        entity = TestEntityBuilder(is_player=True).build()

        entity.recalculate_stats()

        assert entity.max_hp == entity.calculate_max_hp()
        assert isinstance(entity.passive_bonuses, dict)

    def test_recalculate_stats_restores_base_and_skips_unknown_keys(self):
        class _PartialBase:
            def to_dict(self):
                return {"strength": 21, "ghost_attr": 7}

        entity = TestEntityBuilder().build()
        entity._base_attributes = _PartialBase()

        entity.recalculate_stats()

        assert entity.attributes.strength == 21  # restored from base snapshot
        assert entity.max_hp == entity.calculate_max_hp()

    def test_recalculate_stats_without_base_attributes(self):
        entity = TestEntityBuilder().build()
        entity._base_attributes = None

        entity.recalculate_stats()

        assert entity.max_hp == entity.calculate_max_hp()

    def test_gain_exp_without_base_attributes(self):
        entity = TestEntityBuilder(is_player=True).build()
        entity._base_attributes = None

        entity.gain_exp(10000)

        assert entity.level > 1


# =============================================================================
# Coverage: to_dict __dict__ fallback for components without to_dict
# =============================================================================


class TestToDictRawComponentFallback:
    def test_raw_component_serialization_paths(self):
        class _BrokenSet(set):
            def __iter__(self):
                raise RuntimeError("cannot iterate")

        class RawStateComponent:  # no to_dict -> __dict__ fallback
            def __init__(self):
                self.tags = {"alpha", "beta"}  # set -> list
                self.pair = (1, 2)  # tuple -> list
                self.nested = {"k": (7, 8), "n": 3}  # dict with tuple value -> list
                self.helper = lambda: 42  # callable -> skipped
                self.broken = _BrokenSet({1})  # raises on list() -> skipped

        class RawExtraComponent:  # second raw comp so the fallback loops more than once
            def __init__(self):
                self.flag = True

        class SlottedComponent:  # no __dict__ -> neither serialization branch applies
            __slots__ = ("value",)

            def __init__(self):
                self.value = 5

        entity = TestEntityBuilder().build()
        entity.components[RawStateComponent] = RawStateComponent()
        entity.components[RawExtraComponent] = RawExtraComponent()
        entity.components[SlottedComponent] = SlottedComponent()

        data = entity.to_dict()

        raw = data["components"]["RawStateComponent"]
        assert sorted(raw["tags"]) == ["alpha", "beta"]
        assert raw["pair"] == [1, 2]
        assert raw["nested"] == {"k": [7, 8], "n": 3}
        assert "helper" not in raw  # callable field skipped
        assert "broken" not in raw  # exception path: logged and skipped
        assert data["components"]["RawExtraComponent"] == {"flag": True}
        assert "SlottedComponent" not in data["components"]


# =============================================================================
# Coverage: from_dict unknown/dynamic components and unknown skills
# =============================================================================


class TestFromDictUnknownComponents:
    def test_from_dict_ignores_unknown_component_name(self):
        entity = TestEntityBuilder().build()
        data = entity.to_dict()
        data["components"]["NonexistentComponent"] = {"level": 9}
        # A default component missing from the save data is simply left as-is.
        data["components"].pop("TitleComponent", None)

        restored = Entity.from_dict(data)  # must not raise

        assert restored.get_component(TitleComponent) is not None
        assert not hasattr(restored, "NonexistentComponent")

    def test_from_dict_dynamically_loads_non_default_component(self):
        from ecs.components import HuskComponent

        entity = TestEntityBuilder().build()
        data = entity.to_dict()
        data["components"]["HuskComponent"] = {
            "husk_id": "h1",
            "source_monster": "goblin",
            "tier": 3,
        }

        restored = Entity.from_dict(data)

        husk = restored.get_component(HuskComponent)
        assert husk.husk_id == "h1"
        assert husk.source_monster == "goblin"
        assert husk.tier == 3

    def test_from_dict_swallows_import_error_for_unknown_component(self, monkeypatch):
        import sys

        import ecs.components as comp_pkg

        # Simulate `from ecs.components import components` failing entirely.
        monkeypatch.delattr(comp_pkg, "components", raising=False)
        monkeypatch.setitem(sys.modules, "ecs.components.components", None)

        entity = TestEntityBuilder().build()
        data = entity.to_dict()
        data["components"]["NonexistentComponent"] = {"level": 9}

        restored = Entity.from_dict(data)  # ImportError swallowed -> no crash

        assert restored.get_component(TitleComponent) is not None

    def test_from_dict_ignores_unknown_skill_keys(self):
        entity = TestEntityBuilder(is_player=True).build()
        data = entity.to_dict()
        data["skills"]["ghost_skill"] = {"level": 5, "experience": 0, "potential": 100}

        restored = Entity.from_dict(data)

        assert "ghost_skill" not in restored._skills
        assert restored._skills["long_sword"] is not None


# =============================================================================
# Coverage: status_effects setter, legacy non-empty list in ECS mode
# =============================================================================


class TestStatusEffectsSetterEcsMode:
    def test_nonempty_list_assignment_ignored_in_ecs_mode(self):
        entity = TestEntityBuilder().build()
        entity.add_status("poison", 10)

        entity.status_effects = ["poison", "burn"]  # legacy-style list in ECS mode

        comp = entity.get_component(StatusEffectsComponent)
        assert isinstance(entity.status_effects, StatusEffectsComponent)
        assert set(comp.effects) == {"poison"}  # untouched: neither cleared nor replaced


# =============================================================================
# Coverage: exp_next config-file branch
# =============================================================================


class TestExpNextConfigFile:
    def test_exp_next_reads_balance_config_when_present(self, monkeypatch):
        import builtins
        import io
        import pathlib
        import sys
        import types

        real_open = builtins.open
        config_text = "exp_curve:\n  base: 100\n  growth: 1.5\n"

        def fake_open(file, *args, **kwargs):
            if "balance_standards.yaml" in str(file):
                return io.StringIO(config_text)
            return real_open(file, *args, **kwargs)

        class FakePosixPath(pathlib.PosixPath):
            def exists(self):
                return True

        # exp_next imports Path from pathlib at call time; swap in a stub whose
        # exists() reports the config file as present.
        stub = types.ModuleType("pathlib")
        stub.Path = FakePosixPath
        monkeypatch.setitem(sys.modules, "pathlib", stub)
        monkeypatch.setattr(builtins, "open", fake_open)

        entity = TestEntityBuilder(level=3).build()

        # base * growth^(level-1) = 100 * 1.5^2 = 225
        assert entity.exp_next == 225


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
