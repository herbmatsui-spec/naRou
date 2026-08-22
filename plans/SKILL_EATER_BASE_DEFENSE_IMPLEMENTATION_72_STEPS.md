# Skill Eater Base Defense System - 72-Step Implementation Plan

This plan breaks down the complete base defense system into 72 atomic steps that a low-performance LLM can implement sequentially. Each step is self-contained with clear inputs, outputs, and verification criteria.

---

## Phase 0: Foundation & Data Structures (Steps 1-10)

### Step 1: Create DefenseFacility Dataclass
**File**: `skill_eater_base_defense.py`
- Add `DefenseFacility` dataclass with fields: `id`, `name`, `level`, `max_level`, `tier_required`, `build_cost_aldo`, `build_cost_junk`, `hp`, `damage`, `range`, `cooldown`, `effect_description`
- Include `from_dict` classmethod for YAML loading
- Follow pattern of `BaseFacility` in economy system

### Step 2: Create RaidPhase Enum
**File**: `skill_eater_base_defense.py`
- Add `RaidPhase` enum: `WARNING`, `BREACH`, `AFTERMATH`
- Include duration constants: `WARNING_DURATION = 30` (seconds), `BREACH_DURATION = 120` (seconds)

### Step 3: Create RaidTrigger Dataclass
**File**: `skill_eater_base_defense.py`
- Add `RaidTrigger` dataclass: `trigger_type` (heat/turn/meta), `threshold`, `current_value`, `is_active`
- Types: `HEAT_LEVEL`, `ELAPSED_TURNS`, `META_QUEST_PROGRESS`

### Step 4: Create DamageReport Dataclass
**File**: `skill_eater_base_defense.py`
- Add `DamageReport`: `facility_id`, `damage_amount`, `hp_before`, `hp_after`, `is_destroyed`, `junk_looted`, `subordinate_injured`

### Step 5: Extend BaseDefenseManager with Defense Facilities
**File**: `skill_eater_base_defense.py`
- Add `defense_facilities: dict[str, DefenseFacility]` initialized with 4 facilities:
  - `auto_turret`: AutoTurret (Tier 1, 5000 aldo, 200 junk, DMG 50, Range 5, CD 2)
  - `barrier_generator`: BarrierGenerator (Tier 2, 8000 aldo, 300 junk, HP 500, CD 10)
  - `sensor_array`: SensorArray (Tier 2, 6000 aldo, 250 junk, Detection +3, CD 1)
  - `decoy_terminal`: DecoyTerminal (Tier 3, 10000 aldo, 400 junk, Decoy HP 300, CD 15)

### Step 6: Add Base Storage & Subordinates Tracking
**File**: `skill_eater_base_defense.py`
- Add `storage_junk: int = 0`, `storage_aldo: int = 0`, `subordinates: list[dict]` with `name`, `hp`, `max_hp`, `skills`
- Add `base_max_hp: int = 1000`, `base_current_hp: int = 1000`

### Step 7: Add Raid State Tracking Fields
**File**: `skill_eater_base_defense.py`
- Add: `current_phase: RaidPhase = RaidPhase.WARNING`, `phase_timer: int = 0`, `active_raid: bool = False`, `raid_enemies: list[dict]`, `warning_issued: bool = False`

### Step 8: Add Audio/Emote Constants
**File**: `skill_eater_base_defense.py`
- Add class constants:
  - `ALARM_KLAXON = "alarm_klaxon.ogg"`
  - `TURRET_FIRE = "turret_fire.ogg"`
  - `BARRIER_HUM = "barrier_hum.ogg"`
  - `EXPLOSION_DEBRIS = "explosion_debris.ogg"`
  - `EMOTE_SHIELD = "emote_shield.png"`
  - `EMOTE_WRENCH = "emote_wrench.png"`
  - `EMOTE_ALERT = "emote_alert.png"`
  - `EMOTE_CROSS = "emote_cross.png"`

### Step 9: Initialize Presentation & Audio References
**File**: `skill_eater_base_defense.py`
- Add `presentation: SkillEaterPresentationSystem`, `audio: SkillEaterAudioSystem` to `__init__`
- Accept optional params, default to singleton instances

### Step 10: Add Economy System Reference
**File**: `skill_eater_base_defense.py`
- Add `economy: SkillEaterEconomySystem` to `__init__`
- Accept optional param, default to new instance
- This enables access to `heat_level`, `aldo_currency`, `base_facilities`

---

## Phase 1: Facility Construction & Upgrades (Steps 11-18)

### Step 11: Implement can_build_facility()
**File**: `skill_eater_base_defense.py`
- Check: tier requirement met (via economy system), aldo >= cost, junk >= cost
- Return `(bool, str)` tuple with reason

### Step 12: Implement build_facility()
**File**: `skill_eater_base_defense.py`
- Deduct aldo/junk from economy/storage
- Set facility level = 1, hp = base_hp
- Play `emote_stars.png` + `chop.ogg` + `metalPot1.ogg`
- Return `(bool, str)`

### Step 13: Implement upgrade_facility()
**File**: `skill_eater_base_defense.py`
- Check level < max_level, resources sufficient
- Increase level, scale hp/damage/range by 1.2x per level
- Increase build_cost by 1.5x
- Play upgrade sound + emote

### Step 14: Implement get_facility_status()
**File**: `skill_eater_base_defense.py`
- Return dict with all facilities: id, name, level, hp, max_hp, damage, range, cooldown, is_operational

### Step 15: Implement repair_facility()
**File**: `skill_eater_base_defense.py` (AFTERMATH phase)
- Cost: junk = (max_hp - current_hp) * 2
- Restore HP to max
- Play `emote_wrench.png` + `metalPot1.ogg`

### Step 16: Implement collect_junk_from_storage()
**File**: `skill_eater_base_defense.py`
- Add junk to storage (called per turn from economy)
- Cap at 5000 junk base capacity

### Step 17: Implement collect_aldo_from_vault()
**File**: `skill_eater_base_defense.py`
- If `hq_vault` exists in economy, add aldo per turn = vault.level * 100
- Integrate with economy system's turn processing

### Step 18: Create YAML Config for Defense Facilities
**File**: `data/defense_facilities.yaml`
- Define all 4 facilities with tiers, costs, stats
- Load in `BaseDefenseManager.__init__` via new `load_from_yaml()` method

---

## Phase 2: Raid Trigger System (Steps 19-26)

### Step 19: Implement check_raid_triggers()
**File**: `skill_eater_base_defense.py`
- Check 3 triggers each turn:
  1. Heat level >= 80 (configurable)
  2. Elapsed turns >= 50 since last raid (configurable)
  3. Meta quest flag `raid_triggered` = True
- Return `(bool, RaidTrigger)` if any triggered

### Step 20: Implement start_raid_warning_phase()
**File**: `skill_eater_base_defense.py`
- Set `current_phase = RaidPhase.WARNING`, `phase_timer = 30`
- Set `active_raid = True`, `warning_issued = True`
- Generate raid enemies based on heat_level + facility tiers
- Play `alarm_klaxon.ogg` + `emote_alert.png`
- Return raid info dict

### Step 21: Implement generate_raid_enemies()
**File**: `skill_eater_base_defense.py`
- Base enemy count: 3 + (heat_level // 20)
- Enemy types: `MIDAS_SECURITY`, `MIDAS_ELITE`, `MIDAS_MECH`, `MIDAS_HACKER`
- Scale HP/ATK by heat_level * 0.5
- Assign target priority: storage > barrier > turret > sensor > decoy > base

### Step 22: Implement process_warning_phase()
**File**: `skill_eater_base_defense.py`
- Decrement `phase_timer` each turn
- If timer <= 0: transition to BREACH phase
- SensorArray reduces enemy accuracy by (level * 10)%
- Return warning status

### Step 23: Implement start_breach_phase()
**File**: `skill_eater_base_defense.py`
- Set `current_phase = RaidPhase.BREACH`, `phase_timer = 120`
- Activate all operational facilities
- Play `turret_fire.ogg` + `emote_shield.png`
- Initialize combat turn counter

### Step 24: Implement process_breach_phase()
**File**: `skill_eater_base_defense.py`
- Process facility attacks (turret, barrier pulse)
- Process enemy attacks on facilities
- Decrement timer
- If timer <= 0 or all enemies dead: transition to AFTERMATH
- Return breach status with damage reports

### Step 25: Implement facility_attack_enemies()
**File**: `skill_eater_base_defense.py`
- AutoTurret: attacks nearest enemy in range, DMG = level * 50, CD = 2 turns
- BarrierGenerator: grants shield to all facilities = level * 100 HP, CD = 10 turns
- SensorArray: reveals enemy positions, reduces enemy evasion
- DecoyTerminal: spawns decoy with HP = level * 300, attracts aggro

### Step 26: Implement enemy_attack_facilities()
**File**: `skill_eater_base_defense.py`
- Each enemy attacks highest priority target
- Damage = enemy_atk - facility_defense (min 1)
- Apply to facility HP
- If facility HP <= 0: mark destroyed, level -1 (min 1)
- 30% chance to loot junk from storage per destroyed facility

---

## Phase 3: Aftermath & Recovery (Steps 27-34)

### Step 27: Implement start_aftermath_phase()
**File**: `skill_eater_base_defense.py`
- Set `current_phase = RaidPhase.AFTERMATH`, `phase_timer = 10`
- Calculate total damage, junk looted, subordinate injuries
- Reset `active_raid = False`
- Play `explosion_debris.ogg` if base damaged

### Step 28: Implement calculate_aftermath_damage()
**File**: `skill_eater_base_defense.py`
- Return `DamageReport` list for each facility
- Include: junk looted (facility.level * 50), subordinate injury chance (20% per destroyed facility)
- Base HP damage = sum of facility damage taken

### Step 29: Implement apply_subordinate_injuries()
**File**: `skill_eater_base_defense.py`
- For each subordinate: 20% chance per destroyed facility to take 20% max HP damage
- If HP <= 0: mark as `incapacitated` (cannot work for 5 turns)
- Play `emote_cross.png` for each injury

### Step 30: Implement process_aftermath_phase()
**File**: `skill_eater_base_defense.py`
- Auto-repair facilities with available junk (priority: barrier > turret > sensor > decoy)
- Heal subordinates 10% HP per turn
- Decrement timer
- When timer <= 0: return to normal state

### Step 31: Implement get_aftermath_report()
**File**: `skill_eater_base_defense.py`
- Return summary: facilities damaged/destroyed, junk lost, subordinates injured, base HP remaining
- Include repair cost estimate

### Step 32: Implement reset_raid_state()
**File**: `skill_eater_base_defense.py`
- Clear raid_enemies, reset phase, timers, warning flag
- Reduce heat_level by 30 (min 0) after successful defense
- Reduce heat_level by 10 if base fell

### Step 33: Add Raid History Tracking
**File**: `skill_eater_base_defense.py`
- Add `raid_history: list[dict]` with timestamp, trigger, result, damage, rewards
- Keep last 20 raids

### Step 34: Implement get_raid_history()
**File**: `skill_eater_base_defense.py`
- Return formatted history for UI display

---

## Phase 4: Turn Processing Integration (Steps 35-42)

### Step 35: Implement process_turn()
**File**: `skill_eater_base_defense.py`
- Main entry point called from gameplay loop
- If not active_raid: check triggers → start warning if triggered
- If WARNING: process_warning_phase()
- If BREACH: process_breach_phase()
- If AFTERMATH: process_aftermath_phase()
- Return current state dict for UI

### Step 36: Integrate with Economy System Turn Tick
**File**: `skill_eater_economy_system.py`
- Add `defense_manager: BaseDefenseManager` field
- In `process_turn_tick()` (new method): call `defense_manager.process_turn()`
- Collect vault income, add to storage

### Step 37: Add Heat Level Integration
**File**: `skill_eater_economy_system.py`
- In `sell_skill_to_black_market`: after heat increase, call `defense_manager.increase_heat(amount)`
- Add `increase_heat(amount)` method to defense manager

### Step 38: Implement increase_heat()
**File**: `skill_eater_base_defense.py`
- Increase internal heat tracker
- At 50, 70, 90: play warning sounds with increasing urgency
- Return current heat and whether raid imminent

### Step 39: Add Meta Quest Raid Trigger
**File**: `skill_eater_base_defense.py`
- Add `trigger_meta_quest_raid()` method
- Sets meta_quest_trigger = True
- Used by story events

### Step 40: Implement get_defense_ui_state()
**File**: `skill_eater_base_defense.py`
- Return dict: phase, timer, heat, facilities status, enemies count, base HP
- Used by UI to show defense status

### Step 41: Add Facility Operational Check
**File**: `skill_eater_base_defense.py`
- Property `is_operational`: level > 0 and hp > 0
- Damaged facilities (HP < 50%) operate at 50% efficiency

### Step 42: Add Base HP Damage from Raid
**File**: `skill_eater_base_defense.py`
- If all facilities destroyed: base takes direct damage
- Base HP at 0: game over / base fallen state
- Play `explosion_debris.ogg` + `emote_cross.png`

---

## Phase 5: Audio/Visual Integration (Steps 43-50)

### Step 43: Add Warning Phase Audio/Emote
**File**: `skill_eater_base_defense.py`
- In `start_raid_warning_phase()`: `presentation.add_event(emote_alert.png, alarm_klaxon.ogg, "襲撃警報！")`
- Repeat alarm every 10 seconds during warning

### Step 44: Add Turret Fire Audio
**File**: `skill_eater_base_defense.py`
- In `facility_attack_enemies()`: when turret fires, `audio.play_sound(turret_fire.ogg)`
- Add `emote_shield.png` visual for barrier activation

### Step 45: Add Barrier Hum Audio
**File**: `skill_eater_base_defense.py`
- In `facility_attack_enemies()`: when barrier activates, `audio.play_sound(barrier_hum.ogg)`
- Loop while barrier active (or play once per activation)

### Step 46: Add Explosion Audio for Damage
**File**: `skill_eater_base_defense.py`
- In `enemy_attack_facilities()`: on facility hit, `audio.play_sound(explosion_debris.ogg)`
- On facility destroyed: play + `emote_cross.png`

### Step 47: Add Repair Audio/Emote
**File**: `skill_eater_base_defense.py`
- In `repair_facility()`: `presentation.add_event(emote_wrench.png, metalPot1.ogg, "修理完了")`

### Step 48: Add Aftermath Summary Audio
**File**: `skill_eater_base_defense.py`
- In `start_aftermath_phase()`: different sounds for victory/defeat
  - Victory: `fanfare.ogg` + `emote_stars.png`
  - Defeat: `explosion_debris.ogg` + `emote_cross.png`

### Step 49: Add Heat Level Warning Sounds
**File**: `skill_eater_base_defense.py`
- At heat 50: `metalClick.ogg` + `emote_exclamations.png` "警戒度上昇"
- At heat 70: `alarm_klaxon.ogg` (short) + `emote_alert.png` "危険水域"
- At heat 90: `alarm_klaxon.ogg` (loop) + `emote_alert.png` "襲撃差し迫る"

### Step 50: Add Facility Build/Upgrade Sounds
**File**: `skill_eater_base_defense.py`
- Reuse economy system sounds: `chop.ogg` + `metalPot1.ogg` + `emote_stars.png`
- On build fail: `metalClick.ogg` + `emote_cross.png`

---

## Phase 6: Configuration & Balancing (Steps 51-58)

### Step 51: Create Defense Config Constants
**File**: `skill_eater_base_defense.py`
- Add class-level constants for all numeric values (costs, damages, timers, chances)
- Make easily tunable

### Step 52: Implement Difficulty Scaling
**File**: `skill_eater_base_defense.py`
- Scale enemy stats by: `1.0 + (turn_number // 100) * 0.1`
- Scale raid frequency by heat_level

### Step 53: Add Facility Synergy Bonuses
**File**: `skill_eater_base_defense.py`
- Turret + Sensor: +20% accuracy
- Barrier + Decoy: decoy gets barrier HP
- All 4 built: +10% base HP

### Step 54: Implement Facility Special Abilities
**File**: `skill_eater_base_defense.py`
- Turret Lv3+: Piercing shot (ignores 50% armor)
- Barrier Lv3+: Reflect 25% damage
- Sensor Lv3+: Predict enemy target next turn
- Decoy Lv3+: Explodes on death (AoE damage)

### Step 55: Add Junk Loot Scaling
**File**: `skill_eater_base_defense.py`
- Junk looted = facility.level * 50 * (1 + heat_level/100)
- Aldo looted = facility.level * 20 * (1 + heat_level/100)

### Step 56: Implement Subordinate Protection
**File**: `skill_eater_base_defense.py`
- Subordinates with combat skills can man turrets (+50% DMG)
- Medical subordinates heal others in AFTERMATH (+20% heal rate)

### Step 57: Add Raid Rewards
**File**: `skill_eater_base_defense.py`
- On RAID_REPELLED_VICTORY: aldo = wave * 500, junk = wave * 100, reputation +10
- On BASE_FALLEN: lose 50% storage, all facilities -1 level

### Step 58: Balance Test Values
**File**: `skill_eater_base_defense.py`
- Document all values in comments
- Provide `balance_test()` method that simulates 100 raids

---

## Phase 7: Integration with Game Loop (Steps 59-65)

### Step 59: Add Defense Manager to Game Engine
**File**: `packages/gameplay/package.py` or engine init
- Instantiate `BaseDefenseManager` with economy reference
- Store in engine's world_a_data

### Step 60: Call process_turn() in Game Loop
**File**: `packages/gameplay/package.py` (GameplayLoop.advance_world)
- Add call to `defense_manager.process_turn()` in World A turn tick section
- Pass player/state for subordinate checks

### Step 61: Add UI Commands for Defense
**File**: New `skill_eater_defense_commands.py` or extend existing
- `build_defense <facility_id>`
- `upgrade_defense <facility_id>`
- `repair_defense <facility_id>`
- `defense_status`

### Step 62: Add Defense Status Display
**File**: UI system
- Show: phase, timer, heat, facilities (HP bars), enemies remaining
- Color code: green=ok, yellow=damaged, red=critical

### Step 63: Add Raid Warning Overlay
**File**: UI system
- During WARNING: full-screen alert with countdown
- Show enemy composition preview (from SensorArray)

### Step 64: Add Aftermath Report Screen
**File**: UI system
- Show damage summary, rewards, repair options
- Auto-advance after 10 seconds or key press

### Step 65: Save/Load Defense State
**File**: `skill_eater_base_defense.py`
- Add `to_dict()` and `from_dict(data)` methods
- Include all facilities, raid state, history, storage
- Integrate with existing save system

---

## Phase 8: Testing & Polish (Steps 66-72)

### Step 66: Unit Test - Facility Build/Upgrade
**File**: `test_skill_eater_base_defense.py`
- Test build requires correct tier/resources
- Test upgrade scales stats correctly
- Test max level cap

### Step 67: Unit Test - Raid Trigger
**File**: `test_skill_eater_base_defense.py`
- Test heat trigger at 80
- Test turn trigger at 50 turns
- Test meta quest trigger

### Step 68: Unit Test - Warning Phase
**File**: `test_skill_eater_base_defense.py`
- Test 30-turn countdown
- Test transition to BREACH
- Test sensor accuracy debuff

### Step 69: Unit Test - Breach Combat
**File**: `test_skill_eater_base_defense.py`
- Test turret attacks enemies
- Test barrier grants shield
- Test decoy attracts aggro
- Test facility destruction + level down

### Step 70: Unit Test - Aftermath
**File**: `test_skill_eater_base_defense.py`
- Test junk looting calculation
- Test subordinate injuries
- Test auto-repair priority
- Test heat reduction on victory

### Step 71: Integration Test - Full Raid Cycle
**File**: `test_skill_eater_base_defense.py`
- Simulate: build facilities → trigger raid → warning → breach → aftermath
- Verify state transitions correct
- Verify audio/emote events queued

### Step 72: Integration Test - Economy Link
**File**: `test_skill_eater_base_defense.py`
- Test black market sales increase heat → trigger raid
- Test vault income funds defense
- Test facility upgrade unlocks via secret skills

---

## File Structure Summary

```
naRou/
├── skill_eater_base_defense.py          # Main implementation (extended)
├── data/
│   └── defense_facilities.yaml          # Facility definitions
├── test_skill_eater_base_defense.py     # New test file
└── packages/gameplay/package.py         # Integration point (modified)
```

---

## Implementation Order Recommendation

1. **Steps 1-10**: Foundation - data classes, enums, references
2. **Steps 11-18**: Facility system - build, upgrade, repair
3. **Steps 19-26**: Raid triggers & combat phases
4. **Steps 27-34**: Aftermath & recovery
5. **Steps 35-42**: Turn processing & economy integration
6. **Steps 43-50**: Audio/visual polish
7. **Steps 51-58**: Balancing & special mechanics
8. **Steps 59-65**: Game loop integration & UI
9. **Steps 66-72**: Testing

Each step should be implemented, tested, and verified before moving to the next. Run the test file after each phase to catch regressions early.