#!/usr/bin/env python3
"""
Generate tiny_rogue_manifest.csv from the tile PNGs.
"""
import csv
from pathlib import Path

tiles_dir = Path("assets/tiles/tiny_rogue/tiles")
output_csv = Path("assets/tiles/tiny_rogue/tiny_rogue_manifest.csv")

# Kenney Tiny Rogue typical layout (12 cols x 11 rows = 132 tiles)
# Based on common Kenney packs, we categorize by index ranges:
# Row 0 (0-11): floors
# Row 1 (12-23): walls
# Row 2 (24-35): wall variants / corners
# Row 3 (36-47): decorations (torches, chests, etc.)
# Row 4 (48-59): items (potions, weapons, armor, gold)
# Row 5 (60-71): monsters (goblin, slime, skeleton, etc.)
# Row 6 (72-83): monster variants / bosses
# Row 7 (84-95): effects (magic, blood, explosions)
# Row 8 (96-107): UI icons (hearts, mana, keys)
# Row 9 (108-119): player / NPC sprites (4-dir * frames)
# Row 10 (120-131): misc / extra

category_map = {}
for i in range(132):
    row = i // 12
    col = i % 12
    if row == 0:
        cat = "floor"
        suggested = f"TR_FLOOR_{col+1:02d}"
    elif row == 1:
        cat = "wall"
        suggested = f"TR_WALL_{col+1:02d}"
    elif row == 2:
        cat = "wall_variant"
        suggested = f"TR_WALL_VAR_{col+1:02d}"
    elif row == 3:
        cat = "decoration"
        suggested = f"TR_DECOR_{col+1:02d}"
    elif row == 4:
        cat = "item"
        suggested = f"TR_ITEM_{col+1:02d}"
    elif row == 5:
        cat = "monster"
        suggested = f"TR_MONSTER_{col+1:02d}"
    elif row == 6:
        cat = "monster_variant"
        suggested = f"TR_MONSTER_VAR_{col+1:02d}"
    elif row == 7:
        cat = "effect"
        suggested = f"TR_EFFECT_{col+1:02d}"
    elif row == 8:
        cat = "ui"
        suggested = f"TR_UI_{col+1:02d}"
    elif row == 9:
        cat = "player_npc"
        suggested = f"TR_PLAYER_{col+1:02d}"
    else:
        cat = "misc"
        suggested = f"TR_MISC_{col+1:02d}"
    category_map[i] = (cat, suggested)

rows = []
for i in range(132):
    filename = f"tile_{i:04d}.png"
    cat, suggested = category_map[i]
    rows.append([i, filename, suggested, cat])

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["index", "filename", "suggested_id", "category"])
    writer.writerows(rows)

print(f"Generated {output_csv} with {len(rows)} entries")