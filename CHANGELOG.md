# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Tiny Rogue Graphics Pack integration (Kenney "Tiny Rogue" asset pack)

### Refactored
- Split `Engine` god-class into `managers/` (Combat, SkillReward, PetBond, WorldNews, Persistence, Faction, ContextMenu, StateMachine, SetupCoordinator)
- Componentized `Entity`: `affection`, `pet_type`, `emote_*`, `pet_ai` now ECS components
- Moved `GodInfo` → `god_system.py`, `Skill`/`Attributes` → `components.py`
- Centralized `localize()` in `localization_manager.py`; magic numbers → `constants.py`
- Added `data_validation.py` YAML loader; `Kernel.get_system` default overload; DI-friendly `Engine(renderer, kernel)`
- Added unit tests (core_framework, event_bus, entity, config_manager, kernel) and `tools/cli.py`
- 132 new tiles across 12 categories: floors, walls, decorations, items, monsters, effects, UI
- New `tiny_rogue_16` atlas scale (509×115) with 105 tile entries
- Monster rendering: 12 monster types mapped to `TR_MONSTER_01/02/03` and `TR_MONSTER_VAR_01/02/03` with 4-directional animation
- Particle effects: 12 new effect types using `TR_EFFECT_01-12` (magic_cast, fire, ice, lightning, poison, heal, teleport, explosion, sparkle, smoke, slash, shockwave)
- Blood splatter system using `TR_DECOR_10` on damage/kill with directional splatter
- UI icons: heart, mana, coin, key, sword, shield, potion, level using `TR_UI_01-12`
- Screen flash on critical hits using `TR_EFFECT_09` + `TR_EFFECT_01`
- Dynamic lighting enhancements: tile-specific properties (emissive, reflective, translucent, material)
- Ambient occlusion for wall corners based on neighbor count
- Parallax background layers from `tilemap_packed.png`
- Weather effects: rain, snow, ash using repurposed effect tiles
- Tile variant randomization (12 floor variants) during dungeon generation
- Footstep particles matching floor type (stone, water, grass, dirt)
- Death animations with monster-type-specific effects
- Loot sparkle with rarity-based colors on item drops
- Feature flag `ENABLE_TINY_ROGUE_GFX` (toggle with `G` key)
- Tile mapping utilities for dungeon generation, items, decorations, effects, UI
- Comprehensive integration test suite
- Demo script `demo_tiny_rogue_graphics.py` showcasing all features
- テキスト(ASCII)モード（GPU不要）: `core/text_renderer.py`, `main_text.py`, メニュー選択肢追加
- アクセシビリティ対応: 色覚多様性 (`design_tokens.*`, `core/accessibility.py`), 難易度プリセット (`core/difficulty.py`, `config.yaml`), チュートリアル (`data/tutorial_steps.json`, `core/tutorial_controller.py`), 操作ガイドトグル, フォントスケール (`web_server.py`)
- ワンタッチ Web 起動＋モバイル対応: `web_server.py` の `launch_browser`, `--open` フラグ, バックグラウンド起動, レンダラ選択フォールバック (WebGL2→Canvas2D), タッチ/スワイプ/D-pad, レスポンシブ対応, 自動再接続, FPS ベース品質低下, ライトモードトグル

### Changed
- `TileAtlas._load()` now loads `tiny_rogue_16` metadata
- `TileRegistry.get_uv()` supports `tiny_rogue_16` scale with feature flag fallback
- `EntityRenderer._get_tile_id()` maps monster types to Tiny Rogue tiles
- `MonsterPreset.create()` stores `monster_type` for tile mapping
- `CombatSystem` publishes damage/kill/trap events for FX
- `FXManager` spawns blood, death animations, loot sparkles, flash effects
- `TileRegistry` supports autotile variants for Tiny Rogue floors/walls
- Dungeon generation assigns random floor variants (0-11) when feature flag enabled
- Parallax background rendering in `MapRenderer`
- Weather particle spawning using Tiny Rogue effect tiles
- UI icons rendered via Tiny Rogue tiles when feature flag enabled
- Screen flash on critical hits
- Ambient occlusion for wall tiles
- ゲーム本編の SDL 失敗フォールバック: テキストモード有効時はテキストモードへ自動切替
- web_server.py: /api/tokens エンドポイントに ?a11y= クエリ対応, /api/capabilities エンドポイント追加
- main.py: メニューにテキストモード起動オプション追加, アクセシビリティ選択画面追加, NAROU_FORCE_TEXT 環境変数対応

### Fixed
- Validation warnings for variant/frame counts are expected (atlas packing uses single-tile entries with animation handled via UV offsets)
- Feature flag fallback to standard tiles when disabled

## [v1.0.0] - 2026-08-20

### Added
- Initial release of Tiny Rogue Graphics Pack integration
- Complete asset pipeline from Kenney "Tiny Rogue" pack to in-game rendering
- Reusable atlas packing tool (`tools/pack_tiny_rogue_atlas.py`)
- Tile mapping configuration system (`data/tile_mappings/`)
- Integration test suite (`tests/integration/test_tiny_rogue_graphics.py`)
- Demo script (`demo_tiny_rogue_graphics.py`)