# Unused Tools Audit (Step 59)

A heuristic scan (`grep` for `tools.<name>`, `import <name>`, etc.) flagged the
following modules as *candidates* for removal. **None were deleted** because the
heuristic produces false positives (e.g. test files and directly-invoked
scripts do not show up as imports).

Each entry below MUST be manually reviewed before deletion:

- analyze_assets, animation_interpolator, asset_quality_filter, atlas_packer
- backup_assets, build_appimage, build_assets, build_wasm, check_tilemap
- cleanup_assets, codegen, convert_demos_to_template, convert_sounds
- create_placeholder_sources, deploy_assets, docs_assets, gemini_asset_generator
- generate_colorblind_palettes, generate_font_atlas, generate_normal_atlas
- generate_palette, generate_theme, generate_tileset_atlas
- generate_tiny_rogue_defs, generate_tiny_rogue_manifest, gen_checksums
- inventory_emote, log_assets, monitor_assets, optimize_assets, optimize_models
- pack_tiny_rogue_atlas, palette_unifier, performance_validator
- rebuild_tileset_def, replace_classes, restore_assets, test_assets
- test_attack_anim, test_entity_parity, test_fx_manager, test_guild_systems
- test_lighting, test_palette_parity, test_particles, test_passive_skills
- test_pet_systems, test_seasonal_systems, test_skill_inheritance
- test_skill_synergy_ui, test_tile_parity, test_tiny_rogue_tiles
- tiled_to_game, tokens_to_css, validate_tileset_def

## Recommendation
Wire genuinely-useful tools into `tools/cli.py` (see Step 53) instead of
deleting. Delete only after confirming no `run.py` / Makefile / CI reference
exists for each name.
