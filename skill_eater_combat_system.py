"""Compatibility wrapper for the original `skill_eater_combat_system` module.
It re-exports the combat system implementation from the new package
`skill_eater.combat`. This maintains backward compatibility for existing
imports while allowing the codebase to transition to the package structure.
"""
# Re-export all public symbols from the new combat package implementation
from skill_eater.combat.engine import *  # noqa: F403,F401
