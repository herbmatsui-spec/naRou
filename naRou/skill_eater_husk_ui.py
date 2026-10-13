"""UI functions for the Husk Puppet System."""

from naRou.config import get_config
from naRou.ecs.components.components import HuskComponent, PuppetUnitComponent
from naRou.skill_eater.skill_eater_husk_forge import PuppetForgeSystem
from naRou.skill_eater.skill_eater_husk_units import set_order


def open_forge_ui(player) -> str:
    """Open the puppet forge UI.

    Args:
        player: The player entity

    Returns:
        String identifier for the forge menu
    """
    return "forge_menu"


def list_husks(player) -> list[str]:
    """List all husks in the player's inventory.

    Args:
        player: The player entity with husk_inventory component

    Returns:
        List of strings representing husks in format "husk_id(source_monster)"
    """
    if not hasattr(player, 'husk_inventory') or not player.husk_inventory:
        return []

    husks = []
    for husk in player.husk_inventory.husks:
        husks.append(f"{husk.husk_id}({husk.source_monster})")
    return husks


def list_injectable_skills(player) -> list[str]:
    """List skills available for injection into husks.

    Args:
        player: The player entity

    Returns:
        List of skill names available for injection
    """
    # Try to get from config first, fallback to default list
    default_skills = ['fire_bolt', 'guard', 'dash']
    config_skills = get_config('husk.injectable_skills')
    return config_skills if config_skills is not None else default_skills


def ui_inject(player, husk_id: str, skill: str) -> None:
    """Handle UI injection request for a husk.

    Args:
        player: The player entity
        husk_id: The ID of the husk to inject into
        skill: The skill name to inject
    """
    if not hasattr(player, 'husk_inventory') or not player.husk_inventory:
        return

    # Find the husk with the matching ID
    target_husk = None
    for husk in player.husk_inventory.husks:
        if husk.husk_id == husk_id:
            target_husk = husk
            break

    if target_husk is None:
        return

    # Use the forge system to inject the skill
    forge = PuppetForgeSystem()
    try:
        forge.inject_skill(target_husk, skill)
    except ValueError:
        # Slot full - UI should handle this error
        pass


def forge_status(husk) -> str:
    """Get status string for display in forge UI.

    Args:
        husk: The husk to get status for

    Returns:
        Formatted string with control load and rebellion risk
    """
    forge = PuppetForgeSystem()
    load = forge.calc_control_load(husk)
    risk = forge.rebellion_risk(husk)
    return f"load={load} risk={risk:.2f}"


def dispatch(player, husk_id: str, role: str) -> None:
    """Dispatch a husk to become a puppet unit with the specified role.

    Args:
        player: The player entity
        husk_id: The ID of the husk to dispatch
        role: The role to assign to the unit ('escort', 'turret', or 'drone')
    """
    # Validate role
    if role not in ['escort', 'turret', 'drone']:
        raise ValueError(f"Invalid role: {role}. Valid roles: 'escort', 'turret', 'drone'")

    # Find the husk with the matching ID
    target_husk = None
    if hasattr(player, 'husk_inventory') and player.husk_inventory:
        for husk in player.husk_inventory.husks:
            if husk.husk_id == husk_id:
                target_husk = husk
                break

    if target_husk is None:
        return  # Husk not found

    # Create the forge system
    forge = PuppetForgeSystem()

    # Create unit from husk (using default protocol rank 0 for now)
    # In a full implementation, we might want to allow specifying protocol rank
    unit = forge.create_unit(target_husk, protocol_rank=0)

    # Add unit to player's units list
    if not hasattr(player, 'units'):
        player.units = []
    player.units.append(unit)
