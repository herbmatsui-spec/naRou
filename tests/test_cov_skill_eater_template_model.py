"""Coverage tests for skill_eater_template_model (TemplateData model + YAML loader)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from skill_eater_template_model import (
    ExploitWindow,
    RouteStep,
    TemplateData,
    TemplateReward,
    load_templates,
)


def _write_yaml(tmp_path: Path, name: str, data: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


class TestRouteStep:
    def test_instantiation(self) -> None:
        rs = RouteStep(flag="enter_slum", turn=3, actor="broker", on_fail="alert")
        assert rs.flag == "enter_slum"
        assert rs.turn == 3
        assert rs.actor == "broker"
        assert rs.on_fail == "alert"


class TestExploitWindow:
    def test_defaults(self) -> None:
        ew = ExploitWindow(id="w1", tier=1)
        assert ew.id == "w1"
        assert ew.tier == 1
        assert ew.req_gold == 0
        assert ew.req_skill == []
        assert ew.base_success == 0.5

    def test_full(self) -> None:
        ew = ExploitWindow(id="w2", tier=2, req_gold=500, req_skill=["analysis"], base_success=0.8)
        assert ew.req_gold == 500
        assert ew.req_skill == ["analysis"]
        assert ew.base_success == 0.8


class TestTemplateReward:
    def test_defaults(self) -> None:
        r = TemplateReward()
        assert r.karma_t1 == 0
        assert r.karma_t2 == 0
        assert r.stealable_skill == ""

    def test_full(self) -> None:
        r = TemplateReward(karma_t1=100, karma_t2=300, stealable_skill="rare_skill_01")
        assert r.karma_t1 == 100
        assert r.karma_t2 == 300
        assert r.stealable_skill == "rare_skill_01"


class TestTemplateData:
    def test_instantiation(self) -> None:
        td = TemplateData(
            id="tpl_01",
            archetype="expel",
            contexts=["slum", "guild"],
            faction_weight={"outlaw": 0.4},
            route_steps=[RouteStep(flag="a", turn=1, actor="x", on_fail="b")],
            exploit_windows=[ExploitWindow(id="w1", tier=1, base_success=0.5)],
            reward=TemplateReward(karma_t1=50, stealable_skill="s1"),
        )
        assert td.id == "tpl_01"
        assert td.archetype == "expel"
        assert "slum" in td.contexts
        assert len(td.route_steps) == 1
        assert len(td.exploit_windows) == 1
        assert td.reward.karma_t1 == 50

    def test_from_dict(self) -> None:
        data = {
            "id": "tpl_02",
            "archetype": "betray",
            "contexts": ["guild"],
            "faction_weight": {"guild": 0.5},
            "route_steps": [{"flag": "f", "turn": 2, "actor": "y", "on_fail": "c"}],
            "exploit_windows": [{"id": "w2", "tier": 3, "req_gold": 100}],
            "reward": {"karma_t2": 200},
        }
        td = TemplateData.from_dict(data)
        assert td.id == "tpl_02"
        assert td.archetype == "betray"
        assert td.contexts == ["guild"]
        assert td.faction_weight == {"guild": 0.5}
        assert len(td.route_steps) == 1
        assert td.route_steps[0].turn == 2
        assert len(td.exploit_windows) == 1
        assert td.exploit_windows[0].tier == 3
        assert td.exploit_windows[0].req_gold == 100
        assert td.reward.karma_t2 == 200

    def test_from_dict_minimal(self) -> None:
        td = TemplateData.from_dict({"id": "tpl_min", "archetype": "expel", "contexts": ["slum"]})
        assert td.id == "tpl_min"
        assert td.route_steps == []
        assert td.exploit_windows == []
        assert td.reward == TemplateReward()


class TestLoadTemplates:
    def test_load_directory(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path, "tpl_a.yaml", {
            "id": "tpl_a",
            "archetype": "expel",
            "contexts": ["slum"],
            "faction_weight": {},
            "route_steps": [],
            "exploit_windows": [],
            "reward": {},
        })
        _write_yaml(tmp_path, "tpl_b.yaml", {
            "id": "tpl_b",
            "archetype": "betray",
            "contexts": ["guild"],
            "faction_weight": {},
            "route_steps": [],
            "exploit_windows": [],
            "reward": {},
        })
        templates = load_templates(tmp_path)
        assert set(templates.keys()) == {"tpl_a", "tpl_b"}
        assert templates["tpl_a"].archetype == "expel"
        assert templates["tpl_b"].archetype == "betray"

    def test_load_empty_directory(self, tmp_path: Path) -> None:
        templates = load_templates(tmp_path)
        assert templates == {}

    def test_load_nonexistent_directory(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_templates(Path("/nonexistent/templates_dir"))

    def test_load_skips_non_yaml(self, tmp_path: Path) -> None:
        (tmp_path / "not_template.txt").write_text("hello", encoding="utf-8")
        templates = load_templates(tmp_path)
        assert templates == {}
