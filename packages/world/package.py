from __future__ import annotations

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


class WorldPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="world",
            provides=[
                "procedural_dungeon_generator",
                "world_event_manager",
                "archaeology_manager",
                "world_state_manager",
                "dungeon_theme_registry",
            ],
            requires=["event_bus", "entity_manager"],
            dependencies=["core"],
        )

    def setup(self, kernel: Kernel) -> None:
        from archaeology_system import ArchaeologyManager, ArchaeologyRegistry
        from procedural_dungeon_generator import DungeonThemeRegistry, ProceduralDungeonGenerator
        from world_event_system import WorldEventManager, WorldEventRegistry
        from world_state_system import WorldStateManager, WorldStateRegistry

        theme_reg = DungeonThemeRegistry()
        theme_reg.load()
        kernel.register_system("dungeon_theme_registry", theme_reg)
        kernel.register_system(
            "procedural_dungeon_generator", ProceduralDungeonGenerator(theme_reg)
        )

        world_event_reg = WorldEventRegistry()
        world_event_reg.load()
        kernel.register_system("world_event_manager", WorldEventManager(world_event_reg))

        archaeology_reg = ArchaeologyRegistry()
        archaeology_reg.load()
        kernel.register_system("archaeology_manager", ArchaeologyManager(archaeology_reg))

        world_state_reg = WorldStateRegistry()
        world_state_reg.load()
        kernel.register_system("world_state_manager", WorldStateManager(world_state_reg))

    def teardown(self, kernel: Kernel) -> None:
        pass
