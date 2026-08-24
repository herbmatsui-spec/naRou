from __future__ import annotations

from naRou.packages.core.kernel.kernel import Kernel
from naRou.packages.core.kernel.package import IPackage, PackageMetadata


class MetaPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="meta",
            provides=[
                "achievement_manager",
                "reincarnation_manager",
                "inheritance_manager",
                "karma_manager",
                "reincarnation_dungeon_manager",
                "legacy_skill_manager",
                "challenge_manager",
                "meta_progression_manager",
                "title_manager",
            ],
            requires=["event_bus", "entity_manager"],
            dependencies=["core", "character"],
        )

    def setup(self, kernel: Kernel) -> None:
        from naRou.achievement_system import AchievementManager, AchievementRegistry
        from naRou.inheritance_system import InheritanceManager, InheritanceRegistry
        from naRou.karma_system import KarmaManager, KarmaRegistry
        from naRou.legacy_skill_system import LegacySkillManager, LegacySkillRegistry
        from naRou.meta_progression_system import MetaProgressionManager, MetaProgressionRegistry
        from naRou.reincarnation_challenge_system import (
            ReincarnationChallengeManager,
            ReincarnationChallengeRegistry,
        )
        from naRou.reincarnation_dungeon_system import (
            ReincarnationDungeonManager,
            ReincarnationDungeonRegistry,
        )
        from naRou.reincarnation_system import ReincarnationManager, ReincarnationRegistry
        from naRou.title_system import MANAGER as TitleManager

        ach_reg = AchievementRegistry()
        ach_reg.load()
        kernel.register_system("achievement_manager", AchievementManager(ach_reg))

        reinc_reg = ReincarnationRegistry()
        reinc_reg.load()
        kernel.register_system("reincarnation_manager", ReincarnationManager(reinc_reg))

        inh_reg = InheritanceRegistry()
        inh_reg.load()
        kernel.register_system("inheritance_manager", InheritanceManager(inh_reg))

        karma_reg = KarmaRegistry()
        karma_reg.load()
        kernel.register_system("karma_manager", KarmaManager(karma_reg))

        reinc_dungeon_reg = ReincarnationDungeonRegistry()
        reinc_dungeon_reg.load()
        kernel.register_system(
            "reincarnation_dungeon_manager",
            ReincarnationDungeonManager(reinc_dungeon_reg),
        )

        legacy_reg = LegacySkillRegistry()
        legacy_reg.load()
        kernel.register_system("legacy_skill_manager", LegacySkillManager(legacy_reg))

        challenge_reg = ReincarnationChallengeRegistry()
        challenge_reg.load()
        kernel.register_system("challenge_manager", ReincarnationChallengeManager(challenge_reg))

        meta_reg = MetaProgressionRegistry()
        meta_reg.load()
        kernel.register_system("meta_progression_manager", MetaProgressionManager(meta_reg))

        kernel.register_system("title_manager", TitleManager)

    def teardown(self, kernel: Kernel) -> None:
        pass
