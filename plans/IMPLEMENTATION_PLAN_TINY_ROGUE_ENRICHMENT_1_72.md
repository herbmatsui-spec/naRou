# Implementation Plan: Tiny Rogue / Audio / Emote Asset Pack Enrichment (Steps 1-72)

> Goal: Use the downloaded `tiny rogue`, `audio`, and `emote` asset packs to make graphics richer
> and increase immersion. Every step is small and self-contained so a low-performance LLM can
> implement it one at a time and verify before moving on.

## Conventions
- New feature flags go in `feature_flags.py`.
- Real audio playback is gated behind `ENABLE_AUDIO_PACK` (add `pygame` or `simpleaudio` to requirements).
- All new assets live under `assets/audio/`, `assets/emote/`, `assets/tiles/`.
- After each phase, run `python tools/validate_tileset_def.py` and `python tools/validate_assets.py`.

---

## PHASE 1 - Foundation & Asset Import (Steps 1-15)

1. Create directory `assets/audio/` (mkdir).
2. Create directory `assets/emote/` (mkdir).
3. Copy all 51 OGG files from `audio/Audio/` into `assets/audio/` (flat copy).
4. Create `assets/emote/pixel/style1/` and copy `emote/PNG/Pixel/Style 1/*.png` into it.
5. Create `assets/emote/pixel/style2/` and copy `emote/PNG/Pixel/Style 2/*.png`.
6. Create `assets/emote/pixel/style3/` and copy `emote/PNG/Pixel/Style 3/*.png`.
7. Create `assets/emote/pixel/style4/` and copy `emote/PNG/Pixel/Style 4/*.png`.
8. Create `assets/emote/pixel/style5/` and copy `emote/PNG/Pixel/Style 5/*.png`.
9. Create `assets/emote/pixel/style6/` and copy `emote/PNG/Pixel/Style 6/*.png`.
10. Create `assets/emote/pixel/style7/` and copy `emote/PNG/Pixel/Style 7/*.png`.
11. Create `assets/emote/pixel/style8/` and copy `emote/PNG/Pixel/Style 8/*.png`.
12. Copy all `emote/Spritesheets/*.png` into `assets/emote/spritesheets/`.
13. Copy all `emote/Tilesheets/*.png` into `assets/emote/tilesheets/`.
14. Copy `emote/Vector/emotes_vector.svg` into `assets/emote/vector/`.
15. Create `assets/audio/manifest.csv` with columns: `filename,category,suggested_id`
    (category in: bgm, ambient, se, ui). Fill from the 51 OGG names heuristically.

## PHASE 2 - Graphics Integration (Steps 16-30)

16. Create `tools/inventory_emote.py` that prints all emote PNG paths grouped by style.
17. Extend `assets/tiles/tiny_rogue/tiny_rogue_manifest.csv` to include the 27 unused tiles
    (tile_0105..tile_0131 not yet packed) with new suggested ids.
18. Re-run `tools/atlas_packer.py` to pack all 132 tiles -> `tileset_tiny_rogue_full_16x16.png`.
19. Add the new tile ids (`TR_FLOOR_13..`, `TR_DECOR_*`, etc.) to `tileset_def.json`.
20. Extend `core/tiny_rogue_tiles.py`: add `get_extra_floor_id`, `get_extra_wall_id`,
    `get_extra_decor_id` helpers (flag-aware).
21. Update `data/tile_mappings/` YAMLs to map new decoration tiles to room themes.
22. Create `core/animated_tile.py` with class `AnimatedTile(tile_ids: list, fps: int)`.
23. Define water/lava animated tiles using emote spritesheet frames in `core/animated_tile.py`.
24. In `core/tile_atlas.py`, when flag on, register animated tiles from `AnimatedTile` defs.
25. Extend `fx_manager.py`: add particle types using new `TR_EFFECT_*` tiles for richer FX.
26. Add `fx_manager.py` methods `spawn_water_splash(x,y)` and `spawn_lava_bubble(x,y)`.
27. Extend `entity_renderer.py` to allow new monster types to use new `TR_MONSTER_*` frames.
28. In `map_engine.py`, assign extra `TR_DECOR` variants during dungeon generation.
29. Create `tests/unit/test_animated_tile.py` asserting frame cycling works.
30. Run `python tools/validate_tileset_def.py` and confirm all 132 tiles valid.

## PHASE 3 - Audio Integration (Steps 31-45)

31. Add `pygame` (or `simpleaudio`) to `requirements.txt`, guarded by `ENABLE_AUDIO_PACK`.
32. Create `audio/backend.py` wrapper that loads/plays OGG via chosen backend.
33. Add `ENABLE_AUDIO_PACK` flag (default False) to `feature_flags.py`.
34. Extend `sound_manager.py`: load OGG files from `assets/audio/` into a cache dict.
35. Add `se:` section to `data/audio_config.yaml` mapping se_type -> ogg filename.
36. Implement `SoundManager.play_se_ogg(se_type)` using the backend (threaded).
37. Add footstep categories `footstep_stone/grass/wood/metal` mapping to OGGs in config.
38. Create `systems/footstep_audio.py` that picks sound by current terrain type.
39. Hook footstep audio into player-move logic in `game.py` (call on successful step).
40. Extend `AmbientLayer` to loop real OGG ambient files instead of dummy strings.
41. Add depth-based ambient selection (dungeon floor N -> ambient variant) in config+layer.
42. Add `bgm:` track entries referencing OGG files in `data/audio_config.yaml`.
43. Create `audio/bgm_player.py` to cross-fade OGG BGM tracks.
44. Hook BGM/ambient switching into scene transitions (town/dungeon/forest).
45. Trigger UI sounds (click/hover/notify) via OGG in `uirenderer.py` event handlers.

## PHASE 4 - Emote & UI Integration (Steps 46-60)

46. Create `core/emote_manager.py` to load emote sprites by (style, expression).
47. Build emote id mapping dict: (style, expression) -> file path; expose `get_emote(...)`.
48. Create `ui/emote_overlay.py` to render a temporary emote sprite above an entity.
49. Add API `show_emote(entity, expression, duration_frames)` to `emote_manager` / overlay.
50. Hook emotes to events: level_up (star), quest_complete (happy), damage (angry), heal (heart).
51. Create `ui/status_indicator.py` using emote sprites for buff/debuff icons.
52. Render status indicators in `uirenderer.py` / `ui_fx_systems.py` when flag on.
53. On achievement unlock, show random celebration emote + `spawn_sparkle_effect`.
54. During NPC dialogue, show face emote overlay from `emote_manager`.
55. Copy emote tilesheet frames as new UI icons into `tileset_def.json` (`TR_UI_*`).
56. Add extra `TR_UI_*` icon ids (heart/mana/coin/key/sword/shield/potion) from emote tiles.
57. Update `uirenderer.py` to draw new UI icons when `ENABLE_TINY_ROGUE_GFX` is on.
58. Add minimap icon variants using emote sprites in `map_renderer.py`.
59. Create `tests/unit/test_emote_manager.py` asserting loader returns valid paths.
60. Create `tests/integration/test_emote_ui.py` exercising show_emote + status indicators.

## PHASE 5 - Polish, Testing & Documentation (Steps 61-72)

61. Create `demo_asset_pack_showcase.py` combining graphics + audio + emote features.
62. Add headless integration test that runs the demo without crashing.
63. Run `python tools/validate_assets.py` for all new audio/emote/tile assets.
64. Update `CHANGELOG.md` with the three new asset-pack integrations.
65. Write `docs/ASSET_PACK_ENRICHMENT.md` usage/configuration guide.
66. Add feature-flag defaults (per-pack enable/disable) to `config.yaml`.
67. Performance check: measure atlas load time and audio memory; log warnings if high.
68. Add graceful fallback when an asset file is missing (use placeholder / no sound).
69. Create `tools/repack_all.py` to rebuild every atlas from manifests in one command.
70. Add a CI step (or pre-commit hook) verifying asset manifest consistency.
71. Write manual QA checklist in `docs/ASSET_PACK_QA_CHECKLIST.md`.
72. Final review pass: ensure flags toggle cleanly; prepare commit message draft.

---

## Verification per Phase
- Phase 1: `ls assets/audio assets/emote` shows copied files; manifest.csv non-empty.
- Phase 2: `validate_tileset_def.py` passes with 132 tiles; animated_tile unit test green.
- Phase 3: `SoundManager` plays an OGG without error when flag enabled; config loads.
- Phase 4: `test_emote_manager.py` + `test_emote_ui.py` green; demo shows emotes.
- Phase 5: `demo_asset_pack_showcase.py` runs; changelog/docs updated; CI check passes.
