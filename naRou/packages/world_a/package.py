"""
World A (Skill Eater) Package for Elona / naRou Roguelike Kernel
Steps 3, 4, 5, 6: WorldAPackage definition and system registration
"""

from __future__ import annotations

from pathlib import Path

from naRou.packages.core.kernel.kernel import Kernel
from naRou.packages.core.kernel.package import IPackage, PackageMetadata


class WorldAPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="world_a",
            provides=[
                "skill_eater_registry",
                "skill_eater_combat_system",
                "skill_eater_synthesis_system",
                "skill_eater_presentation_system",
                "skill_eater_audio_system",
                "skill_eater_economy_system",
                "skill_eater_servant_system",
                "skill_eater_meta_quest_system",
                "skill_eater_exploration_system",
                "skill_eater_meta_intervention",
                "skill_eater_intervention_engine",
                "skill_eater_reincarnation_system",
                "skill_eater_toxicity_manager",
                "slum_base_expansion_manager",
                "skill_eater_pet_dispatch_manager",
                "skill_eater_underground_arena",
                "skill_eater_bounty_system",
                "skill_eater_ascension_board",
                "skill_eater_concept_crystal",
                "skill_eater_temporal_vault",
                "skill_eater_epilogue_manager",
            ],
            requires=["event_bus", "entity_manager"],
            dependencies=["core"],
        )

    def setup(self, kernel: Kernel) -> None:
        from naRou.skill_eater_ascension_board import AscensionBoard
        from naRou.skill_eater_audio_system import SkillEaterAudioSystem
        from naRou.skill_eater_base_expansion import SlumBaseExpansionManager
        from naRou.skill_eater_bounty_system import MidasBountyManager
        from naRou.skill_eater_combat_system import SkillEaterCombatSystem
        from naRou.skill_eater_concept_crystal import ConceptCrystallizer
        from naRou.skill_eater_economy_system import SkillEaterEconomySystem
        from naRou.skill_eater_epilogue import EpilogueAndTransitionManager
        from naRou.skill_eater_exploration_system import SkillEaterExplorationSystem
        from naRou.systems.skill_eater_meta_intervention_system import TemplateEventGenerator, InterventionEngine
        from naRou.skill_eater_meta_quest_system import SkillEaterQuestSystem, SkillEaterReincarnationSystem
        from naRou.skill_eater_pet_dispatch import PetDispatchManager
        from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
        from naRou.skill_eater_servant_system import SkillEaterServantSystem
        from naRou.skill_eater_synthesis_system import SkillEaterSynthesisSystem
        from naRou.skill_eater_system import SkillEaterRegistry
        from naRou.systems.skill_eater_template_model import load_templates
        from naRou.skill_eater_temporal_vault import TemporalVaultManager
        from naRou.skill_eater_toxicity_system import SkillToxicityManager
        from naRou.skill_eater_underground_arena import UndergroundArenaManager

        # Initialize and load registry
        registry = SkillEaterRegistry.get_instance()
        skills_yaml_candidates = [
            Path(__file__).resolve().parents[3] / "data" / "worlds" / "skill_eater" / "skills.yaml",
            Path(__file__).resolve().parents[3] / "data" / "skills_skill_eater.yaml",
            Path(__file__).resolve().parents[2] / "data" / "worlds" / "skill_eater" / "skills.yaml",
            Path(__file__).resolve().parents[2] / "data" / "skills_skill_eater.yaml",
        ]
        for candidate in skills_yaml_candidates:
            if candidate.exists():
                try:
                    registry.load_from_yaml(candidate)
                    break
                except Exception:
                    pass

        kernel.register_system("skill_eater_registry", registry)

        # Audio & Presentation
        audio_sys = SkillEaterAudioSystem()
        kernel.register_system("skill_eater_audio_system", audio_sys)

        pres_sys = SkillEaterPresentationSystem(audio_system=audio_sys)
        kernel.register_system("skill_eater_presentation_system", pres_sys)

        # Combat
        combat_sys = SkillEaterCombatSystem(
            registry=registry, audio=audio_sys, presentation=pres_sys
        )
        kernel.register_system("skill_eater_combat_system", combat_sys)

        # Synthesis
        synth_sys = SkillEaterSynthesisSystem(
            registry=registry, audio=audio_sys, presentation=pres_sys
        )
        kernel.register_system("skill_eater_synthesis_system", synth_sys)

        # Economy, Servants, Exploration, Meta Quest
        econ_sys = SkillEaterEconomySystem(
            registry=registry, audio=audio_sys, presentation=pres_sys
        )
        kernel.register_system("skill_eater_economy_system", econ_sys)

        servant_sys = SkillEaterServantSystem(
            registry=registry, audio=audio_sys, presentation=pres_sys
        )
        kernel.register_system("skill_eater_servant_system", servant_sys)

        meta_sys = SkillEaterQuestSystem(registry=registry, audio=audio_sys, presentation=pres_sys)
        kernel.register_system("skill_eater_meta_quest_system", meta_sys)

        # Reincarnation system for meta_state
        reincarnation_sys = SkillEaterReincarnationSystem(registry=registry, audio=audio_sys, presentation=pres_sys)
        kernel.register_system("skill_eater_reincarnation_system", reincarnation_sys)

        explore_sys = SkillEaterExplorationSystem(audio=audio_sys, presentation=pres_sys)
        kernel.register_system("skill_eater_exploration_system", explore_sys)

        # Template Intervention System (Phase C)
        templates = load_templates("data/templates")
        meta_intervention = TemplateEventGenerator(templates=templates)
        kernel.register_system("skill_eater_meta_intervention", meta_intervention)

        # Intervention Engine (Phase D)
        reincarnation_sys = kernel.get_system("skill_eater_reincarnation_system")
        meta_quest = kernel.get_system("skill_eater_meta_quest_system")
        intervention_engine = InterventionEngine(
            registry=registry,
            presentation=pres_sys,
            rule_engine=meta_quest.rule_engine if meta_quest else None,
            meta_state=reincarnation_sys.meta_state if reincarnation_sys else None,
            templates=templates,
        )
        kernel.register_system("skill_eater_intervention_engine", intervention_engine)

        # Wire generator to exploration system
        explore_sys.template_generator = meta_intervention

        # Phase 2-5 Advanced Subsystems
        kernel.register_system("skill_eater_toxicity_manager", SkillToxicityManager())
        kernel.register_system("slum_base_expansion_manager", SlumBaseExpansionManager())
        kernel.register_system("skill_eater_pet_dispatch_manager", PetDispatchManager())
        kernel.register_system("skill_eater_underground_arena", UndergroundArenaManager())
        kernel.register_system("skill_eater_bounty_system", MidasBountyManager())
        kernel.register_system("skill_eater_ascension_board", AscensionBoard())
        kernel.register_system("skill_eater_concept_crystal", ConceptCrystallizer())
        kernel.register_system("skill_eater_temporal_vault", TemporalVaultManager())
        kernel.register_system("skill_eater_epilogue_manager", EpilogueAndTransitionManager())

    def teardown(self, kernel: Kernel) -> None:
        pass
