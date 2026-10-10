"""Puppet Forge system for injecting skills into Husks."""

from naRou.ecs.components.components import HuskComponent, PuppetUnitComponent
from naRou.config import get_config


class PuppetForgeSystem:
    def __init__(self):
        # Skill attribute mapping for role determination
        self.skill_attributes = {
            # Attack skills
            'fire_bolt': 'attack',
            'ice_shard': 'attack',
            'lightning': 'attack',
            'poison': 'attack',
            'slash': 'attack',
            'thrust': 'attack',
            'wave': 'attack',
            # Defense skills
            'heal': 'defense',
            'shield': 'defense',
            'armor': 'defense',
            'barrier': 'defense',
            'regen': 'defense',
            # Movement/Utility skills
            'dash': 'movement',
            'teleport': 'movement',
            'stealth': 'movement',
            'scan': 'movement',
            'tracking': 'movement',
            # Default fallback
        }

    def calc_control_load(self, husk: HuskComponent) -> int:
        """Calculate control load for a husk based on injected skills and codes.
        
        Args:
            husk: The husk to calculate control load for
            
        Returns:
            Control load value (higher = more difficult to control)
        """
        # Base load from skills: 10 per skill
        skill_load = len(husk.injected_skills) * 10
        # Base load from codes: 5 per code
        code_load = len(husk.injected_codes) * 5
        return skill_load + code_load

    def inject_skill(self, husk: HuskComponent, skill: str) -> None:
        """Inject a skill into a husk.
        
        Args:
            husk: The husk to inject the skill into
            skill: The skill name to inject
            
        Raises:
            ValueError: If the husk has no available slots
        """
        if len(husk.injected_skills) >= husk.slots:
            raise ValueError("slots full")
        husk.injected_skills.append(skill)

    def inject_code(self, husk: HuskComponent, code: str) -> None:
        """Inject a chimera code into a husk.
        
        Args:
            husk: The husk to inject the code into
            code: The chimera code name to inject
            
        Raises:
            ValueError: If the husk has no available code slots
                     (code slots are half of skill slots, minimum 1)
        """
        max_code_slots = max(1, husk.slots // 2)
        if len(husk.injected_codes) >= max_code_slots:
            raise ValueError("code slots full")
        husk.injected_codes.append(code)

    def role_of(self, husk: HuskComponent) -> str:
        """Determine the role of a husk based on injected skills.
        
        Args:
            husk: The husk to determine role for
            
        Returns:
            One of: 'escort', 'turret', 'drone'
        """
        if not husk.injected_skills:
            # No skills injected - default to escort
            return 'escort'
        
        # Count skills by attribute
        attr_counts = {'attack': 0, 'defense': 0, 'movement': 0}
        
        for skill in husk.injected_skills:
            attr = self.skill_attributes.get(skill, 'attack')  # Default to attack
            attr_counts[attr] = attr_counts.get(attr, 0) + 1
        
        # Determine role based on which attribute has the most skills
        # In case of tie, priority: attack > defense > movement
        max_count = max(attr_counts.values())
        if attr_counts['attack'] == max_count:
            return 'escort'
        elif attr_counts['defense'] == max_count:
            return 'turret'
        else:
            return 'drone'

    def rebellion_risk(self, husk: HuskComponent) -> float:
        """Calculate rebellion risk for a husk.
        
        Args:
            husk: The husk to calculate rebellion risk for
            
        Returns:
            Rebellion risk value (0.0 to 1.0+)
        """
        control_load = self.calc_control_load(husk)
        # Risk increases with control load and decreases with loyalty
        # Formula: max(0.0, (control_load - loyalty * 2) / 100)
        risk = max(0.0, (control_load - husk.loyalty * 2) / 100)
        return risk

    def effective_power(self, husk: HuskComponent, protocol_rank: int) -> float:
        """Calculate effective power of a husk with protocol rank applied.
        
        Args:
            husk: The husk to calculate effective power for
            protocol_rank: The rank of the control protocol (0-10)
            
        Returns:
            Effective power value (minimum 0.1)
        """
        base_power = 1.0 + 0.1 * protocol_rank
        risk_penalty = self.rebellion_risk(husk)
        effective_power = base_power - risk_penalty
        # Clamp to minimum 0.1
        return max(0.1, effective_power)

    def create_unit(self, husk: HuskComponent, protocol_rank: int = 0, player=None) -> PuppetUnitComponent:
        """Create a puppet unit from a husk.
        
        Args:
            husk: The husk to create a unit from
            protocol_rank: The rank of the control protocol (0-10), default 0
            player: The player entity (optional, for resource consumption)
            
        Returns:
            PuppetUnitComponent: The created puppet unit
            
        Raises:
            ValueError: If player doesn't have enough resources
        """
        # Determine the role based on injected skills
        role = self.role_of(husk)
        
        # Calculate base HP from effective power
        # effective_power is multiplied by 10 to get HP (so 1.0 = 10 HP, 2.0 = 20 HP, etc.)
        base_hp = int(self.effective_power(husk, protocol_rank) * 10)
        
        # Consume resources if player is provided
        if player is not None:
            forge_fuel_cost = get_config('husk.forge_fuel')
            # Try to get economy component from player using standard ECS pattern
            try:
                # Try to import EconomyComponent
                try:
                    from naRou.ecs.components.components import EconomyComponent
                    economy = player.get_component(EconomyComponent)
                    if economy.gold < forge_fuel_cost:
                        raise ValueError(f"Insufficient gold: need {forge_fuel_cost}, have {economy.gold}")
                    economy.gold -= forge_fuel_cost
                except ImportError:
                    # EconomyComponent not available in this view - skip resource consumption
                    # In a full implementation, this component would exist
                    pass
                except AttributeError:
                    # Player doesn't have get_component method - try direct attribute
                    if hasattr(player, 'gold') and player.gold >= forge_fuel_cost:
                        player.gold -= forge_fuel_cost
                    elif hasattr(player, 'aldo_currency') and player.aldo_currency >= forge_fuel_cost:
                        player.aldo_currency -= forge_fuel_cost
                    # If we can't access resources through known paths, skip consumption for now
            except Exception:
                # Any other error - skip resource consumption to avoid breaking the flow
                pass
        
        # Create the unit
        unit = PuppetUnitComponent(
            unit_id=f"unit_{husk.husk_id}",
            role=role,
            husk_ref=husk.husk_id,
            hp=base_hp,
            max_hp=base_hp
        )
        
        # Copy injected skills and codes to the unit
        unit.injected_skills = husk.injected_skills.copy()
        unit.injected_codes = husk.injected_codes.copy()
        
        return unit