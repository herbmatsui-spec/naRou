"""Partial-coverage tests for quest / narrative systems.

Modules covered:
- narrative_executor.py  : step execution, condition checks, dialogue flow
- main_quest_system.py   : quest progression, chapter advancement
- quest_fragment_rewards.py : fragment drop distribution
- quest_dungeon_spec.py  : dungeon spec generation / validation

External dependencies (YAML data files, global world-state phase, fragment
registry, narrative singleton) are isolated via tmp_path and monkeypatching.
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

import narrative_executor
import quest_dungeon_spec as qds
import quest_fragment_rewards as qfr
from main_quest_system import MainQuest, MainQuestSystem, QuestObjective, QuestStatus
from narrative_executor import NarrativeExecutor, NarrativeState
from quest_narrative_dag import (
    NarrativeContext,
    NarrativeDAG,
    NarrativeEdge,
    NarrativeEdgeType,
    NarrativeNode,
    NarrativeNodeType,
)
from world_state_system import REGISTRY, WorldPhase

# ============================================================================
# Helpers
# ============================================================================


class MockPlayer:
    """Minimal mock entity: the executor only reads `name` via getattr."""

    def __init__(self, name: str):
        self.name = name


class MockQuestPlayer:
    """Bare player object: EvaluationContext probes optional attributes."""

    def __init__(self, name: str = "quest_runner"):
        self.name = name


class PinnedRng:
    """Deterministic stand-in for the `random` module with pinned values."""

    def __init__(self, random_value: float = 0.5, randint_value: int | None = None):
        self.random_value = random_value
        self.randint_value = randint_value

    def random(self) -> float:
        return self.random_value

    def randint(self, a: int, b: int) -> int:
        return self.randint_value if self.randint_value is not None else a


class FakeCondition:
    """Mock ConditionNode for unlock/evaluate checks."""

    def __init__(self, result: bool):
        self.result = result
        self.calls = 0

    def evaluate(self, context) -> bool:
        self.calls += 1
        return self.result


def write_yaml(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def make_executor(tmp_path, dags=None, choices=None, endings=None) -> NarrativeExecutor:
    data_path = tmp_path / "narratives.yaml"
    choices_path = tmp_path / "choices.yaml"
    endings_path = tmp_path / "endings.yaml"
    if dags is not None:
        write_yaml(data_path, {"narrative_dags": dags})
    if choices is not None:
        write_yaml(choices_path, {"choice_consequences": choices})
    if endings is not None:
        write_yaml(endings_path, {"story_endings": endings})
    return NarrativeExecutor(str(data_path), str(choices_path), str(endings_path))


def standard_dag_yaml() -> dict:
    return {
        "dialogue_dag": {
            "nodes": {
                "n_start": {"type": "START", "title": "始まり", "set_flags": ["met_elder"]},
                "n_choice": {"type": "CHOICE", "title": "どうする？"},
                "n_end_good": {"type": "END", "title": "善い結末", "rewards": {"xp": 5}},
                "n_end_bad": {"type": "END", "title": "悪い結末"},
            },
            "edges": [
                {"edge_id": "e_auto", "source": "n_start", "target": "n_choice", "type": "AUTO"},
                {
                    "edge_id": "e_good",
                    "source": "n_choice",
                    "target": "n_end_good",
                    "type": "CHOICE",
                    "choice_text": "助ける",
                    "weight": 2.0,
                    "effects": {"helped": 1},
                },
                {
                    "edge_id": "e_bad",
                    "source": "n_choice",
                    "target": "n_end_bad",
                    "type": "CHOICE",
                    "choice_text": "無視",
                    "weight": 1.0,
                },
            ],
        }
    }


STANDARD_CHOICES = {
    "e_good": {
        "description": "村人を助ける",
        "immediate_effects": [{"type": "gain_gold", "value": 50}],
        "long_term_effects": [{"type": "reputation", "value": 10}],
        "world_state_changes": {"peace": True},
    },
}

STANDARD_ENDINGS = {
    "n_end_good": {
        "name": "救済の結末",
        "description": "村に平和が戻った。",
        "unlock_conditions": ["has_flag:met_elder"],
        "ending_scene": "scene_good",
        "rewards": {
            "title": "救世主",
            "gold": 100,
            "item": "potion_minor",
            "ending_scene": "scene_good",
        },
    },
}


@pytest.fixture(autouse=True)
def _reset_world_phase():
    """Keep the global world-state phase deterministic across tests."""
    REGISTRY.get_template().current_phase = WorldPhase.BEGINNING
    yield
    REGISTRY.get_template().current_phase = WorldPhase.BEGINNING


@pytest.fixture(autouse=True)
def _restore_fragment_registry():
    saved = dict(qfr._FRAGMENT_DROP_TABLES)
    yield
    qfr._FRAGMENT_DROP_TABLES.clear()
    qfr._FRAGMENT_DROP_TABLES.update(saved)


# ============================================================================
# narrative_executor.py - loading
# ============================================================================


class TestNarrativeExecutorLoading:
    def test_loads_dags_choices_and_endings_from_yaml(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml(), STANDARD_CHOICES, STANDARD_ENDINGS)
        dag = executor.get_dag("dialogue_dag")
        assert dag is not None
        assert dag.get_start_node().node_id == "n_start"
        assert len(dag.get_end_nodes()) == 2
        choice = executor.get_choice("e_good")
        assert choice is not None
        assert choice.description == "村人を助ける"
        ending = executor.get_ending("n_end_good")
        assert ending is not None
        assert ending.name == "救済の結末"

    def test_missing_files_yield_empty_executor(self, tmp_path):
        executor = make_executor(tmp_path)
        assert executor.get_dag("anything") is None
        assert executor.get_choice("x") is None
        assert executor.get_ending("x") is None

    def test_start_unknown_dag_returns_none(self, tmp_path):
        executor = make_executor(tmp_path)
        assert executor.start_narrative("nope", MockPlayer("p")) is None

    def test_start_dag_without_start_node_returns_none(self, tmp_path):
        dags = {"no_start": {"nodes": {"only": {"type": "EVENT"}}, "edges": []}}
        executor = make_executor(tmp_path, dags)
        assert executor.start_narrative("no_start", MockPlayer("p")) is None


# ============================================================================
# narrative_executor.py - dialogue flow with mock entities
# ============================================================================


class TestNarrativeDialogueFlow:
    def test_start_applies_auto_transition_chain(self, tmp_path):
        dags = {
            "chain": {
                "nodes": {
                    "s": {"type": "START", "set_flags": ["flag_start"]},
                    "mid": {"type": "EVENT", "set_flags": ["flag_mid"]},
                    "stop": {"type": "CHOICE"},
                },
                "edges": [
                    {"edge_id": "a1", "source": "s", "target": "mid", "type": "AUTO"},
                    {"edge_id": "a2", "source": "mid", "target": "stop", "type": "AUTO"},
                ],
            }
        }
        executor = make_executor(tmp_path, dags)
        state = executor.start_narrative("chain", MockPlayer("hero"))
        assert state is not None
        assert state.current_node_id == "stop"
        assert "flag_start" in state.flags
        assert "flag_mid" in state.flags
        assert state.history == ["s", "stop"]

    def test_full_dialogue_flow_choice_to_ending(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml(), STANDARD_CHOICES, STANDARD_ENDINGS)
        player = MockPlayer("hero")

        state = executor.start_narrative("dialogue_dag", player)
        assert state is not None
        assert state.current_node_id == "n_choice"
        assert not state.completed

        choices = executor.get_available_choices(player)
        assert [e.edge_id for e in choices] == ["e_good", "e_bad"]  # weight 降順

        logs = executor.make_choice(player, "e_good")
        joined = "\n".join(logs)
        assert "ゴールド獲得: +50" in joined
        assert "長期効果登録: reputation = 10" in joined
        assert "世界状態更新: peace = True" in joined
        assert "効果適用: helped = 1" in joined
        assert "完了しました" in joined
        assert "称号獲得: 救世主" in joined
        assert "ゴールド獲得: +100" in joined
        assert "アイテム獲得: potion_minor" in joined

        final = executor.get_active_state(player)
        assert final is not None
        assert final.completed is True
        assert final.ending_id == "n_end_good"
        assert final.variables["gold"] == 150  # 選択効果 +50 / エンディング報酬 +100
        assert final.variables["title"] == "救世主"
        assert final.variables["items"] == ["potion_minor"]
        assert final.variables["ending_scene"] == "scene_good"
        assert "met_elder" in final.flags

    def test_states_are_tracked_per_player(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml(), STANDARD_CHOICES)
        alice, bob = MockPlayer("alice"), MockPlayer("bob")
        s1 = executor.start_narrative("dialogue_dag", alice)
        s2 = executor.start_narrative("dialogue_dag", bob)
        assert s1 is not None and s2 is not None and s1 is not s2
        executor.make_choice(alice, "e_good")
        assert executor.get_active_state(alice).completed
        assert not executor.get_active_state(bob).completed

    def test_get_current_node_and_unknown_player(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        player = MockPlayer("cur")
        assert executor.get_current_node(player) is None
        executor.start_narrative("dialogue_dag", player)
        node = executor.get_current_node(player)
        assert node is not None
        assert node.node_id == "n_choice"

    def test_available_choices_empty_when_inactive_or_completed(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml(), STANDARD_CHOICES)
        player = MockPlayer("solo")
        assert executor.get_available_choices(player) == []
        executor.start_narrative("dialogue_dag", player)
        executor.make_choice(player, "e_bad")
        assert executor.get_available_choices(player) == []


class TestNarrativeMakeChoice:
    def test_make_choice_without_active_narrative(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        assert executor.make_choice(MockPlayer("ghost"), "e_good") == [
            "ナラティブが進行中ではありません"
        ]

    def test_make_choice_unknown_edge(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        player = MockPlayer("p")
        executor.start_narrative("dialogue_dag", player)
        assert executor.make_choice(player, "missing_edge") == ["指定された選択肢が見つかりません"]

    def test_make_choice_blocked_by_forbidden_flag(self, tmp_path):
        dags = {
            "gated": {
                "nodes": {"s": {"type": "START"}, "end": {"type": "END"}},
                "edges": [
                    {
                        "edge_id": "e_gate",
                        "source": "s",
                        "target": "end",
                        "type": "CHOICE",
                        "forbidden_flags": ["cursed"],
                    }
                ],
            }
        }
        executor = make_executor(tmp_path, dags)
        player = MockPlayer("cursed_one")
        executor.start_narrative("gated", player, initial_flags={"cursed"})
        assert executor.get_available_choices(player) == []
        assert executor.make_choice(player, "e_gate") == ["現在その選択肢は選べません"]

    def test_edge_required_flags_gate_availability(self, tmp_path):
        dags = {
            "keyed": {
                "nodes": {"s": {"type": "START"}, "end": {"type": "END"}},
                "edges": [
                    {
                        "edge_id": "e_key",
                        "source": "s",
                        "target": "end",
                        "type": "CHOICE",
                        "required_flags": ["has_key"],
                    }
                ],
            }
        }
        executor = make_executor(tmp_path, dags)
        locked = MockPlayer("thief")
        executor.start_narrative("keyed", locked)
        assert executor.get_available_choices(locked) == []

        keyed = MockPlayer("thief2")
        executor.start_narrative("keyed", keyed, initial_flags={"has_key"})
        assert [e.edge_id for e in executor.get_available_choices(keyed)] == ["e_key"]


class TestNarrativeChoiceConsequences:
    def test_unknown_choice_consequence_reports_missing(self, tmp_path):
        executor = make_executor(tmp_path)
        logs = executor.apply_choice_consequence("ghost_choice", NarrativeContext())
        assert logs == ["選択肢結果 ghost_choice が見つかりません"]

    def test_immediate_long_term_and_world_effects_applied(self, tmp_path):
        choices = {
            "c1": {
                "immediate_effects": [
                    {"type": "gain_gold", "value": 30},
                    {"type": "gain_karma", "value": -5},
                    {"type": "gain_exp", "value": 12},
                    {"type": "gain_piety", "value": 7},
                    {"type": "gain_mp_max", "value": 4},
                    {"type": "unknown_type", "value": 1},
                ],
                "long_term_effects": [{"type": "trauma", "value": 3}],
                "world_state_changes": {"famine": True},
            }
        }
        executor = make_executor(tmp_path, choices=choices)
        ctx = NarrativeContext(variables={"gold": 10})
        logs = executor.apply_choice_consequence("c1", ctx)
        joined = "\n".join(logs)
        assert "ゴールド獲得: +30" in joined
        assert "カルマ変化: -5" in joined
        assert "経験値獲得: +12" in joined
        assert "信仰心変化: +7" in joined
        assert "最大MP増加: +4" in joined
        assert "長期効果登録: trauma = 3" in joined
        assert "世界状態更新: famine = True" in joined
        assert ctx.variables["gold"] == 40
        assert ctx.variables["karma"] == -5
        assert ctx.variables["exp"] == 12
        assert ctx.variables["piety"] == 7
        assert ctx.variables["mp_max"] == 4
        assert ctx.variables["long_term_trauma"] == 3
        assert ctx.variables["world_famine"] is True


# ============================================================================
# narrative_executor.py - condition checks and endings
# ============================================================================


class TestNarrativeConditionChecks:
    @pytest.fixture
    def executor(self, tmp_path):
        return make_executor(tmp_path)

    @pytest.fixture
    def context(self):
        return NarrativeContext(flags={"brave"}, variables={"karma": 15, "total_kills": 120})

    def test_has_flag_condition(self, executor, context):
        assert executor._check_condition("has_flag:brave", context) is True
        assert executor._check_condition("has_flag:absent", context) is False

    def test_karma_good_condition(self, executor, context):
        assert executor._check_condition("karma_good_10", context) is True
        assert executor._check_condition("karma_good_20", context) is False

    def test_karma_evil_condition(self, executor):
        evil = NarrativeContext(variables={"karma": -7})
        assert executor._check_condition("karma_evil_5", evil) is True
        assert executor._check_condition("karma_evil_10", evil) is False

    def test_kill_total_condition(self, executor, context):
        assert executor._check_condition("kill_counts_total_100", context) is True
        assert executor._check_condition("kill_counts_total_500", context) is False

    def test_bare_flag_condition(self, executor, context):
        assert executor._check_condition("brave", context) is True
        assert executor._check_condition("coward", context) is False


class TestNarrativeEndings:
    def test_check_ending_unlock_unknown_ending(self, tmp_path):
        executor = make_executor(tmp_path)
        assert executor.check_ending_unlock("nope", NarrativeContext()) is False

    def test_check_ending_unlock_requires_all_conditions(self, tmp_path):
        executor = make_executor(tmp_path)
        executor._endings["dual"] = narrative_executor.StoryEnding(
            id="dual", unlock_conditions=["has_flag:brave", "karma_good_10"]
        )
        ctx = NarrativeContext(flags={"brave"}, variables={"karma": 15})
        assert executor.check_ending_unlock("dual", ctx) is True
        executor._endings["dual"].unlock_conditions.append("karma_good_50")
        assert executor.check_ending_unlock("dual", ctx) is False

    def test_get_available_endings_filters_unlocked(self, tmp_path):
        executor = make_executor(tmp_path)
        executor._endings["e1"] = narrative_executor.StoryEnding(id="e1", unlock_conditions=[])
        executor._endings["e2"] = narrative_executor.StoryEnding(
            id="e2", unlock_conditions=["has_flag:sealed"]
        )
        available = executor.get_available_endings(NarrativeContext())
        assert [e.id for e in available] == ["e1"]

    def test_grant_ending_rewards(self, tmp_path):
        executor = make_executor(tmp_path)
        executor._endings["rich"] = narrative_executor.StoryEnding(
            id="rich",
            rewards={"title": "覇者", "gold": 30, "item": "amulet", "ending_scene": "finale"},
        )
        ctx = NarrativeContext(variables={"gold": 5})
        logs = executor.grant_ending_rewards("rich", ctx)
        assert len(logs) == 4
        assert ctx.variables["title"] == "覇者"
        assert ctx.variables["gold"] == 35
        assert ctx.variables["items"] == ["amulet"]
        assert ctx.variables["ending_scene"] == "finale"

    def test_grant_ending_rewards_unknown(self, tmp_path):
        executor = make_executor(tmp_path)
        assert executor.grant_ending_rewards("ghost", NarrativeContext()) == [
            "エンディング ghost が見つかりません"
        ]


# ============================================================================
# narrative_executor.py - state persistence and forced transitions
# ============================================================================


class TestNarrativeStatePersistence:
    def test_narrative_state_serialization_roundtrip(self):
        state = NarrativeState(
            dag_id="d",
            current_node_id="n",
            flags={"a", "b"},
            variables={"gold": 5},
            history=["n"],
            completed=True,
            ending_id="n",
        )
        restored = NarrativeState.from_dict(state.to_dict())
        assert restored.dag_id == "d"
        assert restored.current_node_id == "n"
        assert restored.flags == {"a", "b"}
        assert restored.variables == {"gold": 5}
        assert restored.history == ["n"]
        assert restored.completed is True
        assert restored.ending_id == "n"

    def test_save_and_load_state_roundtrip(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml(), STANDARD_CHOICES, STANDARD_ENDINGS)
        saver = MockPlayer("saver")
        executor.start_narrative("dialogue_dag", saver)
        executor.make_choice(saver, "e_good")
        data = executor.save_state(saver)
        assert data is not None
        assert data["dag_id"] == "dialogue_dag"
        assert data["completed"] is True
        assert data["variables"]["gold"] == 150

        loader = MockPlayer("loader")
        assert executor.load_state(loader, data) is True
        loaded = executor.get_active_state(loader)
        assert loaded is not None
        assert loaded.current_node_id == data["current_node_id"]
        assert loaded.completed is True
        assert loaded.ending_id == "n_end_good"
        assert loaded.variables["gold"] == 150

    def test_save_state_without_active_narrative(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        assert executor.save_state(MockPlayer("p")) is None

    def test_load_state_unknown_dag_fails(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        assert executor.load_state(MockPlayer("p"), {"dag_id": "ghost", "current_node_id": "x"}) is False

    def test_load_state_corrupt_data_fails(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        assert executor.load_state(MockPlayer("p"), {}) is False

    def test_force_transition(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        player = MockPlayer("forced")
        executor.start_narrative("dialogue_dag", player)
        logs = executor.force_transition(player, "n_end_bad")
        assert logs == ["強制遷移: n_end_bad -> n_end_bad"]
        assert executor.get_active_state(player).current_node_id == "n_end_bad"

    def test_force_transition_errors(self, tmp_path):
        executor = make_executor(tmp_path, standard_dag_yaml())
        player = MockPlayer("forced")
        assert executor.force_transition(player, "n_end_bad") == [
            "アクティブなナラティブがありません"
        ]
        executor.start_narrative("dialogue_dag", player)
        assert executor.force_transition(player, "ghost_node") == ["対象ノードが存在しません"]

    def test_auto_transition_cycle_terminates(self, tmp_path):
        executor = make_executor(tmp_path)
        dag = NarrativeDAG("cycle")
        node_a = NarrativeNode("a", NarrativeNodeType.START)
        node_b = NarrativeNode("b", NarrativeNodeType.EVENT)
        node_a.add_edge(NarrativeEdge("eab", "a", "b", NarrativeEdgeType.AUTO))
        node_b.add_edge(NarrativeEdge("eba", "b", "a", NarrativeEdgeType.AUTO))
        dag.add_node(node_a)
        dag.add_node(node_b)
        result = executor._apply_auto_transitions(dag, "a", NarrativeContext())
        assert result in {"a", "b"}


# ============================================================================
# main_quest_system.py - progression and chapter advancement
# ============================================================================

QUESTS_YAML = {
    "main_quests": [
        {
            "quest_id": "chapter1_q1",
            "title": "第一章：封印の亀裂",
            "description": "スライムを退治せよ。",
            "required_phase": "BEGINNING",
            "objectives": [
                {
                    "objective_id": "kill_slimes",
                    "description": "スライムを倒す",
                    "target_type": "kill",
                    "target_id": "slime",
                    "required_count": 3,
                },
            ],
            "rewards": {"gold": 200},
            "next_quest_id": "chapter1_q2",
        },
        {
            "quest_id": "chapter1_q2",
            "title": "第二章：遺跡の謎",
            "description": "遺跡を探索せよ。",
            "required_phase": "BEGINNING",
            "objectives": [
                {
                    "objective_id": "visit_ruins",
                    "description": "遺跡へ向かう",
                    "target_type": "visit",
                    "target_id": "ruins",
                    "required_count": 1,
                },
            ],
            "rewards": {"gold": 300},
        },
    ]
}


@pytest.fixture
def quest_system(tmp_path):
    path = tmp_path / "main_quests.yaml"
    write_yaml(path, QUESTS_YAML)
    return MainQuestSystem(str(path))


class TestMainQuestProgression:
    def test_loads_quests_from_yaml(self, quest_system):
        assert set(quest_system.quests) == {"chapter1_q1", "chapter1_q2"}
        q1 = quest_system.quests["chapter1_q1"]
        assert q1.status is QuestStatus.LOCKED
        assert q1.objectives[0].target_id == "slime"
        assert q1.rewards == {"gold": 200}

    def test_auto_activates_locked_quest_and_counts_progress(self, quest_system):
        logs = quest_system.update_progress(MockQuestPlayer(), "kill", "slime", 2)
        assert quest_system.active_quest_id == "chapter1_q1"
        assert quest_system.quests["chapter1_q1"].status is QuestStatus.ACTIVE
        assert any("(2/3)" in line for line in logs)

    def test_wrong_target_does_not_progress(self, quest_system):
        quest_system.update_progress(MockQuestPlayer(), "kill", "slime", 1)
        logs = quest_system.update_progress(MockQuestPlayer(), "kill", "goblin", 1)
        assert logs == []
        obj = quest_system.quests["chapter1_q1"].objectives[0]
        assert obj.current_count == 1

    def test_completion_advances_chapter_to_next_quest(self, quest_system):
        quest_system.update_progress(MockQuestPlayer(), "kill", "slime", 3)
        q1 = quest_system.quests["chapter1_q1"]
        assert q1.status is QuestStatus.COMPLETED
        assert q1.objectives[0].is_completed
        assert quest_system.active_quest_id is None
        # チャプター進行: 次章が受注可能状態になる
        assert quest_system.quests["chapter1_q2"].status is QuestStatus.AVAILABLE

    def test_completion_logs_and_gold_reward(self, tmp_path):
        path = tmp_path / "main_quests.yaml"
        write_yaml(path, QUESTS_YAML)
        system = MainQuestSystem(str(path))
        engine = SimpleNamespace(survival=SimpleNamespace(gold=0))
        logs = system.update_progress(MockQuestPlayer(), "kill", "slime", 3, engine=engine)
        assert any("★メインクエスト【第一章：封印の亀裂】を完了した！" in line for line in logs)
        assert engine.survival.gold == 200

    def test_available_next_quest_is_not_auto_activated(self, quest_system):
        quest_system.update_progress(MockQuestPlayer(), "kill", "slime", 3)
        logs = quest_system.update_progress(MockQuestPlayer(), "visit", "ruins", 1)
        # LOCKED のクエストのみ自動受注される（AVAILABLE は対象外）
        assert quest_system.active_quest_id is None
        assert logs == []
        obj = quest_system.quests["chapter1_q2"].objectives[0]
        assert obj.current_count == 0


class TestMainQuestDefaults:
    def test_default_quests_created_when_yaml_missing(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        assert "prologue_01" in system.quests
        q = system.quests["prologue_01"]
        assert q.required_phase == "BEGINNING"
        assert q.next_quest_id == "awakening_01"
        assert q.rewards["gold"] == 100
        assert q.objectives[0].narrative_dag_id == "prologue_branching"

    def test_default_prologue_completes_via_visit_event(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        logs = system.update_progress(MockQuestPlayer(), "visit", "village_elder")
        assert any("★メインクエスト【運命の始まり】を完了した！" in line for line in logs)
        assert system.quests["prologue_01"].status is QuestStatus.COMPLETED


class TestMainQuestConditions:
    def test_objective_condition_tree_evaluation_completes(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        obj = QuestObjective("obj_cond", "条件達成", auto_evaluate=True)
        obj.condition_tree = FakeCondition(True)
        quest = MainQuest("cond_q", "条件クエスト", "説明", "BEGINNING", [obj])
        system.quests["cond_q"] = quest
        system.active_quest_id = "cond_q"

        logs = system.update_progress(MockQuestPlayer(), "kill", "anything")
        assert any("達成" in line for line in logs)
        assert obj.is_completed
        assert system.quests["cond_q"].status is QuestStatus.COMPLETED

    def test_objective_condition_tree_false_keeps_quest_active(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        obj = QuestObjective("obj_cond", "条件達成", auto_evaluate=True)
        obj.condition_tree = FakeCondition(False)
        quest = MainQuest("cond_q", "条件クエスト", "説明", "BEGINNING", [obj])
        quest.status = QuestStatus.ACTIVE
        system.quests["cond_q"] = quest
        system.active_quest_id = "cond_q"

        logs = system.update_progress(MockQuestPlayer(), "kill", "anything")
        assert logs == []
        assert not obj.is_completed
        assert system.quests["cond_q"].status is QuestStatus.ACTIVE

    def test_check_unlock_with_condition_override(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        quest = system.quests["prologue_01"]
        quest.unlock_condition = FakeCondition(True)
        assert quest.check_unlock(None) is True
        quest.unlock_condition = FakeCondition(False)
        assert quest.check_unlock(None) is False

    def test_check_unlock_falls_back_to_world_phase(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        quest = system.quests["prologue_01"]
        assert quest.check_unlock(None) is True  # BEGINNING フェーズ
        quest.required_phase = "CLIMAX"
        assert quest.check_unlock(None) is False


class TestQuestObjectiveSemantics:
    def test_update_counts_and_completes(self):
        obj = QuestObjective("o", "倒す", "kill", "slime", required_count=2)
        assert obj.update("slime") is True
        assert obj.current_count == 1
        assert not obj.is_completed
        assert obj.update("slime") is True
        assert obj.is_completed

    def test_update_wrong_target_returns_false(self):
        obj = QuestObjective("o", "倒す", "kill", "slime")
        assert obj.update("goblin") is False
        assert obj.current_count == 0

    def test_update_after_completion_is_noop(self):
        obj = QuestObjective("o", "倒す", "kill", "slime", required_count=1)
        obj.update("slime")
        assert obj.update("slime") is False
        assert obj.current_count == 1

    def test_serialization_roundtrip(self):
        obj = QuestObjective("o", "説明", "collect", "herb", required_count=4, current_count=2)
        restored = QuestObjective.from_dict(obj.to_dict())
        assert restored.objective_id == "o"
        assert restored.target_type == "collect"
        assert restored.required_count == 4
        assert restored.current_count == 2
        assert restored.condition_tree is None

    def test_build_condition_tree_skips_empty_dsl(self):
        obj = QuestObjective("o", "説明")
        obj.build_condition_tree()
        assert obj.condition_tree is None

    def test_main_quest_is_completed_requires_all_objectives(self):
        o1 = QuestObjective("o1", "a", "kill", "x")
        o2 = QuestObjective("o2", "b", "kill", "y")
        quest = MainQuest("q", "t", "d", "BEGINNING", [o1, o2])
        assert not quest.is_completed()
        o1.is_completed = True
        assert not quest.is_completed()
        o2.is_completed = True
        assert quest.is_completed()


class TestMainQuestNarrativeBridge:
    def test_narrative_state_helpers_safe_without_active_narrative(self, tmp_path):
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        player = MockPlayer("nobody")
        assert system.get_narrative_state(player) is None
        assert system.load_narrative_state(player, {"dag_id": "ghost", "current_node_id": "x"}) is False
        assert system.get_active_narrative_node(player) is None
        assert system.get_narrative_choices(player) == []

    def test_completion_starts_narrative_dag(self, tmp_path, monkeypatch):
        mock_executor = MagicMock()
        monkeypatch.setattr(narrative_executor, "NARRATIVE_EXECUTOR", mock_executor)
        data = {
            "main_quests": [
                {
                    "quest_id": "nq",
                    "title": "ナラティブクエスト",
                    "description": "d",
                    "required_phase": "BEGINNING",
                    "objectives": [
                        {
                            "objective_id": "o",
                            "description": "desc",
                            "target_type": "kill",
                            "target_id": "mob",
                        }
                    ],
                    "rewards": {},
                    "narrative_dag_id": "prologue_branching",
                }
            ]
        }
        path = tmp_path / "main_quests.yaml"
        write_yaml(path, data)
        system = MainQuestSystem(str(path))
        player = MockPlayer("story_seeker")
        engine = SimpleNamespace(survival=SimpleNamespace(gold=0))

        system.update_progress(player, "kill", "mob", 1, engine=engine)
        mock_executor.start_narrative.assert_called_once_with("prologue_branching", player)

    def test_make_narrative_choice_delegates_to_executor(self, tmp_path, monkeypatch):
        mock_executor = MagicMock()
        mock_executor.make_choice.return_value = ["選択した"]
        monkeypatch.setattr(narrative_executor, "NARRATIVE_EXECUTOR", mock_executor)
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        assert system.make_narrative_choice(MockPlayer("p"), "edge_1") == ["選択した"]


# ============================================================================
# quest_fragment_rewards.py - reward distribution
# ============================================================================


class TestFragmentDropTable:
    def make_table(self, **overrides) -> qfr.FragmentDropTable:
        params = dict(
            table_id="t1",
            quest_id="quest_1",
            drops=[
                qfr.FragmentDrop("frag_a", min_count=1, max_count=1, weight=100),
                qfr.FragmentDrop("frag_b", min_count=2, max_count=4, weight=100, required_flags=["cleared"]),
                qfr.FragmentDrop("frag_c", weight=100, forbidden_flags=["pacifist"]),
            ],
        )
        params.update(overrides)
        return qfr.FragmentDropTable(**params)

    def test_required_flags_exclude_drops(self, monkeypatch):
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.0, randint_value=1))
        table = self.make_table()
        assert table.drop_fragments(["cleared"]) == ["frag_a", "frag_b", "frag_c"]

    def test_missing_required_flag_excludes_drop(self, monkeypatch):
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.0, randint_value=1))
        table = self.make_table()
        result = table.drop_fragments([])
        assert result == ["frag_a", "frag_c"]

    def test_forbidden_flag_excludes_drop(self, monkeypatch):
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.0, randint_value=1))
        table = self.make_table()
        assert table.drop_fragments(["pacifist"]) == ["frag_a"]

    def test_weight_gating_between_drops(self, monkeypatch):
        table = qfr.FragmentDropTable(
            table_id="t",
            quest_id="q",
            drops=[
                qfr.FragmentDrop("frag_low", weight=1),
                qfr.FragmentDrop("frag_high", weight=1000),
            ],
        )
        # random()=0.5 → frag_low は落選 (0.5*1001 >= 1)、frag_high は当選
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.5, randint_value=1))
        assert table.drop_fragments([]) == ["frag_high"]

    def test_default_drop_used_when_pool_empty(self, monkeypatch):
        table = qfr.FragmentDropTable(
            table_id="t",
            quest_id="q",
            drops=[qfr.FragmentDrop("frag_rare", required_flags=["secret"])],
            default_drop=qfr.FragmentDrop("frag_default", weight=1000),
        )
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.0, randint_value=2))
        assert table.drop_fragments([]) == ["frag_default", "frag_default"]

    def test_no_pool_and_no_default_returns_empty(self):
        table = qfr.FragmentDropTable(
            table_id="t",
            quest_id="q",
            drops=[qfr.FragmentDrop("frag_rare", required_flags=["secret"])],
        )
        assert table.drop_fragments([]) == []

    def test_zero_total_weight_returns_empty(self):
        table = qfr.FragmentDropTable(
            table_id="t",
            quest_id="q",
            drops=[qfr.FragmentDrop("f", weight=0, required_flags=["s"])],
            default_drop=qfr.FragmentDrop("d", weight=0),
        )
        assert table.drop_fragments([]) == []

    def test_count_respects_min_max(self, monkeypatch):
        monkeypatch.setattr(qfr, "random", random.Random(42))
        table = qfr.FragmentDropTable(
            table_id="t",
            quest_id="q",
            drops=[qfr.FragmentDrop("frag_only", min_count=2, max_count=5, weight=1000)],
        )
        for _ in range(20):
            result = table.drop_fragments([])
            assert result
            assert all(f == "frag_only" for f in result)
            assert 2 <= len(result) <= 5


class TestFragmentRegistry:
    def test_register_and_get(self):
        table = qfr.FragmentDropTable(table_id="reg_t", quest_id="reg_q", drops=[])
        qfr.register_fragment_drop_table(table)
        assert qfr.get_fragment_drop_table("reg_t") is table
        assert qfr.get_fragment_drop_table("absent") is None

    def test_drop_fragments_for_quest(self, monkeypatch):
        table = qfr.FragmentDropTable(
            table_id="registry_quest",
            quest_id="registry_quest",
            drops=[qfr.FragmentDrop("frag_reg", weight=100)],
        )
        qfr.register_fragment_drop_table(table)
        monkeypatch.setattr(qfr, "random", PinnedRng(random_value=0.0, randint_value=1))
        assert qfr.drop_fragments_for_quest("registry_quest") == ["frag_reg"]
        assert qfr.drop_fragments_for_quest("unknown_quest") == []

    def test_load_tables_from_yaml(self, tmp_path, monkeypatch):
        data = {
            "fragment_drop_tables": {
                "yaml_table": {
                    "quest_id": "yaml_quest",
                    "drops": [
                        {
                            "fragment_id": "frag_yaml",
                            "min_count": 1,
                            "max_count": 3,
                            "weight": 40,
                            "required_flags": ["flag1"],
                            "forbidden_flags": ["flag2"],
                        }
                    ],
                }
            }
        }
        write_yaml(tmp_path / "data" / "fragment_drop_tables.yaml", data)
        monkeypatch.chdir(tmp_path)
        qfr.load_fragment_drop_tables_from_yaml()
        table = qfr.get_fragment_drop_table("yaml_table")
        assert table is not None
        assert table.quest_id == "yaml_quest"
        drop = table.drops[0]
        assert drop.fragment_id == "frag_yaml"
        assert drop.min_count == 1 and drop.max_count == 3
        assert drop.weight == 40
        assert drop.required_flags == ["flag1"]
        assert drop.forbidden_flags == ["flag2"]

    def test_load_tables_missing_file_is_noop(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        qfr.load_fragment_drop_tables_from_yaml()
        assert qfr.get_fragment_drop_table("anything") is None


# ============================================================================
# quest_dungeon_spec.py - spec generation
# ============================================================================


def build_spec_data() -> dict:
    return {
        "spec_id": "spec_001",
        "name": "封印の坑道",
        "description": "テスト用ダンジョン",
        "min_floors": 1,
        "max_floors": 2,
        "width": 40,
        "height": 40,
        "theme_id": "cave",
        "quest_id": "chapter1_q1",
        "objective_mapping": {"kill_slimes": "room_slime"},
        "global_constraints": {"no_random_boss": True},
        "floors": [
            {
                "floor_number": 1,
                "min_rooms": 2,
                "max_rooms": 5,
                "required_rooms": [
                    {
                        "room_id": "room_entrance",
                        "room_type": "ENTRANCE",
                        "traps": [
                            {
                                "trap_id": "trap_1",
                                "trap_type": "SPIKE",
                                "position": [2, 3],
                                "damage": 15,
                                "trigger_condition": "enter",
                                "disarm_difficulty": 8,
                            }
                        ],
                        "enemies": [
                            {
                                "enemy_id": "enemy_1",
                                "monster_id": "slime",
                                "role": "GUARD",
                                "position": [4, 4],
                                "level_modifier": 1,
                                "ai_hints": ["guard_entrance"],
                                "spawn_condition": "always",
                            }
                        ],
                        "items": [{"item_id": "potion"}],
                    },
                    {
                        "room_id": "room_treasure",
                        "room_type": "TREASURE",
                        "is_locked": True,
                        "lock_key_id": "key_1",
                        "required_connections": ["room_entrance"],
                    },
                ],
                "optional_rooms": [
                    {"room_id": "room_secret", "room_type": "SECRET", "is_required": False}
                ],
            },
            {
                "floor_number": 2,
                "boss_room": {
                    "room_id": "room_boss",
                    "room_type": "BOSS",
                    "enemies": [
                        {"enemy_id": "boss_1", "monster_id": "boss_lord", "role": "BOSS"}
                    ],
                },
            },
        ],
    }


class TestDungeonSpecGeneration:
    def test_full_spec_from_yaml(self):
        spec = qds.build_dungeon_spec_from_yaml(build_spec_data())
        assert spec.spec_id == "spec_001"
        assert spec.name == "封印の坑道"
        assert spec.quest_id == "chapter1_q1"
        assert spec.objective_mapping == {"kill_slimes": "room_slime"}
        assert spec.global_constraints == {"no_random_boss": True}
        assert spec.min_floors == 1 and spec.max_floors == 2
        assert spec.theme_id == "cave"

        f1, f2 = spec.floor_specs
        assert f1.floor_number == 1
        assert f1.min_rooms == 2 and f1.max_rooms == 5
        assert [r.room_id for r in f1.required_rooms] == ["room_entrance", "room_treasure"]

        entrance = f1.required_rooms[0]
        assert entrance.room_type is qds.RoomType.ENTRANCE
        trap = entrance.traps[0]
        assert trap.trap_type is qds.TrapType.SPIKE
        assert trap.position == (2, 3)
        assert trap.damage == 15
        assert trap.trigger_condition == "enter"
        assert trap.disarm_difficulty == 8
        enemy = entrance.enemies[0]
        assert enemy.monster_id == "slime"
        assert enemy.role is qds.EnemyRole.GUARD
        assert enemy.position == (4, 4)
        assert enemy.level_modifier == 1
        assert enemy.ai_hints == ["guard_entrance"]
        assert enemy.spawn_condition == "always"
        assert entrance.items == [{"item_id": "potion"}]

        treasure = f1.required_rooms[1]
        assert treasure.room_type is qds.RoomType.TREASURE
        assert treasure.is_locked is True
        assert treasure.lock_key_id == "key_1"
        assert treasure.required_connections == ["room_entrance"]

        assert [r.room_id for r in f1.optional_rooms] == ["room_secret"]
        assert f1.optional_rooms[0].is_required is False

        # boss_room 指定で is_boss_floor が強制有効化される
        assert f2.is_boss_floor is True
        assert f2.boss_room_spec is not None
        assert f2.boss_room_spec.room_id == "room_boss"
        assert f2.boss_room_spec.room_type is qds.RoomType.BOSS
        assert f2.boss_room_spec.enemies[0].role is qds.EnemyRole.BOSS

    def test_unknown_enum_values_fall_back_to_defaults(self):
        data = {
            "spec_id": "s",
            "floors": [
                {
                    "floor_number": 1,
                    "required_rooms": [
                        {
                            "room_id": "r1",
                            "room_type": "WEIRD",
                            "traps": [{"trap_id": "t1", "trap_type": "NOPE"}],
                            "enemies": [{"enemy_id": "e1", "monster_id": "m", "role": "STRANGE"}],
                        }
                    ],
                }
            ],
        }
        spec = qds.build_dungeon_spec_from_yaml(data)
        room = spec.floor_specs[0].required_rooms[0]
        assert room.room_type is qds.RoomType.CHAMBER
        assert room.traps[0].trap_type is qds.TrapType.SPIKE
        assert room.enemies[0].role is qds.EnemyRole.GUARD

    def test_spec_dataclass_defaults(self):
        room = qds.RoomSpec(room_id="r", room_type=qds.RoomType.CHAMBER)
        assert room.is_required is True and room.is_locked is False
        trap = qds.TrapSpec(trap_id="t", trap_type=qds.TrapType.SPIKE)
        assert trap.damage == 10 and trap.trigger_condition == "enter"
        enemy = qds.EnemySpec(enemy_id="e", monster_id="slime")
        assert enemy.role is qds.EnemyRole.GUARD and enemy.spawn_condition == "always"
        dungeon = qds.DungeonSpec(spec_id="d")
        assert dungeon.min_floors == 1 and dungeon.max_floors == 5
        assert dungeon.width == 60 and dungeon.height == 60
        floor = qds.FloorSpec()
        assert floor.min_rooms == 3 and floor.max_rooms == 8
        assert floor.entrance_from_above is True and floor.exit_to_below is True

    def test_room_trap_enemy_enums_exist(self):
        assert qds.RoomType.BOSS.name == "BOSS"
        assert {t.name for t in qds.TrapType} >= {"SPIKE", "POISON_GAS", "TELEPORT"}
        assert {r.name for r in qds.EnemyRole} >= {"GUARD", "BOSS", "ELITE", "MINIBOSS"}


class TestDungeonVerification:
    def make_spec(self) -> qds.DungeonSpec:
        return qds.build_dungeon_spec_from_yaml(build_spec_data())

    def test_satisfied_generation_passes(self):
        spec = self.make_spec()
        generated = {
            "floors": [
                {"rooms": [{"room_id": "room_entrance"}, {"room_id": "room_treasure"}]},
                {"rooms": [{"room_id": "room_boss"}]},
            ]
        }
        result = qds.verify_dungeon_against_spec(generated, spec)
        assert result.spec_id == "spec_001"
        assert result.satisfied is True
        assert result.missing_required_rooms == []
        assert result.boss_room_missing is False
        assert result.floor_count_mismatch is False

    def test_missing_required_room_detected(self):
        spec = self.make_spec()
        generated = {
            "floors": [
                {"rooms": [{"room_id": "room_entrance"}]},
                {"rooms": [{"room_id": "room_boss"}]},
            ]
        }
        result = qds.verify_dungeon_against_spec(generated, spec)
        assert result.satisfied is False
        assert "room_treasure" in result.missing_required_rooms

    def test_boss_room_missing_detected(self):
        spec = self.make_spec()
        generated = {
            "floors": [
                {"rooms": [{"room_id": "room_entrance"}, {"room_id": "room_treasure"}]},
                {"rooms": []},
            ]
        }
        result = qds.verify_dungeon_against_spec(generated, spec)
        assert result.satisfied is False
        assert result.boss_room_missing is True

    def test_floor_count_mismatch_detected(self):
        spec = self.make_spec()
        result = qds.verify_dungeon_against_spec({"floors": []}, spec)
        assert result.satisfied is False
        assert result.floor_count_mismatch is True
        assert result.details["floor_count"]["actual"] == 0
        assert result.details["floor_count"]["expected_min"] == 1
        assert result.details["floor_count"]["expected_max"] == 2

    def test_out_of_range_floor_index_is_skipped(self):
        data = build_spec_data()
        data["floors"].append(
            {"floor_number": 3, "required_rooms": [{"room_id": "room_x", "room_type": "CHAMBER"}]}
        )
        spec = qds.build_dungeon_spec_from_yaml(data)
        generated = {
            "floors": [
                {"rooms": [{"room_id": "room_entrance"}, {"room_id": "room_treasure"}]},
                {"rooms": [{"room_id": "room_boss"}]},
            ]
        }
        result = qds.verify_dungeon_against_spec(generated, spec)
        # フロア3は生成されていないため必須部屋チェックはスキップされる
        assert result.missing_required_rooms == []
