"""setup_coordinator: initializes Engine subsystems (extracted from game.py)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Engine


def setup_systems(engine: "Engine") -> None:
    """各種マネージャーとサブシステムの生成・初期化 (Step 8)"""
    from advanced_systems import UniqueItemManager
    from ai_system import AdvancedAISystem
    from data_manager import DataManager
    from fx_manager import FXManager
    from skill_fusion_system import FusionRegistry
    from ui_fx_systems import NotificationManager, TutorialManager

    # Core systems are now provided by CorePackage via Kernel
    engine.fx_manager = FXManager(event_bus=engine.event_bus)
    engine.unique_mgr = UniqueItemManager()

    engine.fusion_registry = FusionRegistry()
    engine.fusion_registry.load()

    # Data & AI Systems
    engine.data_manager = engine.systems_coordinator.register_system(
        "data_manager", DataManager()
    )
    engine.ai_system = engine.systems_coordinator.register_system(
        "ai_system", AdvancedAISystem()
    )

    # UX & FX Systems
    engine.tutorial_manager = TutorialManager("data/tutorial_guides.yaml")
    engine.notification_manager = NotificationManager()

    # 一括初期化 (Step 14)
    engine.systems_coordinator.initialize_all(engine)
