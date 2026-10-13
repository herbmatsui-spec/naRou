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
- カバレッジ推進テスト (2026-10-13, 案9バッチ1) で発見した未修正バグ:
  - `skill_eater_synthesis_system.py:156-158` — 最後の2スキルを合成に消費すると
    `remove_skill` の `is_husk=True` が `add_skill` 後も解除されず、
    スキル所持のまま Husk 状態が残る
  - `skill_eater_synthesis_system.py:154,222` — 合成結果を `registry._skills`
    私有 dict に直接書き込み (API 境界違反)
  - `skill_eater_system.py` の `CharacterState.add_skill` / `current_memory_usage` —
    注入された registry を無視して `SkillEaterRegistry.get_instance()` を参照
    (非シングルトン運用でメモリ容量計算が破綻し得る)
  - `skill_eater_slum_map.py:102` — 記憶抽出前に `discovered_secrets` 4989
    フォールバックで金庫が開く (意図的か要確認)
- カバレッジバッチ2 (2026-10-14) で発見した未修正問題:
  - `skill_eater_concept_crystal.py:61` — `drop_history` がクラス属性の list
    で全インスタンス間で共有される
  - `skill_eater_crafting_system.py:127-128` — 本物の forge 経由では
    `except ValueError` 経路が到達不能 (`create_unit` 内の
    `except Exception: pass` が握り潰す)
  - `skill_eater_meta_recipes.py` — 未知入力時に暗黙の None を返す3メソッド
    (失敗辞書を返すべき)
  - `skill_eater_underground_arena.py` — `complete_wave` のスコア式が
    無攻撃 wave 完走でも high_score を増やす (累積平均DPS × 現wave)
- `game.py` — `# TODO: Reincarnation option` (line ~1627): wire reincarnation menu option.
- `save_system.py` — 新コンポーネントの永続化は **実測済み (2026-10-13)**: pickle 本線は
  Husk (player の HuskInventoryComponent) / pet 性格 (personality/bond/favorite_food_tags) /
  Item.enchants を保持。JSON 副線の pet 性格欠落は `ecs/entity.py` の to_dict/from_dict
  条件付き出力で修復 (`tests/test_entity_personality_persistence.py`)。
  **既知制約**: `Engine.__getstate__` は kernel/entity_manager を意図的に除外するため、
  kernel 保持の skill_eater システム実行状態と敵エンティティは非永続化
  (ロード後はライブの kernel を維持する `engine.__dict__.update()` 方式)。
