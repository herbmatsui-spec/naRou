"""
Elona Roguelike - Logging integration module (i18n).

Provides localized log message formatting on top of the standard logger.
"""

from __future__ import annotations

import logging

from localization_manager import LocalizationManager


def localized_log(key: str, language: str = "en", level: str = "info") -> None:
    """Emit a localized log message at the given level."""
    mgr = LocalizationManager()
    message = mgr.get_text(key, language)
    logger = logging.getLogger("naRou")
    getattr(logger, level.lower(), logger.info)(message)


__all__ = ["localized_log"]
