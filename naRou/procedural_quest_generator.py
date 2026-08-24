"""Forwarding shim for naRou.quest_generation.

The implementation was split into naRou/quest_generation/{models,registry,generator,manager}.py.
This module preserves backward-compatible imports.
"""
from naRou.quest_generation import *  # noqa: F401,F403
from naRou.quest_generation import (  # noqa: F401
    GENERATOR,
    MANAGER,
    PROCEDURAL_QUEST_GENERATOR,
    REGISTRY,
)
