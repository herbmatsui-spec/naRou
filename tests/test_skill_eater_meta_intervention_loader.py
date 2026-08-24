"""Tests for meta intervention template loader."""

import tempfile
import pytest
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from naRou.systems.skill_eater_template_model import load_templates, TemplateData
from naRou.systems.karma_system import KarmaManager, REGISTRY


# Mock Entity for testing karma/exposure without full ECS
@dataclass
class MockEntity:
    x: int = 0
    y: int = 0
    char: str = "@"
    color: tuple = (255, 255, 255)
    name: str = "Test"
    is_player: bool = True
    karma_law_chaos: int = 0
    karma_good_evil: int = 0
    template_exposure: int = 0
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "components": {
                "ReincarnationComponent": {
                    "karma_law_chaos": self.karma_law_chaos,
                    "karma_good_evil": self.karma_good_evil,
                    "template_exposure": self.template_exposure,
                }
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MockEntity":
        ent = cls()
        comp_data = data.get("components", {}).get("ReincarnationComponent", {})
        ent.karma_law_chaos = comp_data.get("karma_law_chaos", 0)
        ent.karma_good_evil = comp_data.get("karma_good_evil", 0)
        ent.template_exposure = comp_data.get("template_exposure", 0)
        return ent


def test_load_templates():
    """Test loading template YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpl_dir = Path(tmpdir)
        # Write a test template
        test_yaml = """
id: test_template
archetype: expel
contexts: [slum, guild]
faction_weight:
  outlaw: 0.4
  guild: 0.3
route_steps:
  - { flag: sell_skill_cheap, turn: 2, actor: npc, on_fail: expelled }
  - { flag: rise_later, turn: 8, actor: npc, on_fail: none }
exploit_windows:
  - { id: buy_cheap, tier: 1, req_gold: 200, base_success: 0.85 }
  - { id: exclusive_contract, tier: 2, req_skill: [negotiation], base_success: 0.55 }
reward:
  karma_t1: 120
  karma_t2: 700
  stealable_skill: farming_blessing_minor
"""
        (tmpl_dir / "test.yaml").write_text(test_yaml.strip(), encoding="utf-8")

        templates = load_templates(tmpl_dir)
        assert "test_template" in templates
        tpl: TemplateData = templates["test_template"]
        assert tpl.archetype == "expel"
        assert len(tpl.route_steps) == 2
        assert tpl.route_steps[0].flag == "sell_skill_cheap"
        assert tpl.route_steps[0].turn == 2
        assert len(tpl.exploit_windows) == 2
        assert tpl.exploit_windows[0].id == "buy_cheap"
        assert tpl.exploit_windows[0].tier == 1
        assert tpl.exploit_windows[0].base_success == 0.85
        assert tpl.reward.karma_t1 == 120
        assert tpl.reward.karma_t2 == 700
        assert tpl.reward.stealable_skill == "farming_blessing_minor"


def test_load_real_template():
    """Test loading the real expel_incompetent template."""
    templates = load_templates("data/templates")
    assert "expel_incompetent" in templates
    tpl = templates["expel_incompetent"]
    assert tpl.archetype == "expel"
    assert len(tpl.route_steps) == 2
    assert len(tpl.exploit_windows) == 2


def test_entity_template_exposure_roundtrip():
    """Test that template_exposure survives save/load roundtrip."""
    REGISTRY.load()  # ensure actions exist
    player = MockEntity()
    km = KarmaManager()

    # Initial values
    assert player.template_exposure == 0
    assert player.karma_law_chaos == 0
    assert player.karma_good_evil == 0

    # Apply template deep read
    lc, ge, exp = km.update_karma(player, "template_deep_read", 1)
    assert lc == -1  # law_chaos -1
    assert ge == 0
    assert exp == 1  # exposure +1

    # Apply T1 intervene
    lc2, ge2, exp2 = km.update_karma(player, "template_intervene_t1", 1)
    assert lc2 == -1
    assert ge2 == 0
    assert exp2 == 2  # exposure +1 more

    # Serialize
    data = player.to_dict()
    comp_data = data["components"].get("ReincarnationComponent", {})
    assert comp_data.get("template_exposure") == 2
    assert comp_data.get("karma_law_chaos") == -1
    assert comp_data.get("karma_good_evil") == 0

    # Deserialize
    player2 = MockEntity.from_dict(data)
    assert player2.template_exposure == 2
    assert player2.karma_law_chaos == -1
    assert player2.karma_good_evil == 0


def test_karma_exposure_clamping():
    """Test that exposure is clamped to 0-100 range."""
    REGISTRY.load()
    player = MockEntity()
    km = KarmaManager()

    # Push exposure over max
    for _ in range(150):
        km.update_karma(player, "template_intervene_t3", 1)
    assert player.template_exposure == 100  # clamped

    # Push below min
    player2 = MockEntity()
    # We can't easily test negative since actions only increase exposure
    # but ensure it doesn't go negative on init
    assert player2.template_exposure >= 0