# TODO / FIXME Inventory

Generated during the Phase A–J refactoring. Items marked **DONE** were
verified implemented and their stale markers removed.

## Stale markers removed
- `entity.py` — `# # TODO: Achievement fields will be added here` (fields live in `AchievementComponent`)
- `entity.py` — `# # TODO: Reincarnation fields will be added here` (fields live in `ReincarnationComponent`)
- `entity.py` — `# # TODO: Skill synthesis/evolution fields will be added here` (fields live in `SkillFusionComponent`)
- `entity.py` — `# # TODO: Story/world state fields will be added here` (fields live in `StorytellerComponent`)
- `game.py` — `# TODO: Achievement check` (implemented via `achievement_manager.check_all_achievements`)

## Outstanding (pre-existing, tracked for later)
- `game.py` — `# TODO: Reincarnation option` (line ~1627): wire reincarnation menu option.
- Broad `# TODO: handle exception properly` scattered across:
  archaeology_system.py, dungeon_quest_feedback.py, faction_war_system.py,
  failover.py, generate_rich_gifs.py, generate_skill_eater_gif.py,
  guild_quest_system.py, guild_skill_system.py, guild_system.py,
  inheritance_system.py, integrity_checker.py, item_system.py,
  journal_ui.py, karma_system.py, legacy_skill_system.py,
  license_checker.py, main_quest_system.py, map_engine.py, map_renderer.py,
  meta_progression_system.py, narrative_system.py, pet_evolution_system.py,
  pet_fusion_system.py, relationship_system.py, skill_fusion_system.py,
  skill_tree_system.py, sound_manager.py, title_system.py,
  world_event_system.py.
  These should be replaced with structured error handling in a later pass.
- `entity.py` — `# TODO: Reincarnation XP penalty` removed (moved to `CombatManager`, now uses `REINCARNATION_XP_PENALTY_*` constants).

## New (from recent work: Skill Eater, Pet Personality, Enchantments, Archaeology)
- `skill_eater/meta_intervention_system.py` — `# TODO: Wire meta-intervention triggers into game loop` (systems exist, need integration)
- `skill_eater/husk_forge.py` — `# TODO: Integrate husk forge into crafting UI` (forge logic complete, UI entry missing)
- `pet_personality_system.py` — `# TODO: Implement trait gameplay effects` (traits defined, effects on stats/behavior pending)
- `item_generator.py` / `item_system.py` — `# TODO: Full enchantment integration in item generation` (enchantments defined, generator wiring incomplete)
- `archaeology_decoder_system.py` — `# TODO: Connect decoder to world exploration flow` (decoder works standalone, world hooks missing)
- Broad `# TODO: handle exception properly` — `# TODO: Replace with structured error handling` (27 files; schedule dedicated pass)
- `game.py` — `# TODO: Reincarnation option` (line ~1627): wire reincarnation menu option.
- `save_system.py` — 新コンポーネントの永続化は **実測済み (2026-10-13)**: pickle 本線は
  Husk (player の HuskInventoryComponent) / pet 性格 (personality/bond/favorite_food_tags) /
  Item.enchants を保持。JSON 副線の pet 性格欠落は `ecs/entity.py` の to_dict/from_dict
  条件付き出力で修復 (`tests/test_entity_personality_persistence.py`)。
  **既知制約**: `Engine.__getstate__` は kernel/entity_manager を意図的に除外するため、
  kernel 保持の skill_eater システム実行状態と敵エンティティは非永続化
  (ロード後はライブの kernel を維持する `engine.__dict__.update()` 方式)。
