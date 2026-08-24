"""
Dependency layer constants for engine refactor.
Defines the architectural layers to prevent circular imports.
"""

LAYER_EXCEPTIONS = "L0"
LAYER_KERNEL = "L1"
LAYER_PACKAGES = "L2"
LAYER_ENGINE_SUPPORT = "L3"
LAYER_IO_UI = "L4"
LAYER_ENGINE = "L5"