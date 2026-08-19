from __future__ import annotations
from packages.core.kernel.package import IPackage, PackageMetadata
from packages.core.kernel.kernel import Kernel


class SocialPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="social",
            provides=[
                "guild_manager",
                "guild_quest_manager",
                "faction_war_manager",
                "guild_skill_manager",
                "pet_contract_manager",
                "pet_evolution_manager",
                "pet_fusion_manager",
                "relationship_manager",
                "procedural_quest_manager",
                "quest_scheduler",
            ],
            requires=["event_bus", "entity_manager", "skill_tree_manager"],
            dependencies=["core", "character"],
        )

    def setup(self, kernel: Kernel) -> None:
        from guild_system import GuildRegistry, GuildManager
        from guild_quest_system import GuildQuestRegistry, GuildQuestManager
        from faction_war_system import FactionWarRegistry, FactionWarManager
        from guild_skill_system import GuildSkillRegistry, GuildSkillManager
        from pet_contract_system import PetContractRegistry, PetContractManager
        from pet_evolution_system import PetEvolutionRegistry, PetEvolutionManager
        from pet_fusion_system import PetFusionRegistry, PetFusionManager
        from relationship_system import RelationshipRegistry, RelationshipManager
        from procedural_quest_generator import (
            QuestGenerationRegistry, ProceduralQuestGenerator, ProceduralQuestManager
        )
        from quest_scheduler import QuestScheduler

        guild_reg = GuildRegistry()
        guild_reg.load()
        kernel.register_system("guild_manager", GuildManager(guild_reg))

        guild_quest_reg = GuildQuestRegistry()
        guild_quest_reg.load()
        kernel.register_system("guild_quest_manager", GuildQuestManager(guild_quest_reg))

        faction_war_reg = FactionWarRegistry()
        faction_war_reg.load()
        kernel.register_system("faction_war_manager", FactionWarManager(faction_war_reg))

        guild_skill_reg = GuildSkillRegistry()
        guild_skill_reg.load()
        kernel.register_system("guild_skill_manager", GuildSkillManager(guild_skill_reg))

        pet_contract_reg = PetContractRegistry()
        pet_contract_reg.load()
        kernel.register_system("pet_contract_manager", PetContractManager(pet_contract_reg))

        pet_evolution_reg = PetEvolutionRegistry()
        pet_evolution_reg.load()
        kernel.register_system("pet_evolution_manager", PetEvolutionManager(pet_evolution_reg))

        pet_fusion_reg = PetFusionRegistry()
        pet_fusion_reg.load()
        kernel.register_system("pet_fusion_manager", PetFusionManager(pet_fusion_reg))

        relationship_reg = RelationshipRegistry()
        relationship_reg.load()
        kernel.register_system("relationship_manager", RelationshipManager(relationship_reg))

        quest_gen_reg = QuestGenerationRegistry()
        quest_gen_reg.load()
        procedural_quest_gen = ProceduralQuestGenerator(quest_gen_reg)
        kernel.register_system("procedural_quest_manager", ProceduralQuestManager(procedural_quest_gen))

        kernel.register_system("quest_scheduler", QuestScheduler())

    def teardown(self, kernel: Kernel) -> None:
        pass