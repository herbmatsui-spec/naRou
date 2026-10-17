"""Coverage tests for skill_eater_husk_ui (Husk Puppet UI functions)."""

from __future__ import annotations

from naRou.ecs.components.components import HuskComponent, HuskInventoryComponent

from skill_eater_husk_ui import (
    dispatch,
    forge_status,
    list_husks,
    list_injectable_skills,
    open_forge_ui,
    ui_inject,
)

from skill_eater_husk_forge import PuppetForgeSystem


class _Player:
    def __init__(self, husks=None, location="base"):
        self.husk_inventory = None
        if husks is not None:
            self.husk_inventory = HuskInventoryComponent(husks=list(husks))
        self.units = []


class TestOpenForgeUI:
    def test_returns_forge_menu(self) -> None:
        assert open_forge_ui(_Player()) == "forge_menu"


class TestListHusks:
    def test_no_inventory(self) -> None:
        player = _Player()
        player.husk_inventory = None
        assert list_husks(player) == []

    def test_no_attribute(self) -> None:
        player = MagicMock()
        del player.husk_inventory
        assert list_husks(player) == []

    def test_lists_husks(self) -> None:
        husks = [
            HuskComponent(husk_id="h1", source_monster="goblin", tier=1),
            HuskComponent(husk_id="h2", source_monster="orc", tier=3),
        ]
        player = _Player(husks=husks)
        result = list_husks(player)
        assert result == ["h1(goblin)", "h2(orc)"]


class TestListInjectableSkills:
    def test_default_when_config_none(self) -> None:
        with patch_config("husk.injectable_skills", None):
            assert list_injectable_skills(_Player()) == ["fire_bolt", "guard", "dash"]

    def test_uses_config_when_present(self) -> None:
        with patch_config("husk.injectable_skills", ["ice_shard", "heal"]):
            assert list_injectable_skills(_Player()) == ["ice_shard", "heal"]


def patch_config(key, value):
    from unittest.mock import patch

    return patch("skill_eater_husk_ui.get_config", return_value=value)


class TestUiInject:
    def test_no_inventory(self) -> None:
        player = _Player()
        player.husk_inventory = None
        ui_inject(player, "h1", "fire_bolt")  # should not raise

    def test_husk_not_found(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1)
        player = _Player(husks=[husk])
        ui_inject(player, "h2", "fire_bolt")  # should not raise

    def test_slot_full_swallowed(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1, slots=1)
        husk.injected_skills = ["fire_bolt"]
        player = _Player(husks=[husk])
        ui_inject(player, "h1", "ice_shard")  # ValueError swallowed by UI
        assert husk.injected_skills == ["fire_bolt"]

    def test_normal_injection(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1, slots=2)
        player = _Player(husks=[husk])
        ui_inject(player, "h1", "fire_bolt")
        assert husk.injected_skills == ["fire_bolt"]


class TestForgeStatus:
    def test_format(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1, slots=2)
        husk.injected_skills = ["fire_bolt"]
        status = forge_status(husk)
        assert status.startswith("load=")
        assert "risk=" in status
        assert status == f"load=10 risk=0.10"  # 1*10 + 0*5 = 10; risk=(10-0)/100=0.1


class TestDispatch:
    def test_invalid_role_raises(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1)
        player = _Player(husks=[husk])
        try:
            dispatch(player, "h1", "bogus")
        except ValueError as exc:
            assert "Invalid role" in str(exc)
            return
        raise AssertionError("expected ValueError")

    def test_husk_not_found_no_unit(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1)
        player = _Player(husks=[husk])
        dispatch(player, "h2", "escort")
        assert player.units == []

    def test_normal_dispatch_adds_unit(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1, slots=2)
        player = _Player(husks=[husk])
        dispatch(player, "h1", "escort")
        assert len(player.units) == 1
        unit = player.units[0]
        assert unit.husk_ref == "h1"
        assert unit.role == "escort"
