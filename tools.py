"""
Elona Roguelike - Developer tools integration module (i18n).

Command-line friendly helpers for inspecting and validating localized text.
"""

from __future__ import annotations
from typing import List, Optional

from localization_manager import LocalizationManager


def list_missing_keys() -> dict:
    """Return a mapping of language -> missing keys (relative to default)."""
    mgr = LocalizationManager()
    return mgr.validate()


def dump_language(language: str) -> dict:
    """Return all entries for a given language."""
    mgr = LocalizationManager()
    return mgr.get_language_data(language)


__all__ = ["list_missing_keys", "dump_language"]
