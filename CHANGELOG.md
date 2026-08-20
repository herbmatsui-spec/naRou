# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Tiny Rogue Graphics Pack integration (Kenney "Tiny Rogue" asset pack)
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