"""
Phase 4 テスト: ナラティブ分岐 DAG (Steps 13-17)
"""

from __future__ import annotations

import pytest

from narrative_executor import NarrativeExecutor, NarrativeState
from quest_narrative_dag import (
    NarrativeContext,
    NarrativeDAG,
    NarrativeEdge,
    NarrativeEdgeType,
    NarrativeNode,
    NarrativeNodeType,
    build_dag_from_yaml,
)

# ---------------------------------------------------------------------------
# Step 13: NarrativeNode/Edge DAG definition
# ---------------------------------------------------------------------------


def test_narrative_node_creation():
    """NarrativeNode 基本作成"""
    node = NarrativeNode(
        node_id="test_node",
        node_type=NarrativeNodeType.CHOICE,
        title="テスト選択",
        description="説明",
        set_flags=["flag1"],
        clear_flags=["old_flag"],
    )
    assert node.node_id == "test_node"
    assert node.node_type == NarrativeNodeType.CHOICE
    assert "flag1" in node.set_flags
    assert "old_flag" in node.clear_flags


def test_narrative_edge_creation():
    """NarrativeEdge 基本作成"""
    edge = NarrativeEdge(
        edge_id="test_edge",
        source_node_id="node1",
        target_node_id="node2",
        edge_type=NarrativeEdgeType.CHOICE,
        choice_text="選択肢テキスト",
        condition_dsl="(has flags.flag1)",
    )
    assert edge.edge_id == "test_edge"
    assert edge.edge_type == NarrativeEdgeType.CHOICE
    assert edge.choice_text == "選択肢テキスト"


def test_narrative_edge_availability():
    """エッジ利用可能判定"""
    edge = NarrativeEdge(
        edge_id="test_edge",
        source_node_id="node1",
        target_node_id="node2",
        edge_type=NarrativeEdgeType.CHOICE,
        required_flags=["has_sword"],
        forbidden_flags=["cursed"],
    )

    ctx = NarrativeContext(flags={"has_sword"})
    assert edge.is_available(ctx) is True

    ctx = NarrativeContext(flags={"has_sword", "cursed"})
    assert edge.is_available(ctx) is False

    ctx = NarrativeContext(flags={})
    assert edge.is_available(ctx) is False


def test_narrative_dag_build_and_validate():
    """DAG 構築と検証"""
    dag = NarrativeDAG("test_dag")

    # ノード追加
    start = NarrativeNode("start", NarrativeNodeType.START, title="開始")
    choice = NarrativeNode("choice", NarrativeNodeType.CHOICE, title="選択")
    end1 = NarrativeNode("end1", NarrativeNodeType.END, title="エンディング1")
    end2 = NarrativeNode("end2", NarrativeNodeType.END, title="エンディング2")

    dag.add_node(start)
    dag.add_node(choice)
    dag.add_node(end1)
    dag.add_node(end2)

    # エッジ追加
    e1 = NarrativeEdge("e1", "start", "choice", NarrativeEdgeType.AUTO)
    e2 = NarrativeEdge("e2", "choice", "end1", NarrativeEdgeType.CHOICE, choice_text="道A")
    e3 = NarrativeEdge("e3", "choice", "end2", NarrativeEdgeType.CHOICE, choice_text="道B")

    start.add_edge(e1)
    choice.add_edge(e2)
    choice.add_edge(e3)

    errors = dag.validate()
    assert len(errors) == 0
    assert dag.get_start_node().node_id == "start"
    assert len(dag.get_end_nodes()) == 2


def test_narrative_dag_cycle_detection():
    """サイクル検出"""
    dag = NarrativeDAG("cycle_dag")

    a = NarrativeNode("a", NarrativeNodeType.START)
    b = NarrativeNode("b", NarrativeNodeType.EVENT)
    c = NarrativeNode("c", NarrativeNodeType.END)

    dag.add_node(a)
    dag.add_node(b)
    dag.add_node(c)

    a.add_edge(NarrativeEdge("e1", "a", "b", NarrativeEdgeType.AUTO))
    b.add_edge(NarrativeEdge("e2", "b", "c", NarrativeEdgeType.AUTO))
    c.add_edge(NarrativeEdge("e3", "c", "a", NarrativeEdgeType.AUTO))  # サイクル

    errors = dag.validate()
    assert any("サイクル" in e for e in errors)


def test_narrative_dag_unreachable_node():
    """到達不能ノード検出"""
    dag = NarrativeDAG("unreach_dag")

    start = NarrativeNode("start", NarrativeNodeType.START)
    end = NarrativeNode("end", NarrativeNodeType.END)
    isolated = NarrativeNode("isolated", NarrativeNodeType.EVENT)

    dag.add_node(start)
    dag.add_node(end)
    dag.add_node(isolated)

    start.add_edge(NarrativeEdge("e1", "start", "end", NarrativeEdgeType.AUTO))
    # isolated へのエッジなし

    errors = dag.validate()
    assert any("到達不能" in e for e in errors)


def test_build_dag_from_yaml():
    """YAML から DAG 構築"""
    yaml_data = {
        "nodes": {
            "start": {"type": "START", "title": "開始"},
            "choice": {"type": "CHOICE", "title": "選択", "set_flags": ["chose"]},
            "end": {"type": "END", "title": "終了"},
        },
        "edges": [
            {"edge_id": "e1", "source": "start", "target": "choice", "type": "AUTO"},
            {
                "edge_id": "e2",
                "source": "choice",
                "target": "end",
                "type": "CHOICE",
                "choice_text": "終わる",
            },
        ],
    }
    dag = build_dag_from_yaml("test_yaml", yaml_data)

    assert dag.dag_id == "test_yaml"
    assert dag.get_start_node().node_id == "start"
    assert len(dag.get_end_nodes()) == 1
    assert len(dag.get_node("choice").outgoing_edges) == 1


# ---------------------------------------------------------------------------
# Step 14-15: NarrativeExecutor 基本動作
# ---------------------------------------------------------------------------


class MockEntity:
    def __init__(self, name="player"):
        self.name = name


def test_narrative_executor_start():
    """ナラティブ開始"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player")

    state = executor.start_narrative("prologue_branching", player)

    assert state is not None
    assert state.dag_id == "prologue_branching"
    assert state.current_node_id in [
        "prologue_start",
        "prologue_accept",
        "prologue_decline",
    ]
    assert not state.completed


def test_narrative_executor_choices():
    """選択肢取得"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player2")

    executor.start_narrative("prologue_branching", player)
    choices = executor.get_available_choices(player)

    # prologue_start は AUTO 遷移で choice ノードへ進む
    # もし choice ノードに到達していれば選択肢があるはず
    assert isinstance(choices, list)


def test_narrative_executor_make_choice():
    """選択肢実行"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player3")

    executor.start_narrative("prologue_branching", player)

    # 選択肢があるノードまで自動遷移するか、手動で選択可能な状態にする
    choices = executor.get_available_choices(player)
    if choices:
        edge_id = choices[0].edge_id
        logs = executor.make_choice(player, edge_id)
        assert isinstance(logs, list)
        assert len(logs) > 0


def test_narrative_state_serialization():
    """状態シリアライズ/デシリアライズ"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player4")

    state = executor.start_narrative("prologue_branching", player)
    assert state is not None

    # シリアライズ
    data = state.to_dict()
    assert data["dag_id"] == "prologue_branching"
    assert "flags" in data
    assert "history" in data

    # デシリアライズ
    loaded = NarrativeState.from_dict(data)
    assert loaded.dag_id == state.dag_id
    assert loaded.current_node_id == state.current_node_id
    assert loaded.flags == state.flags


def test_narrative_save_load_state():
    """セーブ/ロード統合"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    player = MockEntity("test_player5")

    state = executor.start_narrative("prologue_branching", player)
    assert state is not None

    # セーブ
    data = executor.save_state(player)
    assert data is not None

    # 新しい実行インスタンスでロード
    executor2 = NarrativeExecutor("data/quest_narratives.yaml")
    loaded = executor2.load_state(player, data)
    assert loaded is True

    loaded_state = executor2.get_active_state(player)
    assert loaded_state is not None
    assert loaded_state.dag_id == state.dag_id


# ---------------------------------------------------------------------------
# Step 16: story_choices.yaml / story_endings.yaml 連携
# ---------------------------------------------------------------------------


def test_story_choices_loading():
    """story_choices.yaml 読み込み"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")

    choice = executor.get_choice("farm_survivor_saved")
    assert choice is not None
    assert choice.id == "farm_survivor_saved"
    assert "gain_gold" in [e["type"] for e in choice.immediate_effects]


def test_story_endings_loading():
    """story_endings.yaml 読み込み"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")

    ending = executor.get_ending("goblin_peace_bringer")
    assert ending is not None
    assert ending.id == "goblin_peace_bringer"
    assert "peace_envoy" in ending.rewards.get("title", "")


def test_apply_choice_consequence():
    """選択肢結果適用"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    context = NarrativeContext(flags=set(), variables={})

    logs = executor.apply_choice_consequence("farm_survivor_saved", context)

    assert isinstance(logs, list)
    assert len(logs) > 0
    assert context.variables.get("gold", 0) > 0
    assert context.variables.get("karma", 0) > 0


def test_ending_unlock_check():
    """エンディング解放条件チェック"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    context = NarrativeContext(
        flags={"spared_cubs_resolved", "karma_good_50"}, variables={"karma": 60}
    )

    # 条件を満たす
    assert executor.check_ending_unlock("goblin_peace_bringer", context) is True

    # 条件を満たさない
    context2 = NarrativeContext(flags=set(), variables={"karma": 0})
    assert executor.check_ending_unlock("goblin_peace_bringer", context2) is False


def test_grant_ending_rewards():
    """エンディング報酬付与"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    context = NarrativeContext(flags=set(), variables={})

    logs = executor.grant_ending_rewards("goblin_peace_bringer", context)

    assert isinstance(logs, list)
    assert context.variables.get("title") == "peace_envoy"
    assert context.variables.get("gold", 0) == 50000


def test_get_available_endings():
    """解放可能エンディング一覧"""
    executor = NarrativeExecutor("data/quest_narratives.yaml")
    context = NarrativeContext(
        flags={"spared_cubs_resolved", "karma_good_50"}, variables={"karma": 60}
    )

    available = executor.get_available_endings(context)
    assert isinstance(available, list)
    assert any(e.id == "goblin_peace_bringer" for e in available)


# ---------------------------------------------------------------------------
# Step 17: main_quest_system.py 連携
# ---------------------------------------------------------------------------


def test_quest_objective_narrative_dag_id():
    """QuestObjective に narrative_dag_id フィールド"""
    from main_quest_system import QuestObjective

    obj = QuestObjective(
        objective_id="test",
        description="テスト",
        target_type="visit",
        target_id="npc1",
        narrative_dag_id="test_dag",
    )

    assert obj.narrative_dag_id == "test_dag"
    assert obj.narrative_started is False


def test_main_quest_narrative_dag_id():
    """MainQuest に narrative_dag_id フィールド"""
    from main_quest_system import MainQuest, QuestObjective

    quest = MainQuest(
        quest_id="test_quest",
        title="テストクエスト",
        description="説明",
        required_phase="BEGINNING",
        objectives=[QuestObjective("obj1", "目的", "visit", "npc1")],
        narrative_dag_id="test_narrative",
    )

    assert quest.narrative_dag_id == "test_narrative"


def test_main_quest_system_narrative_methods():
    """MainQuestSystem ナラティブ連携メソッド存在確認"""
    from main_quest_system import MainQuestSystem

    mqs = MainQuestSystem()

    # メソッド存在確認
    assert hasattr(mqs, "_start_quest_narrative")
    assert hasattr(mqs, "make_narrative_choice")
    assert hasattr(mqs, "get_active_narrative_node")
    assert hasattr(mqs, "get_narrative_choices")
    assert hasattr(mqs, "get_available_endings")
    assert hasattr(mqs, "get_narrative_state")
    assert hasattr(mqs, "load_narrative_state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
