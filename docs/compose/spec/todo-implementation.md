---
feature: todo-implementation
status: in-progress
updated: 2025-01-21
branch: feature/todo-implementation
commits:
---

# TODO Implementation: 8 Items from Recent Work

## Report

## [S1] Problem
Eight new TODO items were added to track integration work from recent Skill Eater, Pet Personality, Item Enchantments, Archaeology, and Reincarnation systems. These systems exist but lack:
1. Game loop integration for meta-intervention triggers
2. Crafting UI integration for husk forge
3. Trait gameplay effects for pet personalities
4. Full enchantment integration in item generation
5. World exploration hooks for archaeology decoder
6. Structured error handling replacement (27 files)
7. Reincarnation menu option wiring
8. Save/load persistence for new components

## [S2] Design

### Architecture
Each TODO item represents an independent integration task. They share:
- **Engine integration points**: game loop, UI systems, save/load pipeline
- **Component persistence**: ECS components need serialization in save_system.py
- **Test coverage**: Each item needs regression tests

### 3-Agent Parallel Implementation Plan
Three agents work in parallel on disjoint file sets:
- **Agent A**: Skill Eater systems (meta-intervention triggers, husk forge UI)
- **Agent B**: Pet Personality + Item Enchantments (trait effects, enchantment wiring)
- **Agent C**: Archaeology + Reincarnation + Error Handling + Save System

### Contracts
- **Meta-intervention triggers**: Call `TemplateEventGenerator.maybe_spawn()` during exploration turns; present intervention UI via `InterventionEngine.execute()`
- **Husk forge UI**: Add forge menu entry in crafting UI; call `PuppetForgeSystem.create_unit()` on confirmation
- **Pet trait effects**: Hook `get_bond_stat_modifiers()` into combat/damage calculation; hook `evaluate_ai_behavior()` into pet AI turn
- **Enchantment wiring**: Ensure `ItemGenerator.generate_enchantments_for_item()` is called for all equipment; verify enchantment effects apply via `Inventory.get_stat_bonuses()`
- **Archaeology hooks**: Call `ArchaeologyDecoderSystem.collect_fragment()` on ruin/tile interaction; add decoder UI to journal
- **Error handling**: Replace bare `except:` with typed exceptions; add structured logging; create custom exception hierarchy
- **Reincarnation menu**: Add menu option in main menu/game over; call `ReincarnationManager.reincarnate()`
- **Save persistence**: Add `to_dict()`/`from_dict()` to new components; extend `SaveSystem.serialize_engine_to_dict()` and `deserialize_dict_to_engine()`

## [S3] Out of Scope
- Full Skill Eater content expansion
- New pet personalities beyond existing 5
- New enchantment types
- New archaeology fragments
- Reincarnation balance changes

## Tasks
- [ ] T1: Skill Eater — Wire meta-intervention triggers into game loop — acceptance: exploration turns spawn template events, intervention UI appears, rewards apply (covers: S2)
- [ ] T2: Skill Eater — Integrate husk forge into crafting UI — acceptance: forge accessible from crafting menu, creates units with correct stats (covers: S2)
- [ ] T3: Pet Personality — Implement trait gameplay effects — acceptance: bond modifiers affect combat stats; AI behavior matches personality (covers: S2)
- [ ] T4: Item Enchantments — Full generation integration — acceptance: random items have enchantments per quality; enchantment stats apply in combat (covers: S2)
- [ ] T5: Archaeology — Connect decoder to world exploration — acceptance: fragments discovered on ruin interaction; decoder UI accessible (covers: S2)
- [ ] T6: Error Handling — Replace 27 files' bare exceptions with structured handling — acceptance: all TODOs removed; custom exception hierarchy used; structured logging present (covers: S2)
- [ ] T7: Reincarnation — Wire menu option — acceptance: reincarnation option appears in menu/game over; executes full NG+ flow (covers: S2)
- [ ] T8: Save System — Persist new components — acceptance: HuskComponent, MetaInterventionState, PetPersonalityComponent, EnchantmentComponent survive save/load (covers: S2)
- [ ] T9: Regression Tests — Create tests for T1-T8 — acceptance: each integration has at least one test; CI passes (covers: S2; depends: T1-T8)