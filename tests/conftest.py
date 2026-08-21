"""Shared pytest fixtures for the naRou test suite.

Provides a lightweight Engine factory that avoids the full package/Kernel
initialization (which requires a rendering context). Tests that need a
partially-initialized engine can use ``make_test_engine``.
"""
from __future__ import annotations

from typing import Any

import pytest

import game


def make_test_engine() -> "game.Engine":
    """Build an Engine without running the full Kernel/package initialization.

    The returned object is a bare Engine instance suitable for unit tests
    that only need attribute-level behavior (components, managers, helpers).
    """
    engine = game.Engine.__new__(game.Engine)
    engine.kernel = _DummyKernel()
    return engine


class _DummyKernel:
    """Minimal Kernel stand-in exposing the get_system API used by Engine."""

    def __init__(self) -> None:
        self._systems: dict[str, Any] = {}

    def get_system(self, name: str, default: Any = None) -> Any:
        return self._systems.get(name, default)

    def has_system(self, name: str) -> bool:
        return name in self._systems


@pytest.fixture
def test_engine() -> "game.Engine":
    return make_test_engine()
