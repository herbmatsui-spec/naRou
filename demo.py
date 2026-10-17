"""
Elona Roguelike - Demo integration module (i18n).

Localized demo strings used by interactive showcases and tutorials.
"""

from __future__ import annotations

from localization_manager import LocalizationManager


def demo_greeting(language: str = "en") -> str:
    """Return a localized greeting for the demo screen."""
    mgr = LocalizationManager()
    return mgr.get_text("welcome", language)


def demo_strings(language: str = "en") -> dict[str, str]:
    """Return a bundle of localized strings used by the demo."""
    mgr = LocalizationManager()
    keys = ["hello", "welcome", "play", "options", "quit", "credits"]
    return {k: mgr.get_text(k, language) for k in keys}


__all__ = ["demo_greeting", "demo_strings"]
