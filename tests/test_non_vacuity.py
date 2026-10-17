"""The non-vacuity helpers themselves are under test.

A guard that is never checked is exactly the failure mode this module exists to
catch, so the guards get their own tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.helpers.non_vacuity import (  # noqa: E402
    NonVacuousViolation,
    assert_can_fail,
    assert_distinguishes,
)


def _is_45(value: int) -> None:
    if value != 45:
        raise AssertionError(f"expected 45, got {value}")


class TestAssertDistinguishes:
    def test_passes_when_check_separates_good_from_bad(self):
        assert_distinguishes(_is_45, 45, 46, label="max_hp")

    def test_fails_when_check_accepts_both(self):
        # A vacuous check: never raises, so it guards nothing.
        with pytest.raises(NonVacuousViolation, match="cannot fail"):
            assert_distinguishes(lambda v: None, 45, 46, label="vacuous")

    def test_fails_when_check_rejects_the_good_value(self):
        with pytest.raises(NonVacuousViolation, match="rejected the correct value"):
            assert_distinguishes(lambda v: _is_45(99), 45, 46, label="over-tight")

    def test_bad_value_may_fail_with_any_exception(self):
        # The probe only needs the check to *notice* the corruption.
        assert_distinguishes(lambda v: 1 / v, 2, 0, label="division")


class TestAssertCanFail:
    def test_passes_when_probe_raises(self):
        assert_can_fail(lambda: _is_45(46), label="hp")

    def test_fails_when_probe_passes(self):
        with pytest.raises(NonVacuousViolation, match="detects nothing"):
            assert_can_fail(lambda: _is_45(45), label="hp")

    def test_reports_unexpected_exception_type(self):
        with pytest.raises(NonVacuousViolation, match="got ValueError"):
            assert_can_fail(lambda: int("x"), label="parse")
