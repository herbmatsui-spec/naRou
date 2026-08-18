"""
Elona Roguelike - Documentation integration module (i18n).

Generates localized documentation fragments from the text bundles.
"""

from __future__ import annotations
from typing import Dict, List

from localization_manager import LocalizationManager


def build_localized_doc(language: str = "en") -> str:
    """Return a short localized documentation snippet."""
    mgr = LocalizationManager()
    lines = [
        mgr.get_text("game_title", language),
        mgr.get_text("description", language),
        mgr.get_text("language", language) + ": " + language,
    ]
    return "\n".join(lines)


__all__ = ["build_localized_doc"]
