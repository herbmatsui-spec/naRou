"""Non-vacuity probes.

This repo has produced a green test that could no longer fail three separate
times (a README badge, a balance tool printing PASS, and a duplicate-detection
assertion disarmed by a storage refactor). The only defence that worked in all
three cases was the same: break one thing on purpose and watch the test go red.

These two helpers make that cheap enough to do every time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class NonVacuousViolation(AssertionError):
    """Raised when a probe proves it cannot detect the breakage it targets."""


def assert_can_fail(probe: Callable[[], Any], *, expect: type[BaseException] = AssertionError,
                    label: str = "probe") -> None:
    """Assert ``probe`` raises ``expect``.

    For steps that deliberately introduce a red test: this proves the redness
    is a real assertion failure and not an import error or a typo.
    """
    try:
        probe()
    except expect:
        return
    except BaseException as exc:  # noqa: BLE001
        raise NonVacuousViolation(
            f"{label}: expected {expect.__name__}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise NonVacuousViolation(
        f"{label}: expected the probe to fail, but it passed — the test detects nothing."
    )


def assert_distinguishes(check: Callable[[Any], Any], good: T, bad: T, *,
                         label: str = "check") -> None:
    """Assert ``check(good)`` passes and ``check(bad)`` raises.

    This is the workhorse. ``check`` is the assertion a test actually makes,
    ``good`` a correct value and ``bad`` a deliberately corrupted one. Passing
    proves the assertion still discriminates rather than being vacuously true.

    Example::

        assert_distinguishes(_assert_hp_is_45, player.hp, player.hp + 1,
                              label="starting max_hp")
    """
    try:
        check(good)
    except BaseException as exc:  # noqa: BLE001
        raise NonVacuousViolation(
            f"{label}: the check rejected the correct value {good!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    try:
        check(bad)
    except BaseException:
        return
    raise NonVacuousViolation(
        f"{label}: the check accepted both {good!r} and {bad!r} — it cannot fail."
    )


__all__ = ["NonVacuousViolation", "assert_can_fail", "assert_distinguishes"]
