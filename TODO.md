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
