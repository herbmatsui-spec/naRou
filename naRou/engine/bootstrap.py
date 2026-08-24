from __future__ import annotations

"""
Bootstrap module for Engine initialization.
Aggregates heavy imports and package loading to avoid circular references in engine.py.
"""

import logging

logger = logging.getLogger(__name__)

from naRou.exceptions import SystemInitError

from naRou.packages.character.package import CharacterPackage
from naRou.packages.core.package import CorePackage
from naRou.packages.gameplay.package import GameplayPackage
from naRou.packages.meta.package import MetaPackage
from naRou.packages.narrative.package import NarrativePackage
from naRou.packages.platform.package import PlatformPackage
from naRou.packages.social.package import SocialPackage
from naRou.packages.world.package import WorldPackage
from naRou.packages.world_a.package import WorldAPackage
from naRou.packages.core.kernel.kernel import Kernel
from naRou.core.world_state_manager import GameStateInitializer
from naRou.core.system_initializer import SystemInitializer
from naRou.core.systems.setup_coordinator import setup_systems
from naRou.core.systems.setup_coordinator import setup_systems
from naRou.core.systems.setup_coordinator import setup_systems
from naRou.core.systems.setup_coordinator import setup_systems
from naRou.core.systems.setup_coordinator import setup_systems

def build_kernel():
    """Build and return the Kernel with core packages loaded."""
    try:
        kernel = Kernel()
        kernel.load_package(CorePackage())
        kernel.load_package(GameplayPackage())
        kernel.load_package(CharacterPackage())
        kernel.load_package(SocialPackage())
        kernel.load_package(MetaPackage())
        kernel.load_package(WorldPackage())
        kernel.load_package(NarrativePackage())
        kernel.load_package(PlatformPackage())
        kernel.load_package(WorldAPackage())
        return kernel
    except Exception as e:
        logger.exception("Failed to load core packages during engine initialization: %s", e)
        raise SystemInitError(f"Package initialization failed: {e}") from e
