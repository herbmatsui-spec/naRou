"""
Test Module for Narrative DAG (Phase 4 Step 13)
"""

from __future__ import annotations

import pytest

from quest_narrative_dag import (
    NarrativeContext,
    NarrativeDAG,
    NarrativeEdge,
    NarrativeEdgeType,
    NarrativeNode,
    NarrativeNodeType,
    build_dag_from_yaml,
)


def test_narrative_node_creation():
    node = NarrativeNode(
        node_id="test_node",
        node_type=NarrativeNodeType.CHOICE,
        title="Test Choice",
        description="Description",
        set_flags=["flag1"],
    )
    assert node.node_id == "test_node"
    assert node.node_type == NarrativeNodeType.CHOICE
    assert "flag1" in node.set_flags


def test_narrative_edge_creation():
    edge = NarrativeEdge(
        edge_id="test_edge",
        source_node_id="node1",
        target_node_id="node2",
        edge_type=NarrativeEdgeType.CHOICE,
        choice_text="Choice Text",
    )
    assert edge.edge_id == "test_edge"
    assert edge.edge_type == NarrativeEdgeType.CHOICE
    assert edge.choice_text == "Choice Text"


def test_narrative_edge_availability():
    edge = NarrativeEdge(
        edge_id="test_edge",
        source_node_id="node1",
        target_node_id="node2",
        edge_type=NarrativeEdgeType.CHOICE,
        required_flags=["has_key"],
        forbidden_flags=["cursed"],
    )

    ctx = NarrativeContext(flags={"has_key"})
    assert edge.is_available(ctx) is True

    ctx = NarrativeContext(flags={"has_key", "cursed"})
    assert edge.is_available(ctx) is False


def test_narrative_dag_build_and_validate():
    dag = NarrativeDAG("test_dag")

    start = NarrativeNode("start", NarrativeNodeType.START, title="Start")
    choice = NarrativeNode("choice", NarrativeNodeType.CHOICE, title="Choice")
    end1 = NarrativeNode("end1", NarrativeNodeType.END, title="End1")

    dag.add_node(start)
    dag.add_node(choice)
    dag.add_node(end1)

    start.add_edge(NarrativeEdge("e1", "start", "choice", NarrativeEdgeType.AUTO))
    choice.add_edge(NarrativeEdge("e2", "choice", "end1", NarrativeEdgeType.CHOICE, choice_text="Proceed"))

    errors = dag.validate()
    assert len(errors) == 0
    assert dag.get_start_node().node_id == "start"
    assert len(dag.get_end_nodes()) == 1
