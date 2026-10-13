"""Husk generation system for the Puppet Hacking feature."""

from naRou.config import get_config
from naRou.ecs.components.components import HuskComponent


def create_husk(source_monster: str, tier: int) -> HuskComponent:
    """Create a HuskComponent from a defeated monster.

    Args:
        source_monster: The name of the monster that was devoured
        tier: The tier/level of the monster

    Returns:
        A new HuskComponent instance
    """
    # Simple husk ID generation - in practice might want to avoid duplicates
    husk_id = f"husk_{source_monster}_{tier}"
    husk = HuskComponent(
        husk_id=husk_id,
        source_monster=source_monster,
        tier=tier
    )
    # Set slots based on tier: at least 1 slot, up to tier
    husk.slots = max(1, tier)
    return husk


def tick_husk_decay(player) -> None:
    """Update decay for all husks in player's inventory.

    Args:
        player: The player entity
    """
    from naRou.ecs.components.components import HuskInventoryComponent
    husk_inventory = player.get_component(HuskInventoryComponent)
    decay_per_turn = get_config('husk.decay_per_turn')
    for husk in husk_inventory.husks:
        husk.decay = min(husk.decay + decay_per_turn, husk.max_decay)
