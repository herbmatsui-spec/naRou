# Architecture (Post-Refactor)

This document describes the refactored architecture of naRou.

## Layering

```
main.py / main_text.py
        │
        ▼
   Engine (game.py) ── delegates to Managers
        │
        ├── Kernel (packages/core/kernel)
        │      registers Packages & Systems
        │
        ├── Managers (managers/)        # extracted from Engine god-class
        │      Combat, SkillReward, PetBond, WorldNews,
        │      Persistence, Faction, ContextMenu, StateMachine, SetupCoordinator
        │
        └── Entity (entity.py) ── ECS component container
               components (components.py): Attributes, Title, GuildFaction,
               Achievement, Reincarnation, Skill*, Storyteller, Archaeology,
               BaseStats, Economy, Level, Affection, PetProfile, Emote, PetAI
```

## Packages

| Package | Provides |
|---------|----------|
| core | event_bus, time_system, turn_queue, renderer, entity_manager, message_log, debug_console |
| gameplay | dungeon_spawner, starter_items_factory, gameplay_loop, survival_system, combat_system |
| character | skill_tree_manager, job_manager, skill fusion/evolution/awakening/transfer/resonance/inheritance/specialization, player_pet_initializer |
| social | guild_manager, guild_quest_manager, faction_war_manager, guild_skill_manager, pet_contract/evolution/fusion, relationship, procedural_quest |
| meta | achievement, reincarnation, inheritance, karma, reincarnation_dungeon, legacy_skill, challenge, meta_progression, title |
| world | procedural_dungeon_generator, world_event_manager, archaeology_manager, world_state_manager, dungeon_theme_registry |
| narrative | storyteller, choice, dialogue, main_quest, journal_ui |
| platform | web_server_factory, input_handler |

## Key refactors (see REFACTOR_PLAN.md)

- **Engine god-class** split into 9 manager modules under `managers/`.
- **Entity** componentized: `affection`, `is_mounted`, `gene_skills`, `pet_type`,
  `pet_fusion_history`, `emote_*`, `pet_ai` now live in ECS components.
- **GodInfo** moved to `god_system.py`; **Skill**/**Attributes** moved to `components.py`.
- **localize()** single-sourced in `localization_manager.py`.
- **Magic numbers** centralized in `constants.py`.
- **YAML loading** centralized in `data_validation.py`.
