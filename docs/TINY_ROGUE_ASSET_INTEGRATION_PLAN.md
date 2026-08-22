<<<<<<< ours
# Tiny Rogue Asset Pack Integration Plan (72 Steps)

## Overview
Integrate the Kenney "Tiny Rogue" asset pack (downloaded at `E:\narou2\tiny rogue`) into the naRou engine to enrich graphics and immersion. The pack contains 132 individual tile PNGs + a tilemap atlas. Steps are atomic, ordered, and suitable for a low-performance LLM to execute sequentially.

---

## Phase 1 – Preparation & Inventory (Steps 1-8)

1. **Create working directory** `assets/tiles/tiny_rogue/` under the project.
2. **Copy all PNGs** from `E:\narou2\tiny rogue\Tiles\` → `assets/tiles/tiny_rogue/tiles/`.
3. **Copy tilemap atlases** (`tilemap.png`, `tilemap_packed.png`) → `assets/tiles/tiny_rogue/`.
4. **Read `Tilesheet.txt`** to understand tile naming / indexing; save as `assets/tiles/tiny_rogue/Tilesheet.txt`.
5. **Generate a CSV manifest** `tiny_rogue_manifest.csv` with columns: `index, filename, suggested_id, category` (floor, wall, decor, monster, item, effect, ui).
6. **Categorize tiles** manually (or via simple script) into: terrain (floor/wall), decorations, monsters, items, effects, UI.
7. **Decide target atlas scale** – use 16×16 to match existing `tileset_16x16.png`.
8. **Backup current atlas files** (`tileset_16x16.png`, `tileset_16x16.json`, `tileset_def.json`) before modification.

---

## Phase 2 – Atlas Construction (Steps 9-20)

9. **Write a small packing script** `tools/pack_tiny_rogue_atlas.py` that:
   - Loads all PNGs from `assets/tiles/tiny_rogue/tiles/`.
   - Packs them into a single 1024×1024 (or 2048×2048) atlas using a simple shelf/rect-pack algorithm.
   - Outputs `assets/tiles/tiny_rogue_atlas_16x16.png` and `assets/tiles/tiny_rogue_atlas_16x16.json` (metadata with x, y, width, height, variants=1, animated=false, frames=1, directions=1).
10. **Run the packing script** and verify the atlas PNG looks correct.
11. **Add new scale entry** `"tiny_rogue_16"` to `TileAtlas._load()` so it loads `tileset_tiny_rogue_16x16.json` when requested.
12. **Update `tileset_def.json`** – add a new top-level key `"tiny_rogue_tiles": { ... }` (or extend `"tiles"` object) with one `TileDef` per logical tile (e.g., `TR_FLOOR_01`, `TR_WALL_01`, `TR_MONSTER_GOBLIN`, `TR_ITEM_POTION_RED`, …). Each def references `file` key from the new atlas metadata.
13. **For animated tiles** (if any in Tilesheet.txt indicate animation), set `animated: true`, `frames`, `fps` accordingly.
14. **For directional monsters** (4-dir), set `directions: 4` and ensure atlas metadata has vertical stacks (height * 4).
15. **Run validation** `python tools/validate_tileset_def.py` – fix errors/warnings.
16. **Add autotile definitions** for floor/wall variants if the pack provides 16 variants; set `autotile: true`, `variants: 16`.
17. **Create 32×32 and 64×64 atlas variants** by up-scaling the 16×16 atlas (nearest-neighbor) and generating matching JSON (or skip if not needed).
18. **Update `TileAtlas` default scale fallback** to include `"tiny_rogue_16"` as an optional scale.
19. **Add unit test** `tests/test_tiny_rogue_atlas.py` that loads a few tile IDs and asserts UVs are valid.
20. **Commit atlas assets** to git (or at least stage them).

---

## Phase 3 – Engine Integration (Steps 21-36)

21. **Extend `EntityRenderer._get_tile_id()`** to map new monster/item types to the new `TR_*` tile IDs.
22. **Add a data table** `data/tile_mappings/tiny_rogue.yaml` mapping entity prototypes → `TR_*` tile IDs.
23. **Modify entity spawning code** (e.g., `entity_manager.py` or `map_engine.py`) to read the mapping table and assign `tile_id` on creation.
24. **Update `TileAtlas.get_uv()`** to gracefully fall back to `"16"` scale if `"tiny_rogue_16"` metadata missing.
25. **Add a feature flag** `ENABLE_TINY_ROGUE_GFX` in `feature_flags.py` to toggle the new graphics.
26. **Wrap new tile IDs** behind the feature flag in `EntityRenderer._get_tile_id()`.
27. **Test player sprite** – ensure `PLAYER` still works (unchanged) and new tiles don't clash.
28. **Test a monster** – spawn a goblin using `TR_MONSTER_GOBLIN` and verify animation, direction, idle/walk/attack states.
29. **Test an item** – drop a potion using `TR_ITEM_POTION_RED`; verify rendering on ground and in inventory.
30. **Test decoration** – place a torch `TR_DECOR_TORCH` and confirm animated idle.
31. **Verify autotiling** – generate a dungeon floor/wall using new `TR_FLOOR_01` / `TR_WALL_01` and check 4-bit transitions.
32. **Profile render performance** – ensure FPS unchanged (atlas is single texture).
33. **Fix any UV bleeding** – add 1-pixel padding in packing script if needed; regenerate atlas.
34. **Add mip-map / anisotropic filtering** toggle in `TileAtlas` init (optional).
35. **Document new tile IDs** in `docs/ASSET_TILE_IDS.md`.
36. **Run full validation suite** (`pytest tools/validate_tileset_def.py` and existing tests).

---

## Phase 4 – Polish & Immersion (Steps 37-54)

37. **Add particle effects** using new effect tiles (`TR_EFFECT_*`) in `fx_manager.py`.
38. **Hook blood splatter** (`TR_DECOR_BLOOD`) into combat damage numbers.
39. **Replace UI icons** (health, mana, gold) with `TR_UI_*` tiles via `ui_fx_systems.py`.
40. **Add screen-shake / flash** on critical hits using new effect tiles.
41. **Implement dynamic lighting color tint** for new tiles (reuse `DynamicLighting.calculate_tile_lighting`).
42. **Add ambient occlusion** for wall tiles by sampling neighbor mask (autotile variant).
43. **Create parallax background layers** from larger tilemap pieces (`tilemap_packed.png`).
44. **Add weather overlay** (rain/snow) using semi-transparent `TR_EFFECT_RAIN` tiles.
45. **Implement tile variant randomization** for floor/ground to reduce repetition.
46. **Add footstep particle puffs** matching floor tile type.
47. **Hook death animation** – play `TR_MONSTER_*_DEAD` frame then fade.
48. **Add loot sparkle** on item drop using `TR_EFFECT_SPARKLE`.
49. **Implement tile-based sound mapping** (optional) – associate each `TR_*` with a sound key.
50. **Create a "graphics settings" menu** entry to toggle Tiny Rogue graphics on/off.
51. **Add language-agnostic tile names** in `Tilesheet.txt` for localisation.
52. **Write a migration script** to convert existing save files' tile IDs to new ones (if any).
53. **Test on low-end hardware** – verify VRAM < 64 MB, FPS ≥ 60.
54. **Update README / CONTRIBUTING** with instructions for adding future Kenney packs.

---

## Phase 5 – QA, Documentation & Release (Steps 55-72)

55. **Write integration test** `tests/integration/test_tiny_rogue_graphics.py` covering spawn→render→animate→despawn cycle.
56. **Run full test suite** (`pytest -x`) – ensure zero regressions.
57. **Generate visual regression screenshots** (headless tcod) for CI.
58. **Create a demo script** `demo_tiny_rogue_graphics.py` showcasing all new tiles.
59. **Record a short GIF** for the project README.
60. **Write a changelog entry** `CHANGELOG.md` under "vX.Y.Z – Tiny Rogue Graphics Pack".
61. **Tag the commit** `gfx/tiny-rogue-integration`.
62. **Prepare a PR description** with before/after screenshots.
63. **Request code review** from at least one other contributor.
64. **Address review comments** (max 2 iteration cycles).
65. **Merge to main** and delete feature branch.
66. **Deploy updated build** to `dist/` or itch.io / Steam branch.
67. **Monitor crash reports** for 48 h post-release.
68. **Hot-fix any critical bugs** (texture missing, UV errors).
69. **Write a post-mortem / lessons-learned** note in `docs/POSTMORTEM_TINY_ROGUE.md`.
70. **Plan next asset pack integration** (e.g., Kenney "Micro Rogue") using the same pipeline.
71. **Refactor packing script** into a reusable CLI `tools/atlas_packer.py` for future packs.
72. **Celebrate** – the game now looks richer and more immersive!

---

## Execution Notes
- Each step should be a single commit with a clear message (`feat: step 12 – add TR_* tile defs`).
- Keep PRs ≤ 300 lines changed per step where possible.
- If a step blocks, create a sub-issue and continue with independent steps.
- Use `git stash` / `git worktree` for parallel experimentation.
=======
# Tiny Rogue Asset Pack Integration Plan (72 Steps)

## Overview
Integrate the Kenney "Tiny Rogue" asset pack (downloaded at `E:\narou2\tiny rogue`) into the naRou engine to enrich graphics and immersion. The pack contains 132 individual tile PNGs + a tilemap atlas. Steps are atomic, ordered, and suitable for a low-performance LLM to execute sequentially.

---

## Phase 1 – Preparation & Inventory (Steps 1-8)

1. **Create working directory** `assets/tiles/tiny_rogue/` under the project.
2. **Copy all PNGs** from `E:\narou2\tiny rogue\Tiles\` → `assets/tiles/tiny_rogue/tiles/`.
3. **Copy tilemap atlases** (`tilemap.png`, `tilemap_packed.png`) → `assets/tiles/tiny_rogue/`.
4. **Read `Tilesheet.txt`** to understand tile naming / indexing; save as `assets/tiles/tiny_rogue/Tilesheet.txt`.
5. **Generate a CSV manifest** `tiny_rogue_manifest.csv` with columns: `index, filename, suggested_id, category` (floor, wall, decor, monster, item, effect, ui).
6. **Categorize tiles** manually (or via simple script) into: terrain (floor/wall), decorations, monsters, items, effects, UI.
7. **Decide target atlas scale** – use 16×16 to match existing `tileset_16x16.png`.
8. **Backup current atlas files** (`tileset_16x16.png`, `tileset_16x16.json`, `tileset_def.json`) before modification.

---

## Phase 2 – Atlas Construction (Steps 9-20)

9. **Write a small packing script** `tools/pack_tiny_rogue_atlas.py` that:
   - Loads all PNGs from `assets/tiles/tiny_rogue/tiles/`.
   - Packs them into a single 1024×1024 (or 2048×2048) atlas using a simple shelf/rect-pack algorithm.
   - Outputs `assets/tiles/tiny_rogue_atlas_16x16.png` and `assets/tiles/tiny_rogue_atlas_16x16.json` (metadata with x, y, width, height, variants=1, animated=false, frames=1, directions=1).
10. **Run the packing script** and verify the atlas PNG looks correct.
11. **Add new scale entry** `"tiny_rogue_16"` to `TileAtlas._load()` so it loads `tileset_tiny_rogue_16x16.json` when requested.
12. **Update `tileset_def.json`** – add a new top-level key `"tiny_rogue_tiles": { ... }` (or extend `"tiles"` object) with one `TileDef` per logical tile (e.g., `TR_FLOOR_01`, `TR_WALL_01`, `TR_MONSTER_GOBLIN`, `TR_ITEM_POTION_RED`, …). Each def references `file` key from the new atlas metadata.
13. **For animated tiles** (if any in Tilesheet.txt indicate animation), set `animated: true`, `frames`, `fps` accordingly.
14. **For directional monsters** (4-dir), set `directions: 4` and ensure atlas metadata has vertical stacks (height * 4).
15. **Run validation** `python tools/validate_tileset_def.py` – fix errors/warnings.
16. **Add autotile definitions** for floor/wall variants if the pack provides 16 variants; set `autotile: true`, `variants: 16`.
17. **Create 32×32 and 64×64 atlas variants** by up-scaling the 16×16 atlas (nearest-neighbor) and generating matching JSON (or skip if not needed).
18. **Update `TileAtlas` default scale fallback** to include `"tiny_rogue_16"` as an optional scale.
19. **Add unit test** `tests/test_tiny_rogue_atlas.py` that loads a few tile IDs and asserts UVs are valid.
20. **Commit atlas assets** to git (or at least stage them).

---

## Phase 3 – Engine Integration (Steps 21-36)

21. **Extend `EntityRenderer._get_tile_id()`** to map new monster/item types to the new `TR_*` tile IDs.
22. **Add a data table** `data/tile_mappings/tiny_rogue.yaml` mapping entity prototypes → `TR_*` tile IDs.
23. **Modify entity spawning code** (e.g., `entity_manager.py` or `map_engine.py`) to read the mapping table and assign `tile_id` on creation.
24. **Update `TileAtlas.get_uv()`** to gracefully fall back to `"16"` scale if `"tiny_rogue_16"` metadata missing.
25. **Add a feature flag** `ENABLE_TINY_ROGUE_GFX` in `feature_flags.py` to toggle the new graphics.
26. **Wrap new tile IDs** behind the feature flag in `EntityRenderer._get_tile_id()`.
27. **Test player sprite** – ensure `PLAYER` still works (unchanged) and new tiles don't clash.
28. **Test a monster** – spawn a goblin using `TR_MONSTER_GOBLIN` and verify animation, direction, idle/walk/attack states.
29. **Test an item** – drop a potion using `TR_ITEM_POTION_RED`; verify rendering on ground and in inventory.
30. **Test decoration** – place a torch `TR_DECOR_TORCH` and confirm animated idle.
31. **Verify autotiling** – generate a dungeon floor/wall using new `TR_FLOOR_01` / `TR_WALL_01` and check 4-bit transitions.
32. **Profile render performance** – ensure FPS unchanged (atlas is single texture).
33. **Fix any UV bleeding** – add 1-pixel padding in packing script if needed; regenerate atlas.
34. **Add mip-map / anisotropic filtering** toggle in `TileAtlas` init (optional).
35. **Document new tile IDs** in `docs/ASSET_TILE_IDS.md`.
36. **Run full validation suite** (`pytest tools/validate_tileset_def.py` and existing tests).

---

## Phase 4 – Polish & Immersion (Steps 37-54)

37. **Add particle effects** using new effect tiles (`TR_EFFECT_*`) in `fx_manager.py`.
38. **Hook blood splatter** (`TR_DECOR_BLOOD`) into combat damage numbers.
39. **Replace UI icons** (health, mana, gold) with `TR_UI_*` tiles via `ui_fx_systems.py`.
40. **Add screen-shake / flash** on critical hits using new effect tiles.
41. **Implement dynamic lighting color tint** for new tiles (reuse `DynamicLighting.calculate_tile_lighting`).
42. **Add ambient occlusion** for wall tiles by sampling neighbor mask (autotile variant).
43. **Create parallax background layers** from larger tilemap pieces (`tilemap_packed.png`).
44. **Add weather overlay** (rain/snow) using semi-transparent `TR_EFFECT_RAIN` tiles.
45. **Implement tile variant randomization** for floor/ground to reduce repetition.
46. **Add footstep particle puffs** matching floor tile type.
47. **Hook death animation** – play `TR_MONSTER_*_DEAD` frame then fade.
48. **Add loot sparkle** on item drop using `TR_EFFECT_SPARKLE`.
49. **Implement tile-based sound mapping** (optional) – associate each `TR_*` with a sound key.
50. **Create a "graphics settings" menu** entry to toggle Tiny Rogue graphics on/off.
51. **Add language-agnostic tile names** in `Tilesheet.txt` for localisation.
52. **Write a migration script** to convert existing save files' tile IDs to new ones (if any).
53. **Test on low-end hardware** – verify VRAM < 64 MB, FPS ≥ 60.
54. **Update README / CONTRIBUTING** with instructions for adding future Kenney packs.

---

## Phase 5 – QA, Documentation & Release (Steps 55-72)

55. **Write integration test** `tests/integration/test_tiny_rogue_graphics.py` covering spawn→render→animate→despawn cycle.
56. **Run full test suite** (`pytest -x`) – ensure zero regressions.
57. **Generate visual regression screenshots** (headless tcod) for CI.
58. **Create a demo script** `demo_tiny_rogue_graphics.py` showcasing all new tiles.
59. **Record a short GIF** for the project README.
60. **Write a changelog entry** `CHANGELOG.md` under "vX.Y.Z – Tiny Rogue Graphics Pack".
61. **Tag the commit** `gfx/tiny-rogue-integration`.
62. **Prepare a PR description** with before/after screenshots.
63. **Request code review** from at least one other contributor.
64. **Address review comments** (max 2 iteration cycles).
65. **Merge to main** and delete feature branch.
66. **Deploy updated build** to `dist/` or itch.io / Steam branch.
67. **Monitor crash reports** for 48 h post-release.
68. **Hot-fix any critical bugs** (texture missing, UV errors).
69. **Write a post-mortem / lessons-learned** note in `docs/POSTMORTEM_TINY_ROGUE.md`.
70. **Plan next asset pack integration** (e.g., Kenney "Micro Rogue") using the same pipeline.
71. **Refactor packing script** into a reusable CLI `tools/atlas_packer.py` for future packs.
72. **Celebrate** – the game now looks richer and more immersive!

---

## Execution Notes
- Each step should be a single commit with a clear message (`feat: step 12 – add TR_* tile defs`).
- Keep PRs ≤ 300 lines changed per step where possible.
- If a step blocks, create a sub-issue and continue with independent steps.
- Use `git stash` / `git worktree` for parallel experimentation.
>>>>>>> theirs
- All scripts must be pure Python 3.10+, no external deps beyond `Pillow` for packing.
