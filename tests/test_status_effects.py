from ecs.entity import Attributes, Entity
from naRou.systems import CombatSystem, StatusEffect


def test_status_effect_husk_and_regen():
    # Setup test entity
    attrs = Attributes(
        strength=10,
        endurance=10,
        dexterity=10,
        perception=10,
        learning=10,
        will=10,
        magic=10,
        charisma=10,
    )
    entity = Entity(
        x=0, y=0, char="@", color=(255, 255, 255), name="TestEntity", speed=100, attributes=attrs
    )
    entity.max_hp = 100
    entity.hp = 50
    entity.energy = 100

    # Add Husk effect
    husk = StatusEffect("Husk", remaining_ticks=50, power=1)
    entity.status_effects = [husk]

    # Process effects
    logs = CombatSystem.process_status_effects(entity)

    # Husk should drop energy to 0 or below
    assert entity.energy <= 0

    # Test Regen
    entity.status_effects = [StatusEffect("Regen", remaining_ticks=50, power=10)]
    CombatSystem.process_status_effects(entity)

    # Regen should heal
    assert entity.hp == 60


def test_infinite_status_effect():
    attrs = Attributes(
        strength=10,
        endurance=10,
        dexterity=10,
        perception=10,
        learning=10,
        will=10,
        magic=10,
        charisma=10,
    )
    entity = Entity(
        x=0, y=0, char="@", color=(255, 255, 255), name="TestEntity", speed=100, attributes=attrs
    )
    entity.max_hp = 100

    inf_eff = StatusEffect("Regen", remaining_ticks=100, power=1)
    inf_eff.is_infinite = True
    entity.status_effects = [inf_eff]

    CombatSystem.process_status_effects(entity)

    # Tick should not decrease if infinite
    assert entity.status_effects[0].remaining_ticks == 100
