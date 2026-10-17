"""Coverage tests for skill_eater_husk_units (puppet unit operations)."""

from __future__ import annotations

from unittest.mock import MagicMock

from naRou.ecs.components.components import PuppetUnitComponent

from skill_eater_husk_units import (
    ORDERS,
    effective_bonus,
    set_order,
    set_route,
    tick_units,
    update_drone,
    update_escort,
    update_turret,
)


class _Player:
    def __init__(self, location="base"):
        self.location = location
        self.units = []


class TestTickUnits:
    def test_no_units(self) -> None:
        player = MagicMock()
        del player.units
        tick_units(player)  # should not raise

    def test_empty_units(self) -> None:
        player = _Player()
        tick_units(player)

    def test_active_increments_corruption(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", state="active", corruption=0)
        player = _Player()
        player.units = [unit]
        tick_units(player)
        assert unit.corruption == 1

    def test_charging_decreases_corruption_increases_loyalty(self) -> None:
        unit = PuppetUnitComponent(
            unit_id="u1", role="escort", husk_ref="h1", state="charging", corruption=5, loyalty=0
        )
        player = _Player()
        player.units = [unit]
        tick_units(player)
        assert unit.corruption == 3
        assert unit.loyalty == 1

    def test_zero_hp_sets_reboot(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", hp=0, state="active")
        player = _Player()
        player.units = [unit]
        tick_units(player)
        assert unit.state == "reboot"

    def test_zero_hp_already_reboot_unchanged(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", hp=0, state="reboot")
        player = _Player()
        player.units = [unit]
        tick_units(player)
        assert unit.state == "reboot"


class TestSetOrder:
    def test_valid_orders(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        for order in ORDERS:
            set_order(unit, order)
            assert unit.order == order

    def test_invalid_order_raises(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        with pytest_raises_value_error(unit, "bogus"):
            pass


def pytest_raises_value_error(unit, order):  # helper placeholder (not collected)
    from skill_eater_husk_units import set_order
    try:
        set_order(unit, order)
    except ValueError as exc:
        assert "Invalid order" in str(exc)
        return
    raise AssertionError("expected ValueError")


class TestSetOrderInline:
    def test_invalid_order_raises_valueerror(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        try:
            set_order(unit, "bogus")
        except ValueError as exc:
            assert "Invalid order" in str(exc)
            assert "escort" in str(exc) or "turret" in str(exc) or "drone" in str(exc)
            return
        raise AssertionError("expected ValueError")


class TestUpdateEscort:
    def test_copies_player_location(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", location="old")
        player = _Player(location="dungeon_entrance")
        update_escort(unit, player)
        assert unit.location == "dungeon_entrance"

    def test_non_escort_unchanged(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="turret", husk_ref="h1", location="base")
        player = _Player(location="dungeon_entrance")
        update_escort(unit, player)
        assert unit.location == "base"


class TestUpdateTurret:
    def test_activates_at_base(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="turret", husk_ref="h1", state="sleep", location="field")
        update_turret(unit)
        assert unit.state == "active"
        assert unit.location == "base"

    def test_non_turret_unchanged(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", state="active", location="field")
        update_turret(unit)
        assert unit.state == "active"
        assert unit.location == "field"


class TestUpdateDrone:
    def test_collects_material(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="drone", husk_ref="h1")
        warehouse = MagicMock()
        warehouse.materials = 0
        update_drone(unit, warehouse)
        assert warehouse.materials == 1

    def test_non_drone_no_effect(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        warehouse = MagicMock()
        warehouse.materials = 5
        update_drone(unit, warehouse)
        assert warehouse.materials == 5


class TestSetRoute:
    def test_sets_route(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="drone", husk_ref="h1")
        set_route(unit, ["a", "b", "c"])
        assert unit.route == ["a", "b", "c"]

    def test_no_route_attribute(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        del unit.route
        set_route(unit, ["a"])  # should not raise (hasattr guard)


class TestEffectiveBonus:
    def test_loyalty_fifty_plus(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", loyalty=50)
        assert effective_bonus(unit) == 1.2

    def test_loyalty_above_fifty(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", loyalty=100)
        assert effective_bonus(unit) == 1.2

    def test_loyalty_below_fifty(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1", loyalty=49)
        assert effective_bonus(unit) == 1.0

    def test_no_loyalty_attribute(self) -> None:
        unit = PuppetUnitComponent(unit_id="u1", role="escort", husk_ref="h1")
        del unit.loyalty
        assert effective_bonus(unit) == 1.0
