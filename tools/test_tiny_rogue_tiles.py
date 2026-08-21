from __future__ import annotations

from feature_flags import set_flag

set_flag("ENABLE_TINY_ROGUE_GFX", True)

from core.tiny_rogue_tiles import (
    get_decoration_tile_id,
    get_dungeon_tile_id,
    get_effect_tile_id,
    get_item_tile_id,
    get_terrain_config,
    get_ui_tile_id,
)

print("Dungeon tiles:")
for t in ["floor", "wall", "stairs_up", "stairs_down", "water", "trap", "wall_variant"]:
    print(f"  {t}: {get_dungeon_tile_id(t)}")

print()
print("Item tiles:")
for c in ["potion", "scroll", "weapon", "armor", "gold", "food", "default"]:
    print(f"  {c}: {get_item_tile_id(c)}")

print()
print("Decoration tiles:")
for d in ["torch", "chest", "altar", "fountain", "trap", "blood"]:
    print(f"  {d}: {get_decoration_tile_id(d)}")

print()
print("Effect tiles:")
for e in ["magic_cast", "fire", "heal", "sparkle"]:
    print(f"  {e}: {get_effect_tile_id(e)}")

print()
print("UI tiles:")
for u in ["heart", "mana", "coin", "sword_icon"]:
    print(f"  {u}: {get_ui_tile_id(u)}")

print()
print("Terrain config:", get_terrain_config())

# Test with feature flag disabled
set_flag("ENABLE_TINY_ROGUE_GFX", False)
print()
print("With feature flag DISABLED:")
print("  floor: {}".format(get_dungeon_tile_id("floor")))
print("  potion: {}".format(get_item_tile_id("potion")))
