from __future__ import annotations

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


class NarrativePackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="narrative",
            provides=[
                "storyteller_manager",
                "choice_manager",
                "dialogue_manager",
                "main_quest_system",
                "journal_ui",
            ],
            requires=["event_bus", "entity_manager"],
            dependencies=["core", "world"],
        )

    def setup(self, kernel: Kernel) -> None:
        from choice_system import ChoiceManager, ChoiceRegistry
        from dialogue_system import DialogueManager
        from journal_ui import JournalUI
        from main_quest_system import MainQuestSystem
        from storyteller_system import StorytellerManager, StorytellerRegistry

        story_reg = StorytellerRegistry()
        story_reg.load()
        kernel.register_system("storyteller_manager", StorytellerManager(story_reg))

        choice_reg = ChoiceRegistry()
        choice_reg.load()
        kernel.register_system("choice_manager", ChoiceManager(choice_reg))

        kernel.register_system("dialogue_manager", DialogueManager())
        kernel.register_system("main_quest_system", MainQuestSystem())
        kernel.register_system("journal_ui", JournalUI())

    def teardown(self, kernel: Kernel) -> None:
        pass
