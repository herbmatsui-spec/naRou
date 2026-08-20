"""
Elona Roguelike - Engine integration module (i18n).

Thin wrapper that exposes a LocalizationManager bound to the game engine so
other systems can fetch localized strings through a shared entry point.
"""

from __future__ import annotations

import logging

from localization_manager import LocalizationManager


class GameLocalizer:
    """Engine-level localization helper."""

    def __init__(self, engine: object = None, language: str = "en") -> None:
        self.engine = engine
        self._manager = LocalizationManager()
        self._manager.set_language(language)

    @property
    def manager(self) -> LocalizationManager:
        return self._manager

    def localize(self, key: str, language: str = None) -> str:
        return self._manager.get_text(key, language)

    def set_language(self, language: str) -> bool:
        return self._manager.set_language(language)


def get_localizer(engine: object = None, language: str = "en") -> GameLocalizer:
    """Return a GameLocalizer instance bound to *engine*."""
    return GameLocalizer(engine=engine, language=language)


import atexit


def _shutdown_hook():
    logging.getLogger(__name__).info("Engine shutdown hook executed")
    logging.shutdown()


atexit.register(_shutdown_hook)

__all__ = ["GameLocalizer", "get_localizer"]
