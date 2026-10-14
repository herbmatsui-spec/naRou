"""Tests for skill_eater_presentation_system module."""

from __future__ import annotations

from skill_eater_presentation_system import REQUIRED_EMOTE_FILES


def test_required_emote_files_is_dict():
    assert isinstance(REQUIRED_EMOTE_FILES, dict)
    assert len(REQUIRED_EMOTE_FILES) > 0