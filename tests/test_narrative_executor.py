"""
Test Module for Narrative Executor (Phase 4 Steps 15-16)
"""

from __future__ import annotations

import pytest

from narrative_executor import NarrativeContext, NarrativeExecutor, NarrativeState


class MockEntity:
    def __init__(self, name="hero"):
        self.name = name


def test_narrative_executor_start():
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player")

    state = executor.start_narrative("prologue_branching", player)

    assert state is not None
    assert state.dag_id == "prologue_branching"
    assert not state.completed


def test_story_choices_loading():
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    choice = executor.get_choice("farm_survivor_saved")
    assert choice is not None
    assert choice.id == "farm_survivor_saved"


def test_story_endings_loading():
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    ending = executor.get_ending("goblin_peace_bringer")
    assert ending is not None
    assert ending.id == "goblin_peace_bringer"


def test_apply_choice_consequence():
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    context = NarrativeContext(flags=set(), variables={})

    logs = executor.apply_choice_consequence("farm_survivor_saved", context)
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert context.variables.get("gold", 0) > 0
