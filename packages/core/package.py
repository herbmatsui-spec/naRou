from __future__ import annotations
from packages.core.kernel.package import IPackage, PackageMetadata
from packages.core.kernel.kernel import Kernel


class CorePackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="core",
            provides=[
                "event_bus",
                "time_system",
                "turn_queue",
                "renderer",
                "entity_manager",
                "message_log",
                "debug_console",
            ],
            dependencies=[],
        )

    def setup(self, kernel: Kernel) -> None:
        from core_framework import EventBus, MessageLog
        from turn_manager import TimeSystem, TurnQueue
        from entity_manager import EntityManager
        from renderer import Renderer, get_renderer
        from advanced_systems import DebugConsole

        kernel.register_system("event_bus", EventBus())
        kernel.register_system("time_system", TimeSystem(event_bus=kernel.get_system("event_bus")))
        kernel.register_system("turn_queue", TurnQueue(kernel.get_system("time_system")))
        kernel.register_system("entity_manager", EntityManager())
        kernel.register_system("renderer", get_renderer())
        kernel.register_system("message_log", MessageLog(max_history=200))
        kernel.register_system("debug_console", DebugConsole())

        kernel.set_event_bus(kernel.get_system("event_bus"))

    def teardown(self, kernel: Kernel) -> None:
        pass