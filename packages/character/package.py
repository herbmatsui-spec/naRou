from __future__ import annotations

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


# Module-level function for pickling support
def _initialize_player_and_pet(kernel: Kernel, engine) -> None:
    from systems import AggroList, ResistanceSet

    player = engine.player
    pet = engine.pet

    player.god_id = "jure"
    player.piety = 80
    player.hp = player.max_hp
    player.mp = player.max_mp
    player.status_effects = []
    player.resistances = ResistanceSet()
    player.resistances.fire = 10
    player.faction = "player"
    player.aggro = AggroList()

    if kernel.has_system("meta_progression_manager"):
        meta_mgr = kernel.get_system("meta_progression_manager")
        meta_mgr.recalculate_and_apply_bonuses(player)

    pet.status_effects = []
    pet.resistances = ResistanceSet()
    pet.faction = "player"


class CharacterPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="character",
            provides=[
                "skill_tree_manager",
                "job_manager",
                "skill_fusion_manager",
                "skill_evolution_manager",
                "skill_awakening_manager",
                "skill_transfer_manager",
                "skill_resonance_manager",
                "skill_inheritance_manager",
                "skill_specialization_manager",
                "player_pet_initializer",
            ],
            requires=["event_bus", "entity_manager"],
            dependencies=["core"],
        )

    def setup(self, kernel: Kernel) -> None:
        from job_system import JobManager, JobRegistry
        from skill_awakening_system import SkillAwakeningManager, SkillAwakeningRegistry
        from skill_evolution_system import SkillEvolutionManager, SkillEvolutionRegistry
        from skill_fusion_system import FusionManager, FusionRegistry
        from skill_inheritance_system import SkillInheritanceManager, SkillInheritanceRegistry
        from skill_resonance_system import SkillResonanceManager, SkillResonanceRegistry
        from skill_specialization_system import (
            SkillSpecializationManager,
            SkillSpecializationRegistry,
        )
        from skill_transfer_system import SkillTransferManager, SkillTransferRegistry
        from skill_tree_system import SkillTreeManager, SkillTreeRegistry

        skill_reg = SkillTreeRegistry()
        skill_reg.load()
        kernel.register_system("skill_tree_manager", SkillTreeManager(skill_reg))

        job_reg = JobRegistry()
        job_reg.load()
        kernel.register_system("job_manager", JobManager(job_reg))

        fusion_reg = FusionRegistry()
        fusion_reg.load()
        kernel.register_system("skill_fusion_manager", FusionManager(fusion_reg))

        evolution_reg = SkillEvolutionRegistry()
        evolution_reg.load()
        kernel.register_system("skill_evolution_manager", SkillEvolutionManager(evolution_reg))

        awakening_reg = SkillAwakeningRegistry()
        awakening_reg.load()
        kernel.register_system("skill_awakening_manager", SkillAwakeningManager(awakening_reg))

        transfer_reg = SkillTransferRegistry()
        transfer_reg.load()
        kernel.register_system("skill_transfer_manager", SkillTransferManager(transfer_reg))

        resonance_reg = SkillResonanceRegistry()
        resonance_reg.load()
        kernel.register_system("skill_resonance_manager", SkillResonanceManager(resonance_reg))

        inheritance_reg = SkillInheritanceRegistry()
        inheritance_reg.load()
        kernel.register_system(
            "skill_inheritance_manager", SkillInheritanceManager(inheritance_reg)
        )

        specialization_reg = SkillSpecializationRegistry()
        specialization_reg.load()
        kernel.register_system(
            "skill_specialization_manager",
            SkillSpecializationManager(specialization_reg),
        )

        kernel.register_system("player_pet_initializer", _initialize_player_and_pet)

    def teardown(self, kernel: Kernel) -> None:
        pass
