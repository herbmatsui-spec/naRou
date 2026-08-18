"""
Elona Roguelike - Internationalization test helpers (i18n).

Lightweight helpers that exercise LocalizationManager so the test suite can
verify language coverage and fallback behaviour.
"""

from __future__ import annotations
from typing import Dict, List

from localization_manager import LocalizationManager


def run_localization_tests() -> Dict[str, object]:
    """Run basic localization self-tests and return a result summary."""
    mgr = LocalizationManager()
    results: Dict[str, object] = {
        "supported": mgr.get_supported_languages(),
        "stats": mgr.get_stats(),
        "validation": mgr.validate(),
        "passed": mgr.test(),
    }
    return results


__all__ = ["run_localization_tests"]
