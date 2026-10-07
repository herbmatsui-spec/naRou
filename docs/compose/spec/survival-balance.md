# Survival Balance Specification (Step 29)

## Overview

This document defines the numeric relationships between natural regeneration, toxicity, and hunger systems. The goal is to ensure that:
1. Starvation outpaces regeneration within a single run
2. Idle players reach a non-lethal starvation equilibrium
3. The 8000 hunger ÷ 1/turn, regen cannot catch up constraint is verified

## Core Parameters

### Hunger System
- **Starting hunger**: 8000
- **Hunger decay per turn**: 1
- **Starvation threshold**: hunger ≤ 0
- **Starvation damage**: 2 HP per turn when hunger ≤ 0
- **Low hunger warning**: hunger < 1000 (10% chance per turn to log warning)

### Natural Regeneration
- **Base HP regen per turn**: 0 (no natural regen in standard SurvivalSystem)
- **Sleep regeneration**: Full HP/MP restoration (via `sleep()` method)
- **Food-based regeneration**: Via eating food items (nutrition value added to hunger)

### Toxicity System (World A / Skill Eater)
- **Toxicity gain per turn**: 1 (when in Skill Eater world)
- **Toxicity damage threshold**: 80%
- **Toxicity damage**: 2 HP per turn when toxicity ≥ 80%
- **Max toxicity**: 100%

## Numeric Relationships

### 1. Starvation Outpaces Regeneration

**Constraint**: A player who does not eat will die from starvation before natural regeneration can save them.

**Analysis**:
- Starting hunger: 8000
- Hunger decay: 1/turn
- Time to starvation: 8000 turns
- Starvation damage: 2 HP/turn after hunger reaches 0
- Starting HP: ~55 (level 1 player with jure god)
- Time to death from starvation: 55 HP ÷ 2 HP/turn = ~27.5 turns
- Total survival time without food: 8000 + 27.5 ≈ 8027 turns

**Regeneration sources**:
- Natural regen: 0 HP/turn (standard SurvivalSystem)
- Sleep: Full restore but costs ~2000 turns (20 x advance_world)
- Food: Nutrition values (bread=1500, ration=3200, apple=800, meat=2400)

**Conclusion**: Without active food consumption, the player has ~8027 turns before death. Natural regeneration (0 HP/turn) cannot catch up to hunger decay. The player MUST eat to survive.

### 2. Idle Player Non-Lethal Starvation Equilibrium

**Constraint**: An idle player (waiting/sleeping) should reach a stable starvation state that is not immediately lethal.

**Analysis**:
- If player uses `WaitAction` (1 turn), hunger decreases by 1
- If player uses `SleepAction` (~2000 turns), hunger decreases by ~2000
- Sleep restores full HP/MP but costs significant hunger
- Equilibrium: Player can sleep ~4 times before starvation damage begins (8000 ÷ 2000 = 4)
- After 4 sleeps: hunger ≈ 0, then starvation damage begins

**Non-lethal equilibrium**: 
- Player can maintain hunger > 1000 by eating periodically
- Bread (1500 nutrition) every ~1500 turns maintains safe hunger level
- This creates a "maintenance loop" that is sustainable but requires active play

### 3. Hunger ÷ Regen Verification

**Constraint**: 8000 hunger ÷ 1/turn, regen cannot catch up

**Verification**:
- Hunger pool: 8000
- Decay rate: 1/turn
- Regeneration rate: 0 HP/turn (passive)
- Active regen (food): 
  - Bread: 1500 nutrition = 1500 turns of hunger
  - Ration: 3200 nutrition = 3200 turns of hunger
- Net hunger change per bread cycle (eat every 1500 turns): +1500 - 1500 = 0 (equilibrium)
- Without food: -8000 over 8000 turns → death

**Mathematical proof**:
```
Let H(t) = hunger at turn t
H(t) = 8000 - t + Σ(nutrition_i) where nutrition_i is food eaten at turn i

dH/dt = -1 + Σ(nutrition_i * δ(t - t_i))

For equilibrium: Σ(nutrition_i / Δt_i) = 1
Where Δt_i is time between food consumptions

Bread cycle: 1500 nutrition / 1500 turns = 1.0 → equilibrium
Ration cycle: 3200 nutrition / 3200 turns = 1.0 → equilibrium

Passive regen contribution: 0
Therefore: regen cannot catch up without active food consumption
```

### 4. Toxicity vs Hunger Interaction (World A)

**Constraint**: Toxicity adds pressure but doesn't replace hunger mechanics.

**Analysis**:
- Toxicity gain: 1/turn (only in Skill Eater world)
- Toxicity damage starts at 80% (80 turns)
- Toxicity damage: 2 HP/turn (same as starvation)
- Combined with starvation: 4 HP/turn when both active
- Time to death with both: 55 HP ÷ 4 HP/turn = ~13.75 turns

**Relationship**: Toxicity accelerates death but hunger is the primary clock. In Skill Eater world, players face dual time pressure.

## Test Scenarios

### Test 1: Starving Outpaces Regen Within a Run
```python
def test_starving_outpaces_regen_within_a_run():
    """Verify that a player who never eats dies within 8027 turns."""
    # Setup: fresh player, no food
    # Run: simulate 9000 turns of waiting
    # Assert: player dies before turn 8027
```

### Test 2: Idle Player Reaches Non-Lethal Starvation
```python
def test_idle_player_reaches_a_nonlethal_starvation():
    """Verify player can maintain hunger > 1000 by eating bread every 1500 turns."""
    # Setup: player with bread supply
    # Run: simulate eat-wait cycles
    # Assert: hunger stabilizes around 1500-3000 range
```

### Test 3: Hunger ÷ Regen Verification
```python
def test_hunger_div_regen_cannot_catch_up():
    """Verify 8000 hunger ÷ 1/turn, passive regen (0) cannot catch up."""
    # Assert: passive_regen_rate < hunger_decay_rate
    # Assert: active food required for survival
```

## Balance Tuning Knobs

| Parameter | Current Value | Effect if Increased | Effect if Decreased |
|-----------|---------------|---------------------|---------------------|
| Starting hunger | 8000 | Longer survival, less pressure | Shorter survival, more pressure |
| Hunger decay/turn | 1 | Faster starvation | Slower starvation |
| Starvation damage | 2 HP/turn | Faster death when starving | Slower death when starving |
| Bread nutrition | 1500 | Easier maintenance | Harder maintenance |
| Ration nutrition | 3200 | Easier maintenance | Harder maintenance |
| Sleep hunger cost | ~2000 | Sleep more costly | Sleep less costly |
| Toxicity gain/turn | 1 | Faster toxicity pressure | Slower toxicity pressure |

## Related Systems

- `survival_system.py`: Core hunger/sleep/karma logic
- `systems.py`: SurvivalSystem implementation
- `input_actions.py`: WaitAction, SleepAction
- `item_system.py`: Food items with nutrition values
- World A toxicity: `engine.py` World A turn tick (lines 373-388)

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| Step 29 | Initial specification | Define survival balance relationships |