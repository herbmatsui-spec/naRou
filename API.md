# API Reference (Post-Refactor)

## Engine (`game.py`)

Public surface that callers and the rendering layer should rely on.

| Member | Kind | Purpose |
|--------|------|---------|
| `Engine(renderer=None, kernel=None)` | ctor | DI-friendly; pass a prebuilt `kernel` for tests |
| `player`, `pet` | property | Player / pet `Entity` accessors |
| `inventory`, `game_map`, `current_state` | property | Game-state accessors |
| `setup_systems()` | method | Wires subsystems (delegates to `managers.setup_coordinator`) |
| `player_act(dx, dy)` | method | Player movement/action |
| `advance_world()` | method | Per-turn NPC/world processing |
| `_on_kill(entity)` | method | Kill settlement (delegates to managers) |
| `open_context_menu()` | method | Build context actions (delegates to `ContextMenuBuilder`) |
| `change_state(new_state)` | method | State transition (delegates to `StateMachine`) |
| `log(text, color, level)` | method | Append to message log |

## Kernel (`packages/core/kernel/kernel.py`)

| Member | Purpose |
|--------|---------|
| `register_system(name, system)` | Register a system (raises if duplicate) |
| `get_system(name, default=None)` | Fetch a system; returns `default` if provided |
| `get_system_strict(name)` | Fetch a system; raises `KeyError` if missing |
| `has_system(name)` | Membership check |
| `load_package(pkg)` / `unload_package(name)` | Package lifecycle |
| `resolve_load_order(names)` | Topological ordering helper |

## Managers (`managers/`)

Each manager encapsulates a slice of former `Engine` logic:

- `CombatManager.handle_kill_rewards(engine, entity)`
- `SkillRewardManager.grant_kill_skill_points(engine, entity)`
- `PetBondManager.update_combat_bond(engine, entity)` / `update_turn_bond(engine)`
- `WorldNewsManager.advance(engine)`
- `PersistenceManager.autosave_if_due(engine)`
- `FactionManager.update_kill_reputation(engine, entity)` / `update_influence(engine)`
- `ContextMenuBuilder.build_actions(engine) -> list[ContextAction]`
- `StateMachine.apply(engine, new_state)`
- `setup_systems(engine)` (module function)

## Entity (`entity.py`)

`Entity` is a component container. Attributes are accessed via properties that
delegate to ECS components (e.g. `entity.affection`, `entity.gold`,
`entity.pet_ai`). Use `entity.get_component(ComponentClass)` to access a
component directly. Serialization is `entity.to_dict()` / `Entity.from_dict()`.
