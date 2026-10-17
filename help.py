"""
Elona Roguelike - Help system integration module (i18n).

Localized help text used by the in-game help screen and tutorials.
"""

from __future__ import annotations

from localization_manager import LocalizationManager


def help_entries(language: str = "en") -> dict[str, str]:
    """Return a mapping of help topic -> localized description."""
    mgr = LocalizationManager()
    topics = ["menu", "play", "save", "load", "settings", "language", "back", "close"]
    return {t: mgr.get_text(t, language) for t in topics}


__all__ = ["help_entries"]
