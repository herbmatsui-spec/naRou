"""Systems for operating puppet units."""

from naRou.ecs.components.components import PuppetUnitComponent

# Order definitions
ORDERS = {
    "follow": "追従",
    "hold": "固定迎撃",
    "patrol": "巡回回収"
}


def tick_units(player) -> None:
    """Update all puppet units based on their current state.

    Args:
        player: The player entity containing units

    Note:
        Currently does nothing - to be expanded in later steps.
    """
    if not hasattr(player, 'units') or not player.units:
        return

    # Process each unit based on its state
    for unit in player.units:
        # Increment corruption for active units (Step 46)
        if hasattr(unit, 'state') and unit.state == 'active':
            if hasattr(unit, 'corruption'):
                unit.corruption += 1

        # Decrease corruption and increase loyalty for charging units (Step 47)
        if hasattr(unit, 'state') and unit.state == 'charging':
            if hasattr(unit, 'corruption'):
                unit.corruption = max(0, unit.corruption - 2)
            if hasattr(unit, 'loyalty'):
                unit.loyalty += 1

        # Handle reboot state for units with 0 HP (Step 53)
        if hasattr(unit, 'hp') and hasattr(unit, 'state'):
            if unit.hp <= 0 and unit.state != 'reboot':
                unit.state = 'reboot'
                # Don't remove the unit, just mark it for reboot/repair

        # For now, do nothing else - implementation will be expanded in later steps
        pass


def set_order(unit: PuppetUnitComponent, order: str) -> None:
    """Set the order for a puppet unit.

    Args:
        unit: The puppet unit to modify
        order: The order to set (must be in ORDERS dict)

    Raises:
        ValueError: If the order is not valid
    """
    if order not in ORDERS:
        raise ValueError(f"Invalid order: {order}. Valid orders: {list(ORDERS.keys())}")
    unit.order = order


def update_escort(unit: PuppetUnitComponent, player) -> None:
    """Update escort unit to follow the player and participate in combat.

    Args:
        unit: The puppet unit (should be escort role)
        player: The player entity to follow
    """
    # Follow the player
    if hasattr(unit, 'role') and unit.role == 'escort':
        if hasattr(player, 'location'):
            unit.location = player.location

    # Participate in combat using injected skills (Step 41)
    # TODO: Implement proper combat participation using servant system
    # This would involve:
    # 1. Getting the servant system instance
    # 2. Creating a servant state from the unit's injected skills
    # 3. Calling the servant system's attack/execute function
    if hasattr(unit, 'role') and unit.role == 'escort':
        # Placeholder for combat participation
        # In full implementation:
        # servant_system = SkillEaterServantSystem.get_instance()
        # # Convert unit's injected skills to servant state
        # # servant_system.execute_servant_turn(servant_state, enemies, allies)
        pass


def update_turret(unit: PuppetUnitComponent) -> None:
    """Update turret unit to activate and fix at base.

    Args:
        unit: The puppet unit (should be turret role)
    """
    if hasattr(unit, 'role') and unit.role == 'turret':
        unit.state = 'active'
        unit.location = 'base'
        # Notify base defense system of turret activation (Step 43)
        # TODO: Implement base defense integration
        # In full implementation:
        # if hasattr(base_defense_system, 'register_turret'):
        #     base_defense_system.register_turret(unit)


def update_drone(unit: PuppetUnitComponent, warehouse) -> None:
    """Update drone unit to collect materials.

    Args:
        unit: The puppet unit (should be drone role)
        warehouse: The warehouse object to collect materials into
    """
    if hasattr(unit, 'role') and unit.role == 'drone':
        if hasattr(warehouse, 'materials'):
            warehouse.materials += 1


def set_route(unit: PuppetUnitComponent, route: list[str]) -> None:
    """Set the patrol route for a drone unit.

    Args:
        unit: The puppet unit (should be drone role)
        route: The route to set as list of location strings
    """
    if hasattr(unit, 'route'):
        unit.route = route


def effective_bonus(unit: PuppetUnitComponent) -> float:
    """Get the effective loyalty bonus for a unit.

    Args:
        unit: The puppet unit

    Returns:
        Bonus multiplier: 1.2 if loyalty >= 50, otherwise 1.0
    """
    if hasattr(unit, 'loyalty') and unit.loyalty >= 50:
        return 1.2
    return 1.0
