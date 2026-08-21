#!/usr/bin/env python3
"""
Create simple colored placeholder PNG files for asset source.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw


def create_placeholder_image(color, size=(16, 16), filename=None):
    """Create a simple colored placeholder image."""
    img = Image.new("RGBA", size, color)
    draw = ImageDraw.Draw(img)

    # Add a simple pattern to make it more interesting than a solid color
    if size[0] >= 8 and size[1] >= 8:
        # Draw a smaller square in the center
        inner_size = (size[0] // 2, size[1] // 2)
        inner_pos = ((size[0] - inner_size[0]) // 2, (size[1] - inner_size[1]) // 2)
        inner_color = tuple(min(255, c + 30) for c in color[:3]) + (
            color[3] if len(color) == 4 else 255,
        )
        draw.rectangle(
            [inner_pos, (inner_pos[0] + inner_size[0], inner_pos[1] + inner_size[1])],
            fill=inner_color,
        )

    if filename:
        img.save(filename)
        print(f"Created {filename}")
    return img


def main():
    """Create placeholder images for all needed assets."""
    # Create directories
    os.makedirs("assets/source/terrain", exist_ok=True)
    os.makedirs("assets/source/entities", exist_ok=True)
    os.makedirs("assets/source/objects", exist_ok=True)
    os.makedirs("assets/source/effects", exist_ok=True)

    # Define colors for different asset types
    terrain_colors = [
        (101, 67, 33, 255),  # Brown - floor
        (85, 85, 85, 255),  # Gray - wall
        (30, 144, 255, 255),  # Blue - water
        (139, 69, 19, 255),  # Saddle brown - stairs
        (255, 69, 0, 255),  # Red-orange - trap
    ]

    entity_colors = [
        (220, 20, 60, 255),  # Crimson - player
        (34, 139, 34, 255),  # Forest green - pet
        (0, 100, 0, 255),  # Dark green - enemy
    ]

    object_colors = [
        (255, 215, 0, 255),  # Gold - item_gold
        (255, 0, 0, 255),  # Red - item_potion
        (192, 192, 192, 255),  # Silver - item_weapon
        (70, 130, 180, 255),  # Steel blue - item_armor
    ]

    effect_colors = [
        (255, 69, 0, 255),  # Red-orange - torch
        (220, 20, 60, 255),  # Crimson - blood_splat
        (30, 144, 255, 255),  # Blue - magic_cast
    ]

    # Create terrain images
    terrain_names = [
        "floor_dungeon",
        "wall_dungeon",
        "water",
        "stairs_down",
        "stairs_up",
        "trap",
    ]
    for i, name in enumerate(terrain_names):
        color = terrain_colors[i % len(terrain_colors)]
        create_placeholder_image(color, (16, 16), f"assets/source/terrain/{name}.png")

    # Create entity images
    entity_names = ["player", "enemy_goblin", "pet"]
    for i, name in enumerate(entity_names):
        color = entity_colors[i % len(entity_colors)]
        create_placeholder_image(color, (16, 16), f"assets/source/entities/{name}.png")

    # Create object images
    object_names = ["item_gold", "item_potion", "item_weapon", "item_armor"]
    for i, name in enumerate(object_names):
        color = object_colors[i % len(object_colors)]
        create_placeholder_image(color, (16, 16), f"assets/source/objects/{name}.png")

    # Create effect images
    effect_names = ["torch", "blood_splat", "magic_cast"]
    for i, name in enumerate(effect_names):
        color = effect_colors[i % len(effect_colors)]
        create_placeholder_image(color, (16, 16), f"assets/source/effects/{name}.png")

    print("All placeholder source images created!")


if __name__ == "__main__":
    main()
