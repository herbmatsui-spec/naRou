"""
Elona Roguelike - Project integration module (i18n).

Provides project-level localization helpers used by build/CI tooling.
"""

from __future__ import annotations

from localization_manager import LocalizationManager


def localize_project_string(key: str, language: str = "en") -> str:
    """Localize a project-level string."""
    mgr = LocalizationManager()
    return mgr.get_text(key, language)


def available_languages() -> list[str]:
    """Return the list of supported project languages."""
    return LocalizationManager().get_supported_languages()


__all__ = ["localize_project_string", "available_languages"]
