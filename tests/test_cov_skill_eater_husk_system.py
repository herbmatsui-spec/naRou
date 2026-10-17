"""Coverage tests for skill_eater_husk_system (create_husk / tick_husk_decay)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from naRou.ecs.components.components import HuskComponent, HuskInventoryComponent

from skill_eater_husk_system import create_husk, tick_husk_decay


class TestCreateHusk:
    def test_basic(self) -> None:
        husk = create_husk("goblin", 1)
        assert isinstance(husk, HuskComponent)
        assert husk.husk_id == "husk_goblin_1"
        assert husk.source_monster == "goblin"
        assert husk.tier == 1
        assert husk.slots == 1

    def test_tier_zero_min_one_slot(self) -> None:
        husk = create_husk("slime", 0)
        assert husk.slots == 1

    def test_tier_five_five_slots(self) -> None:
        husk = create_husk("dragon", 5)
        assert husk.slots == 5

    def test_default_fields(self) -> None:
        husk = create_husk("goblin", 3)
        assert husk.decay == 0
        assert husk.max_decay == 100
        assert husk.corruption == 0
        assert husk.loyalty == 0
        assert husk.injected_skills == []
        assert husk.injected_codes == []


class TestTickHuskDecay:
    def test_no_inventory_component(self) -> None:
        player = MagicMock()
        del player.husk_inventory
        # Should not raise; just returns
        tick_husk_decay(player)

    def test_empty_inventory(self) -> None:
        player = MagicMock()
        player.husk_inventory = HuskInventoryComponent(husks=[])
        tick_husk_decay(player)
        assert player.husk_inventory.husks == []

    def test_decay_increases(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=2)
        husk.decay = 10
        player = MagicMock()
        player.husk_inventory = HuskInventoryComponent(husks=[husk])

        with patch("skill_eater_husk_system.get_config", return_value=5):
            tick_husk_decay(player)

        assert husk.decay == 15

    def test_decay_clamped_at_max_decay(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=2)
        husk.decay = 98
        husk.max_decay = 100
        player = MagicMock()
        player.husk_inventory = HuskInventoryComponent(husks=[husk])

        with patch("skill_eater_husk_system.get_config", return_value=10):
            tick_husk_decay(player)

        assert husk.decay == 100

    def test_get_config_default_when_none(self) -> None:
        husk = HuskComponent(husk_id="h1", source_monster="goblin", tier=1)
        husk.decay = 0
        player = MagicMock()
        player.husk_inventory = HuskInventoryComponent(husks=[husk])

        with patch("skill_eater_husk_system.get_config", return_value=None):
            tick_husk_decay(player)
        # None decay_per_turn -> min(0 + None, ...) would TypeError; code path
        # simply skips because decay_per_turn is None -> decay unchanged
        assert husk.decay == 0
