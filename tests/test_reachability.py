"""Reachability: a declaration nobody can reach is a lie told by the data file.

Three properties. Two are expected to fail on `c7def04`` and are marked
``xfail(strict=True)``; the third passes today and guards the honesty convention
already used in ``data/meta_progression.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from systems import SurvivalSystem

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def _production_sources() -> list[Path]:
    out = []
    for path in REPO_ROOT.rglob("*.py"):
        parts = set(path.relative_to(REPO_ROOT).parts)
        if parts & {"build", "tests", ".worktrees", "venv"}:
            continue
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        out.append(path)
    return out


def _quest_ids_and_successors() -> tuple[set[str], dict[str, str]]:
    quests = yaml.safe_load((DATA_DIR / "main_quests.yaml").read_text(encoding="utf-8")) or {}
    ids: set[str] = set()
    successors: dict[str, str] = {}
    entries = quests.get("main_quests", []) or []
    assert entries, "main_quests.yaml parsed to an empty list — the guard would be vacuous"
    for entry in entries:
        quest_id = entry.get("quest_id")
        assert quest_id, f"main quest without a quest_id: {entry!r}"
        ids.add(quest_id)
        nxt = entry.get("next_quest_id")
        if nxt:
            successors[quest_id] = nxt
    return ids, successors


def test_quest_chain_terminates():
    ids, successors = _quest_ids_and_successors()
    dangling = {src: dst for src, dst in successors.items() if dst not in ids}
    assert dangling == {}, f"quest chain points at quests that do not exist: {dangling}"


def test_meta_progression_bonuses_are_read_or_explicitly_reserved():
    """A bonus token must be read by production code, or explicitly deferred.

    ``data/meta_progression.yaml`` already marks its unrealised bonuses with a
    ``reserved:`` key plus a comment naming the blocker. That is the honest form.
    A token that is neither read nor reserved is a silent lie.
    """
    data = yaml.safe_load((DATA_DIR / "meta_progression.yaml").read_text(encoding="utf-8")) or {}
    corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in _production_sources()
    )

    unhonest: list[str] = []
    for tracker, body in data.get("meta_progression", {}).items():
        for milestone in body.get("milestones", []) or []:
            bonus = milestone.get("reward_bonus")
            if not bonus:
                continue
            if "reserved" in milestone:
                continue
            if bonus not in corpus:
                unhonest.append(f"{tracker}:{milestone.get('count')}={bonus}")

    assert unhonest == [], (
        "reward_bonus tokens with neither a reader nor a reserved: marker: " f"{unhonest}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "main_quest_system writes to engine.survival_system (kernel) while the engine "
        "reads engine.survival (world_state_manager) — two different objects (Step 27)"
    ),
)
def test_main_quest_rewards_reach_the_player(test_engine):
    sentinel = SurvivalSystem()
    test_engine.kernel._systems["survival_system"] = sentinel
    assert test_engine.survival_system is sentinel
    assert test_engine.survival is sentinel, (
        "quest rewards are credited to a SurvivalSystem the engine never reads"
    )
