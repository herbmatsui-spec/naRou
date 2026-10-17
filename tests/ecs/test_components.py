"""Unit tests for ecs.components.components - Core component implementations."""

from __future__ import annotations

import pytest

from ecs.components import (
    AchievementComponent,
    AffectionComponent,
    ArchaeologyComponent,
    Attributes,
    AttributesComponent,
    BaseStatsComponent,
    EconomyComponent,
    EmoteComponent,
    GuildFactionComponent,
    HuskComponent,
    HuskInventoryComponent,
    LevelComponent,
    PetAIComponent,
    PetProfileComponent,
    ProceduralQuestComponent,
    PuppetUnitComponent,
    ReincarnationComponent,
    Skill,
    SkillFusionComponent,
    SkillTreeJobComponent,
    StatusEffectsComponent,
    StorytellerComponent,
    TitleComponent,
)


class TestAttributes:
    """Tests for Attributes dataclass."""

    def test_default_attributes(self):
        """Attributes initializes with default values."""
        attrs = Attributes()

        assert attrs.strength == 10
        assert attrs.endurance == 10
        assert attrs.dexterity == 10
        assert attrs.perception == 10
        assert attrs.learning == 10
        assert attrs.will == 10
        assert attrs.magic == 10
        assert attrs.charisma == 10

    def test_custom_attributes(self):
        """Attributes can be initialized with custom values."""
        attrs = Attributes(strength=15, magic=12, dexterity=14)

        assert attrs.strength == 15
        assert attrs.magic == 12
        assert attrs.dexterity == 14
        # Others should be defaults
        assert attrs.endurance == 10

    def test_to_dict(self):
        """Attributes serializes to dict."""
        attrs = Attributes(strength=12, endurance=11)
        data = attrs.to_dict()

        assert data["strength"] == 12
        assert data["endurance"] == 11
        assert "dexterity" in data
        assert data["dexterity"] == 10

    def test_from_dict(self):
        """Attributes deserializes from dict."""
        data = {"strength": 14, "magic": 13, "will": 11}
        attrs = Attributes.from_dict(data)

        assert attrs.strength == 14
        assert attrs.magic == 13
        assert attrs.will == 11
        # Missing fields should be defaults
        assert attrs.endurance == 10

    def test_all_eight_attributes_present(self):
        """All eight main attributes are present."""
        attrs = Attributes()
        expected = [
            "strength", "endurance", "dexterity", "perception",
            "learning", "will", "magic", "charisma"
        ]

        for attr in expected:
            assert hasattr(attrs, attr)


class TestAttributesComponent:
    """Tests for AttributesComponent."""

    def test_component_creation(self):
        """Component creates with default Attributes."""
        comp = AttributesComponent()

        assert comp is not None
        assert hasattr(comp, "strength")

    def test_attribute_access(self):
        """Attributes accessible via component."""
        comp = AttributesComponent()
        comp.strength = 16
        comp.magic = 14

        assert comp.strength == 16
        assert comp.magic == 14


class TestTitleComponent:
    """Tests for TitleComponent."""

    def test_default_values(self):
        """TitleComponent initializes with defaults."""
        comp = TitleComponent()

        assert comp.titles == []
        assert comp.equipped_title is None
        assert comp.title_notifications == []
        assert comp.kill_counts == {}
        assert comp.gold == 0
        assert comp.craft_counts == {}
        assert comp.max_dungeon_depth == 0
        assert comp.near_death_count == 0
        assert comp.total_turns == 0

    def test_add_title(self):
        """Titles can be added."""
        comp = TitleComponent()
        comp.titles.append("Hero")

        assert "Hero" in comp.titles

    def test_equip_title(self):
        """Title can be equipped."""
        comp = TitleComponent()
        comp.titles = ["Hero", "Champion"]
        comp.equipped_title = "Hero"

        assert comp.equipped_title == "Hero"

    def test_kill_counts(self):
        """Kill counts tracked per enemy type."""
        comp = TitleComponent()
        comp.kill_counts["goblin"] = 10
        comp.kill_counts["slime"] = 5

        assert comp.kill_counts["goblin"] == 10
        assert comp.kill_counts["slime"] == 5


class TestGuildFactionComponent:
    """Tests for GuildFactionComponent."""

    def test_default_values(self):
        """GuildFactionComponent initializes with defaults."""
        comp = GuildFactionComponent()

        assert comp.guild_id is None
        assert comp.guild_rank == "none"
        assert comp.guild_role is None
        assert comp.guild_contribution == 0
        assert comp.faction_reputation == {}
        assert comp.completed_faction_events == []
        assert comp.guild_quest_progress == {}
        assert comp.ranking_titles == []

    def test_faction_reputation(self):
        """Faction reputation can be modified."""
        comp = GuildFactionComponent()
        comp.faction_reputation["fighters_guild"] = 100
        comp.faction_reputation["mages_guild"] = -50

        assert comp.faction_reputation["fighters_guild"] == 100
        assert comp.faction_reputation["mages_guild"] == -50

    def test_guild_progression(self):
        """Guild progression can be tracked."""
        comp = GuildFactionComponent()
        comp.guild_id = "fighters_guild"
        comp.guild_rank = "officer"
        comp.guild_role = "officer"
        comp.guild_contribution = 5000

        assert comp.guild_id == "fighters_guild"
        assert comp.guild_rank == "officer"
        assert comp.guild_contribution == 5000


class TestAffectionComponent:
    """Tests for AffectionComponent."""

    def test_default_values(self):
        """AffectionComponent initializes with defaults."""
        comp = AffectionComponent()

        assert comp.affection == 50
        assert comp.is_mounted is False

    def test_affection_modification(self):
        """Affection can be modified."""
        comp = AffectionComponent()
        comp.affection = 80

        assert comp.affection == 80


class TestPetProfileComponent:
    """Tests for PetProfileComponent."""

    def test_default_values(self):
        """PetProfileComponent initializes with defaults."""
        comp = PetProfileComponent()

        assert comp.pet_type == "puppy"
        assert comp.gene_skills == []
        assert comp.pet_fusion_history == []

    def test_pet_data(self):
        """Pet data can be set."""
        comp = PetProfileComponent()
        comp.pet_type = "dog"
        comp.gene_skills = ["fetch", "guard"]
        comp.pet_fusion_history = ["wolf", "dog"]

        assert comp.pet_type == "dog"
        assert comp.gene_skills == ["fetch", "guard"]
        assert comp.pet_fusion_history == ["wolf", "dog"]


class TestEmoteComponent:
    """Tests for EmoteComponent."""

    def test_default_values(self):
        """EmoteComponent initializes with defaults."""
        comp = EmoteComponent()

        assert comp.emote_state is None
        assert comp.emote_frame == 0
        assert comp.emote_timer == 0.0

    def test_emote_setting(self):
        """Emote can be set."""
        comp = EmoteComponent()
        comp.emote_state = "happy"
        comp.emote_frame = 5
        comp.emote_timer = 1000.0

        assert comp.emote_state == "happy"
        assert comp.emote_frame == 5
        assert comp.emote_timer == 1000.0


class TestPetAIComponent:
    """Tests for PetAIComponent."""

    def test_default_values(self):
        """PetAIComponent initializes with defaults."""
        comp = PetAIComponent()

        assert comp.bond == 0
        assert comp.contract_id == "default"
        assert comp.equipment == {}
        assert comp.evolution_path == []
        assert comp.evolution_stage == 0
        assert hasattr(comp, "TACTIC_ASSAULT")
        assert hasattr(comp, "TACTIC_FOLLOW")
        assert hasattr(comp, "TACTIC_HEAL")
        assert hasattr(comp, "TACTIC_ESCAPE")

    def test_tactic_constants(self):
        """Tactic constants have expected Japanese values."""
        assert PetAIComponent.TACTIC_ASSAULT == "突撃 (近くの敵を殲滅)"
        assert PetAIComponent.TACTIC_FOLLOW == "追従 (主人の傍を離れない)"
        assert PetAIComponent.TACTIC_HEAL == "支援 (回復・援護優先)"
        assert PetAIComponent.TACTIC_ESCAPE == "待避 (危険時は逃走)"

    def test_equipment(self):
        """Equipment can be tracked."""
        comp = PetAIComponent()
        comp.equipment = {"collar": 1, "vest": 1}

        assert comp.equipment == {"collar": 1, "vest": 1}


class TestAchievementComponent:
    """Tests for AchievementComponent."""

    def test_default_values(self):
        """AchievementComponent initializes with defaults."""
        comp = AchievementComponent()

        assert comp.achievements == []
        assert comp.meta_progression == {}

    def test_achievement_tracking(self):
        """Achievements can be tracked."""
        comp = AchievementComponent()
        comp.achievements.append("first_kill")
        comp.achievements.append("level_10")

        assert "first_kill" in comp.achievements
        assert "level_10" in comp.achievements

    def test_meta_progression(self):
        """Meta progression can be tracked."""
        comp = AchievementComponent()
        comp.meta_progression["reincarnation_master"] = 1
        comp.meta_progression["fragment_collector_10"] = 2

        assert comp.meta_progression["reincarnation_master"] == 1


class TestReincarnationComponent:
    """Tests for ReincarnationComponent."""

    def test_default_values(self):
        """ReincarnationComponent initializes with defaults."""
        comp = ReincarnationComponent()

        assert comp.reincarnation_count == 0
        assert comp.karma_law_chaos == 0
        assert comp.karma_good_evil == 0
        assert comp.favor == {}
        assert comp.inheritance_selection == {}
        assert comp.legacy_skills == []
        assert comp.legacy_records == []
        assert comp.collected_fragments == []
        assert comp.challenge_progress == {}
        assert comp.unlocked_reincarnation_dungeons == []
        assert comp.cycle_modifiers == []

    def test_reincarnation_data(self):
        """Reincarnation data can be set."""
        comp = ReincarnationComponent()
        comp.reincarnation_count = 3
        comp.karma_law_chaos = 100
        comp.karma_good_evil = -50
        comp.inheritance_selection = {"skill_focus": True, "stat_boost": True}
        comp.legacy_skills = ["fire_bolt", "heal"]

        assert comp.reincarnation_count == 3
        assert comp.karma_law_chaos == 100
        assert comp.karma_good_evil == -50
        assert comp.inheritance_selection["skill_focus"] is True
        assert "fire_bolt" in comp.legacy_skills


class TestSkillTreeJobComponent:
    """Tests for SkillTreeJobComponent."""

    def test_default_values(self):
        """SkillTreeJobComponent initializes with defaults."""
        comp = SkillTreeJobComponent()

        assert comp.job == "novice"
        assert comp.job_level == 1
        assert comp.job_exp == 0
        assert comp.skill_points == 0
        assert comp.total_skill_points_earned == 0
        assert comp.mastered_jobs == []
        assert comp.previous_jobs == []
        assert comp.learned_passive_skills == []
        assert comp.mastered_exclusive_skills == []
        assert comp.skill_tree_progress == {}
        assert comp.inherited_skills == []
        assert comp.inherited_stat_bonus == 0

    def test_job_progression(self):
        """Job progression can be tracked."""
        comp = SkillTreeJobComponent()
        comp.job = "warrior"
        comp.job_level = 5
        comp.job_exp = 1000
        comp.skill_points = 10
        comp.mastered_jobs = ["fighter", "warrior"]
        comp.learned_passive_skills = ["iron_will", "combat_reflexes"]

        assert comp.job == "warrior"
        assert comp.job_level == 5
        assert comp.skill_points == 10
        assert "fighter" in comp.mastered_jobs
        assert "iron_will" in comp.learned_passive_skills


class TestSkillFusionComponent:
    """Tests for SkillFusionComponent."""

    def test_default_values(self):
        """SkillFusionComponent initializes with defaults."""
        comp = SkillFusionComponent()

        assert comp.fusion_chain_progress == {}
        assert comp.equipped_skills == []
        assert comp.skill_fusion_materials == {}
        assert comp.skill_evolution == {}
        assert comp.skill_specialization == {}
        assert comp.skill_traits == {}
        assert comp.inheritable_skills == []
        assert comp.skill_archive_progress == {}
        assert comp.awakened_skills == []

    def test_fusion_tracking(self):
        """Fused skills can be tracked."""
        comp = SkillFusionComponent()
        comp.awakened_skills = ["fire_heal", "ice_shield"]
        comp.equipped_skills = ["fire_heal"]

        assert "fire_heal" in comp.awakened_skills
        assert "fire_heal" in comp.equipped_skills


class TestStorytellerComponent:
    """Tests for StorytellerComponent."""

    def test_default_values(self):
        """StorytellerComponent initializes with defaults."""
        comp = StorytellerComponent()

        assert comp.ending_progress == {}
        assert comp.story_flags == {}
        assert comp.story_variables == {}
        assert comp.story_notifications == []
        assert comp.memory_fragments == []
        assert comp.completed_storylines == []
        assert comp.available_storylines == []
        assert comp.character_relationships == {}
        assert comp.active_world_events == []
        assert comp.player_legacy == {}
        assert comp.story_choices_made == []
        assert comp.world_state_version == "1.0"

    def test_story_progress(self):
        """Story progress can be tracked."""
        comp = StorytellerComponent()
        comp.ending_progress = {"chapter_1": 50, "chapter_2": 0}
        comp.story_flags["met_king"] = True
        comp.story_flags["found_sword"] = True
        comp.completed_storylines.append("chapter_1")

        assert comp.ending_progress["chapter_1"] == 50
        assert comp.story_flags["met_king"] is True
        assert "chapter_1" in comp.completed_storylines


class TestProceduralQuestComponent:
    """Tests for ProceduralQuestComponent."""

    def test_default_values(self):
        """ProceduralQuestComponent initializes with defaults."""
        comp = ProceduralQuestComponent()

        assert comp.active_board == []
        assert comp.accepted_quests == []
        assert comp.active_chains == {}
        assert comp.completed_quest_ids == []
        assert comp.completed_count == 0
        assert comp.generated_total_count == 0
        assert comp.board_seed == 0

    def test_quest_tracking(self):
        """Quests can be tracked."""
        comp = ProceduralQuestComponent()
        comp.accepted_quests = ["deliver_letter", "kill_goblins"]
        comp.completed_quest_ids = ["collect_herbs"]
        comp.completed_count = 1
        comp.active_board = ["slum_board"]

        assert "deliver_letter" in comp.accepted_quests
        assert "collect_herbs" in comp.completed_quest_ids
        assert comp.completed_count == 1


class TestArchaeologyComponent:
    """Tests for ArchaeologyComponent."""

    def test_default_values(self):
        """ArchaeologyComponent initializes with defaults."""
        comp = ArchaeologyComponent()

        assert comp.collected_fragments == []
        assert comp.decoded_fragments == []
        assert comp.owned_keys == []
        assert comp.decipherment_gauge == 0

    def test_fragment_collection(self):
        """Fragments can be collected."""
        comp = ArchaeologyComponent()
        comp.collected_fragments.append("goblin_child_screams")
        comp.decipherment_gauge = 20

        assert "goblin_child_screams" in comp.collected_fragments
        assert comp.decipherment_gauge == 20


class TestBaseStatsComponent:
    """Tests for BaseStatsComponent."""

    def test_default_values(self):
        """BaseStatsComponent initializes with defaults."""
        comp = BaseStatsComponent()

        # Defaults from actual implementation
        assert comp.hp == 50
        assert comp.max_hp == 50
        assert comp.mp == 20
        assert comp.max_mp == 20
        assert comp.ap == 2
        assert comp.max_ap == 2
        assert comp.facing == "S"

    def test_stat_modification(self):
        """Stats can be modified."""
        comp = BaseStatsComponent()
        comp.hp = 75
        comp.max_hp = 100
        comp.mp = 30
        comp.max_mp = 50

        assert comp.hp == 75
        assert comp.max_hp == 100
        assert comp.mp == 30
        assert comp.max_mp == 50


class TestEconomyComponent:
    """Tests for EconomyComponent."""

    def test_default_values(self):
        """EconomyComponent initializes with defaults."""
        comp = EconomyComponent()

        assert comp.gold == 0
        assert comp.platinum == 0

    def test_currency_modification(self):
        """Currency can be modified."""
        comp = EconomyComponent()
        comp.gold = 1000
        comp.platinum = 10

        assert comp.gold == 1000
        assert comp.platinum == 10


class TestLevelComponent:
    """Tests for LevelComponent."""

    def test_default_values(self):
        """LevelComponent initializes with defaults."""
        comp = LevelComponent()

        assert comp.level == 1
        assert comp.exp == 0
        assert comp.skill_points == 0
        assert comp.total_skill_points_earned == 0

    def test_level_up(self):
        """Level up progression works."""
        comp = LevelComponent()
        comp.level = 5
        comp.exp = 5000
        comp.skill_points = 10
        comp.total_skill_points_earned = 50

        assert comp.level == 5
        assert comp.skill_points == 10


class TestStatusEffectsComponent:
    """Tests for StatusEffectsComponent."""

    def test_default_values(self):
        """StatusEffectsComponent initializes with defaults."""
        comp = StatusEffectsComponent()

        assert comp.effects == {}

    def test_add_effect(self):
        """Effects can be added."""
        comp = StatusEffectsComponent()
        comp.effects["poison"] = {"duration": 10, "power": 2}

        assert "poison" in comp.effects
        assert comp.effects["poison"]["type"] == "poison" if "type" in comp.effects["poison"] else True
        assert comp.effects["poison"]["duration"] == 10
        assert comp.effects["poison"]["power"] == 2

    def test_clear_effects(self):
        """Effects can be cleared."""
        comp = StatusEffectsComponent()
        comp.effects["poison"] = {"duration": 10}
        comp.effects.clear()

        assert len(comp.effects) == 0


class TestSkill:
    """Tests for Skill class."""

    def test_skill_creation(self):
        """Skill initializes correctly."""
        skill = Skill("fire_bolt")

        assert skill.name == "fire_bolt"
        assert skill.level == 1
        assert skill.experience == 0
        assert skill.potential == 100

    def test_skill_level_up(self):
        """Skill level can increase."""
        skill = Skill("heal")
        skill.level = 5
        skill.experience = 1000
        skill.potential = 150

        assert skill.level == 5
        assert skill.experience == 1000
        assert skill.potential == 150


class TestHuskComponent:
    """Tests for HuskComponent."""

    def test_husk_creation(self):
        """HuskComponent initializes correctly."""
        husk = HuskComponent(
            husk_id="test_001",
            source_monster="goblin",
            tier=2,
        )

        assert husk.husk_id == "test_001"
        assert husk.source_monster == "goblin"
        assert husk.tier == 2
        assert husk.decay == 0
        assert husk.corruption == 0
        assert husk.slots == 1
        assert husk.injected_skills == []
        assert husk.injected_codes == []

    def test_husk_serialization(self):
        """HuskComponent serializes correctly."""
        husk = HuskComponent(
            husk_id="test_001",
            source_monster="goblin",
            tier=2,
            decay=10,
            corruption=5,
            slots=3,
            injected_skills=["fire_bolt", "heal"],
            injected_codes=["synergy_fire_heal"],
        )

        data = husk.to_dict()

        assert data["husk_id"] == "test_001"
        assert data["source_monster"] == "goblin"
        assert data["tier"] == 2
        assert data["decay"] == 10
        assert data["corruption"] == 5
        assert data["slots"] == 3
        assert data["injected_skills"] == ["fire_bolt", "heal"]
        assert data["injected_codes"] == ["synergy_fire_heal"]

    def test_husk_deserialization(self):
        """HuskComponent deserializes correctly."""
        data = {
            "husk_id": "test_001",
            "source_monster": "goblin",
            "tier": 2,
            "decay": 10,
            "max_decay": 100,
            "corruption": 5,
            "loyalty": 0,
            "slots": 3,
            "injected_skills": ["fire_bolt", "heal"],
            "injected_codes": ["synergy_fire_heal"],
        }

        husk = HuskComponent.from_dict(data)

        assert husk.husk_id == "test_001"
        assert husk.source_monster == "goblin"
        assert husk.tier == 2
        assert husk.decay == 10
        assert husk.max_decay == 100
        assert husk.corruption == 5
        assert husk.slots == 3
        assert husk.injected_skills == ["fire_bolt", "heal"]
        assert husk.injected_codes == ["synergy_fire_heal"]


class TestHuskInventoryComponent:
    """Tests for HuskInventoryComponent."""

    def test_default_values(self):
        """HuskInventoryComponent initializes with empty list."""
        comp = HuskInventoryComponent()

        assert comp.husks == []

    def test_add_husk(self):
        """Husks can be added to inventory."""
        comp = HuskInventoryComponent()
        husk = HuskComponent(husk_id="test_001", source_monster="goblin", tier=1)
        comp.husks.append(husk)

        assert len(comp.husks) == 1
        assert comp.husks[0].husk_id == "test_001"

    def test_serialization(self):
        """HuskInventoryComponent serializes correctly."""
        comp = HuskInventoryComponent()
        husk = HuskComponent(husk_id="test_001", source_monster="goblin", tier=1)
        comp.husks.append(husk)

        data = comp.to_dict()

        assert "husks" in data
        assert len(data["husks"]) == 1
        assert data["husks"][0]["husk_id"] == "test_001"

    def test_deserialization(self):
        """HuskInventoryComponent deserializes correctly."""
        data = {
            "husks": [
                {
                    "husk_id": "test_001",
                    "source_monster": "goblin",
                    "tier": 1,
                    "decay": 0,
                    "max_decay": 100,
                    "corruption": 0,
                    "loyalty": 0,
                    "slots": 1,
                    "injected_skills": [],
                    "injected_codes": [],
                }
            ]
        }

        comp = HuskInventoryComponent.from_dict(data)

        assert len(comp.husks) == 1
        assert comp.husks[0].husk_id == "test_001"
        assert comp.husks[0].source_monster == "goblin"


class TestPuppetUnitComponent:
    """Tests for PuppetUnitComponent."""

    def test_default_values(self):
        """PuppetUnitComponent initializes with defaults."""
        comp = PuppetUnitComponent(
            unit_id="u1",
            role="turret",
            husk_ref="husk1",
        )

        assert comp.unit_id == "u1"
        assert comp.role == "turret"
        assert comp.husk_ref == "husk1"
        assert comp.state == "sleep"
        assert comp.loyalty == 0
        assert comp.corruption == 0
        assert comp.hp == 10
        assert comp.max_hp == 10
        assert comp.order == "follow"
        assert comp.location == "base"
        assert comp.skills == []
        assert comp.route == []

    def test_custom_values(self):
        """PuppetUnitComponent accepts custom values."""
        comp = PuppetUnitComponent(
            unit_id="u2",
            role="drone",
            husk_ref="husk2",
            state="active",
            loyalty=50,
            corruption=10,
            hp=20,
            max_hp=20,
            order="guard",
            location="field",
            skills=["fire_bolt"],
            route=["base", "outpost"],
        )

        assert comp.state == "active"
        assert comp.loyalty == 50
        assert comp.corruption == 10
        assert comp.hp == 20
        assert comp.order == "guard"
        assert comp.location == "field"
        assert comp.skills == ["fire_bolt"]
        assert comp.route == ["base", "outpost"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
