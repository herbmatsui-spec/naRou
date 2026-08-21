from __future__ import annotations

import pytest

from skill_fusion_system import FusionManager, FusionRegistry


@pytest.fixture
def registry(tmp_path):
    # create temporary yaml file
    yaml_path = tmp_path / "skill_fusion.yaml"
    yaml_path.write_text("""
    fusions:
      test_fusion:
        name: Test Fusion
        description: Test description
        required_skills: []
        result_skills: []
        bonus_effects: []
    """)
    reg = FusionRegistry()
    reg.load(str(yaml_path))
    return reg


class DummyPlayer:
    def __init__(self):
        self.skill_tree_progress = {}
        self.job = None
        self.god_id = ""
        self.fused_skills = []


def test_load_and_get(registry):
    assert "test_fusion" in registry.all()
    data = registry.get("test_fusion")
    assert data.name == "Test Fusion"


def test_perform_fusion_success(registry):
    manager = FusionManager(registry)
    player = DummyPlayer()
    success = manager.perform_fusion(player, "test_fusion")
    assert success
    assert "test_fusion" in player.fused_skills


def test_perform_fusion_duplicate(registry):
    manager = FusionManager(registry)
    player = DummyPlayer()
    manager.perform_fusion(player, "test_fusion")
    # second attempt should fail
    assert not manager.perform_fusion(player, "test_fusion")
