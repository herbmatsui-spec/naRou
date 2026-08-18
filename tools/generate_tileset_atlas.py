#!/usr/bin/env python3
"""
TexturePacker script for generating tileset atlases.
Supports 16x16 and 32x32 tile sizes with metadata generation.
Includes procedural effect generation for blood splatters, magic effects, and flame effects.
Includes procedural entity generation for players, enemies, and pets.
Includes procedural terrain generation for grass, dirt, water, and stone.
Includes procedural animation generation for walk, attack, and death animations.
"""

import os
import json
import argparse
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw


def load_tileset_definition(def_path: str) -> Dict:
    """Load tileset definition from JSON file."""
    with open(def_path, 'r') as f:
        return json.load(f)


def create_atlas(tiles: List[Image.Image], tile_size: int, padding: int = 1) -> Tuple[Image.Image, List[Dict]]:
    """Create an atlas from a list of tile images."""
    if not tiles:
        return Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0)), []
    
    cols = int(len(tiles) ** 0.5) + 1
    rows = (len(tiles) + cols - 1) // cols
    
    atlas_width = cols * (tile_size + padding) - padding
    atlas_height = rows * (tile_size + padding) - padding
    
    atlas = Image.new('RGBA', (atlas_width, atlas_height), (0, 0, 0, 0))
    metadata = []
    
    for idx, tile in enumerate(tiles):
        row = idx // cols
        col = idx % cols
        x = col * (tile_size + padding)
        y = row * (tile_size + padding)
        
        tile_resized = tile.resize((tile_size, tile_size), Image.NEAREST)
        atlas.paste(tile_resized, (x, y))
        
        u = x / atlas_width
        v = y / atlas_height
        uw = tile_size / atlas_width
        vh = tile_size / atlas_height
        
        metadata.append({
            'index': idx,
            'x': x,
            'y': y,
            'width': tile_size,
            'height': tile_size,
            'u': u,
            'v': v,
            'uw': uw,
            'vh': vh
        })
    
    return atlas, metadata


def generate_blood_splat_effect(tile_size: int) -> Image.Image:
    """Generate a blood splatter effect tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Blood color (dark red with some variation)
    blood_color = (139, 0, 0, 255)  # Dark red
    
    # Generate random splatter pattern
    center_x, center_y = tile_size // 2, tile_size // 2
    
    # Draw main splat blob
    main_radius = tile_size // 3
    draw.ellipse([
        center_x - main_radius, center_y - main_radius,
        center_x + main_radius, center_y + main_radius
    ], fill=blood_color)
    
    # Add smaller splatter blobs around the main one
    for _ in range(random.randint(3, 6)):
        blob_radius = random.randint(tile_size // 8, tile_size // 4)
        angle = random.uniform(0, 2 * math.pi)
        distance = random.randint(tile_size // 4, tile_size // 2)
        blob_x = center_x + int(distance * math.cos(angle))
        blob_y = center_y + int(distance * math.sin(angle))
        
        # Vary the blood color slightly
        color_var = random.randint(-20, 20)
        blob_color = (
            max(100, min(180, 139 + color_var)),
            max(0, min(50, 0 + color_var//2)),
            max(0, min(50, 0 + color_var//2)),
            255
        )
        
        draw.ellipse([
            blob_x - blob_radius, blob_y - blob_radius,
            blob_x + blob_radius, blob_y + blob_radius
        ], fill=blob_color)
    
    # Add some blood droplets
    for _ in range(random.randint(2, 5)):
        droplet_radius = random.randint(2, 5)
        angle = random.uniform(0, 2 * math.pi)
        distance = random.randint(tile_size // 3, tile_size // 2)
        droplet_x = center_x + int(distance * math.cos(angle))
        droplet_y = center_y + int(distance * math.sin(angle))
        
        droplet_color = (180, 0, 0, 200)  # Brighter red for droplets
        draw.ellipse([
            droplet_x - droplet_radius, droplet_y - droplet_radius,
            droplet_x + droplet_radius, droplet_y + droplet_radius
        ], fill=droplet_color)
    
    return img


def generate_magic_effect(tile_size: int) -> Image.Image:
    """Generate a magic effect tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Magic color (purple/blue with alpha)
    magic_color = (138, 43, 226, 180)  # Blue violet with transparency
    
    center_x, center_y = tile_size // 2, tile_size // 2
    
    # Draw a starburst/magic effect
    num_points = 8
    outer_radius = tile_size // 2 - 2
    inner_radius = tile_size // 4
    
    points = []
    for i in range(num_points * 2):
        angle = i * math.pi / num_points
        if i % 2 == 0:
            # Outer point
            radius = outer_radius
        else:
            # Inner point
            radius = inner_radius
        
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        points.append((x, y))
    
    # Draw the starburst
    draw.polygon(points, fill=magic_color)
    
    # Add some sparkling particles
    for _ in range(random.randint(3, 8)):
        sparkle_x = random.randint(tile_size // 4, 3 * tile_size // 4)
        sparkle_y = random.randint(tile_size // 4, 3 * tile_size // 4)
        sparkle_size = random.randint(1, 3)
        sparkle_color = (255, 255, 255, 220)  # White sparkles
        
        draw.ellipse([
            sparkle_x - sparkle_size, sparkle_y - sparkle_size,
            sparkle_x + sparkle_size, sparkle_y + sparkle_size
        ], fill=sparkle_color)
    
    return img


def generate_flame_effect(tile_size: int) -> Image.Image:
    """Generate a flame/fire effect tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center_x, center_y = tile_size // 2, tile_size // 2
    
    # Draw flame shape using multiple overlapping ellipses with gradient colors
    flame_colors = [
        (255, 69, 0, 200),    # Orange red
        (255, 140, 0, 180),   # Dark orange
        (255, 165, 0, 160),   # Orange
        (255, 215, 0, 140),   # Gold
        (255, 255, 0, 120)    # Yellow
    ]
    
    # Draw flame layers from bottom to top
    for i, color in enumerate(flame_colors):
        # Flame gets narrower toward the top
        width_factor = 1.0 - (i * 0.15)
        height_factor = 1.0 - (i * 0.1)
        
        width = int(tile_size * 0.4 * width_factor)
        height = int(tile_size * 0.6 * height_factor)
        
        if width > 0 and height > 0:
            # Position the flame lick
            left = center_x - width // 2
            top = center_y - height // 2 + (i * 2)  # Offset upward for each layer
            
            draw.ellipse([
                left, top,
                left + width, top + height
            ], fill=color)
    
    # Add some upward sparks
    for _ in range(random.randint(2, 4)):
        spark_x = center_x + random.randint(-3, 3)
        spark_y = center_y - random.randint(5, 10)
        spark_size = random.randint(1, 2)
        spark_color = (255, 255, 255, 180)
        
        draw.ellipse([
            spark_x - spark_size, spark_y - spark_size,
            spark_x + spark_size, spark_y + spark_size
        ], fill=spark_color)
    
    return img


def generate_player_entity(tile_size: int) -> Image.Image:
    """Generate a simple player entity tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Player colors
    skin_color = (255, 220, 177, 255)  # Peach
    shirt_color = (30, 144, 255, 255)  # Dodger blue
    pants_color = (0, 0, 139, 255)     # Dark blue
    shoe_color = (105, 105, 105, 255)  # Dim gray
    hair_color = (139, 69, 19, 255)    # Saddle brown
    
    center_x = tile_size // 2
    
    # Draw head (circle)
    head_radius = tile_size // 6
    head_y = tile_size // 4
    draw.ellipse([
        center_x - head_radius, head_y - head_radius,
        center_x + head_radius, head_y + head_radius
    ], fill=skin_color)
    
    # Draw hair (simple triangle-ish shape on top of head)
    hair_points = [
        (center_x - head_radius, head_y - head_radius),
        (center_x, head_y - head_radius * 1.5),
        (center_x + head_radius, head_y - head_radius)
    ]
    draw.polygon(hair_points, fill=hair_color)
    
    # Draw body (rectangle)
    body_width = tile_size // 3
    body_height = tile_size // 3
    body_x = center_x - body_width // 2
    body_y = head_y + head_radius
    draw.rectangle([
        body_x, body_y,
        body_x + body_width, body_y + body_height
    ], fill=shirt_color)
    
    # Draw arms (rectangles)
    arm_width = tile_size // 8
    arm_length = tile_size // 3
    # Left arm
    draw.rectangle([
        body_x - arm_width, body_y + tile_size // 12,
        body_x, body_y + arm_length + tile_size // 12
    ], fill=shirt_color)
    # Right arm
    draw.rectangle([
        body_x + body_width, body_y + tile_size // 12,
        body_x + body_width + arm_width, body_y + arm_length + tile_size // 12
    ], fill=shirt_color)
    
    # Draw legs (rectangles)
    leg_width = tile_size // 4
    leg_height = tile_size // 3
    leg_top = body_y + body_height
    # Left leg
    draw.rectangle([
        body_x + body_width // 4, leg_top,
        body_x + body_width // 4 + leg_width, leg_top + leg_height
    ], fill=pants_color)
    # Right leg
    draw.rectangle([
        body_x + body_width // 2, leg_top,
        body_x + body_width // 2 + leg_width, leg_top + leg_height
    ], fill=pants_color)
    
    # Draw shoes (small rectangles)
    shoe_width = leg_width
    shoe_height = tile_size // 8
    shoe_top = leg_top + leg_height
    # Left shoe
    draw.rectangle([
        body_x + body_width // 4, shoe_top,
        body_x + body_width // 4 + shoe_width, shoe_top + shoe_height
    ], fill=shoe_color)
    # Right shoe
    draw.rectangle([
        body_x + body_width // 2, shoe_top,
        body_x + body_width // 2 + shoe_width, shoe_top + shoe_height
    ], fill=shoe_color)
    
    # Draw eyes (small black dots)
    eye_size = max(1, tile_size // 16)
    eye_y = head_y - tile_size // 12
    # Left eye
    draw.ellipse([
        center_x - tile_size // 6, eye_y - eye_size // 2,
        center_x - tile_size // 6 + eye_size, eye_y + eye_size // 2
    ], fill=(0, 0, 0, 255))
    # Right eye
    draw.ellipse([
        center_x + tile_size // 6 - eye_size, eye_y - eye_size // 2,
        center_x + tile_size // 6, eye_y + eye_size // 2
    ], fill=(0, 0, 0, 255))
    
    return img


def generate_enemy_entity(tile_size: int) -> Image.Image:
    """Generate a simple enemy entity tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Enemy colors
    skin_color = (0, 100, 0, 255)      # Dark green
    armor_color = (139, 69, 19, 255)   # Saddle brown
    weapon_color = (169, 169, 169, 255) # Dark gray
    eye_color = (255, 0, 0, 255)       # Red
    
    center_x = tile_size // 2
    
    # Draw head (circle, slightly larger than player)
    head_radius = tile_size // 5
    head_y = tile_size // 5
    draw.ellipse([
        center_x - head_radius, head_y - head_radius,
        center_x + head_radius, head_y + head_radius
    ], fill=skin_color)
    
    # Draw horns (triangles on top of head)
    horn_width = tile_size // 8
    horn_height = tile_size // 4
    # Left horn
    draw.polygon([
        (center_x - head_radius // 2, head_y - head_radius),
        (center_x - head_radius // 2 - horn_width // 2, head_y - head_radius - horn_height),
        (center_x - head_radius // 2 + horn_width // 2, head_y - head_radius - horn_height)
    ], fill=(50, 50, 50, 255))  # Dark gray horns
    # Right horn
    draw.polygon([
        (center_x + head_radius // 2, head_y - head_radius),
        (center_x + head_radius // 2 - horn_width // 2, head_y - head_radius - horn_height),
        (center_x + head_radius // 2 + horn_width // 2, head_y - head_radius - horn_height)
    ], fill=(50, 50, 50, 255))  # Dark gray horns
    
    # Draw body (rectangle, wider than player)
    body_width = tile_size // 2
    body_height = tile_size // 2
    body_x = center_x - body_width // 2
    body_y = head_y + head_radius
    draw.rectangle([
        body_x, body_y,
        body_x + body_width, body_y + body_height
    ], fill=armor_color)
    
    # Draw weapon (rectangle in right hand)
    weapon_width = tile_size // 8
    weapon_height = tile_size // 2
    weapon_x = body_x + body_width
    weapon_y = body_y + tile_size // 6
    draw.rectangle([
        weapon_x, weapon_y,
        weapon_x + weapon_width, weapon_y + weapon_height
    ], fill=weapon_color)
    
    # Draw legs (rectangles)
    leg_width = tile_size // 4
    leg_height = tile_size // 2
    leg_top = body_y + body_height
    # Left leg
    draw.rectangle([
        body_x + body_width // 4, leg_top,
        body_x + body_width // 4 + leg_width, leg_top + leg_height
    ], fill=armor_color)
    # Right leg
    draw.rectangle([
        body_x + body_width // 2, leg_top,
        body_x + body_width // 2 + leg_width, leg_top + leg_height
    ], fill=armor_color)
    
    # Draw eyes (glowing red)
    eye_size = max(2, tile_size // 12)
    eye_y = head_y - tile_size // 12
    # Left eye
    draw.ellipse([
        center_x - tile_size // 5, eye_y - eye_size // 2,
        center_x - tile_size // 5 + eye_size, eye_y + eye_size // 2
    ], fill=eye_color)
    # Right eye
    draw.ellipse([
        center_x + tile_size // 5 - eye_size, eye_y - eye_size // 2,
        center_x + tile_size // 5, eye_y + eye_size // 2
    ], fill=eye_color)
    
    return img


def generate_pet_entity(tile_size: int) -> Image.Image:
    """Generate a simple pet/animal entity tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Pet colors (brown dog-like creature)
    fur_color = (160, 82, 45, 255)     # Saddle brown
    belly_color = (222, 184, 135, 255) # Burlywood
    nose_color = (101, 67, 33, 255)    # Dark brown
    eye_color = (0, 0, 0, 255)         # Black
    
    center_x = tile_size // 2
    center_y = tile_size // 2
    
    # Draw body (oval)
    body_width = tile_size // 2
    body_height = tile_size // 3
    body_x = center_x - body_width // 2
    body_y = center_y - body_height // 2
    draw.ellipse([
        body_x, body_y,
        body_x + body_width, body_y + body_height
    ], fill=fur_color)
    
    # Draw belly (lighter oval on bottom)
    belly_width = body_width * 0.8
    belly_height = body_height * 0.6
    belly_x = center_x - belly_width // 2
    belly_y = body_y + body_height - belly_height // 2
    draw.ellipse([
        belly_x, belly_y,
        belly_x + belly_width, belly_y + belly_height
    ], fill=belly_color)
    
    # Draw head (circle)
    head_radius = tile_size // 4
    head_x = center_x
    head_y = body_y - head_radius // 2
    draw.ellipse([
        head_x - head_radius, head_y - head_radius,
        head_x + head_radius, head_y + head_radius
    ], fill=fur_color)
    
    # Draw ears (triangles on top of head)
    ear_width = tile_size // 6
    ear_height = tile_size // 3
    # Left ear
    draw.polygon([
        (head_x - head_radius // 2, head_y - head_radius),
        (head_x - head_radius // 2 - ear_width // 2, head_y - head_radius - ear_height),
        (head_x - head_radius // 2 + ear_width // 2, head_y - head_radius - ear_height)
    ], fill=fur_color)
    # Right ear
    draw.polygon([
        (head_x + head_radius // 2, head_y - head_radius),
        (head_x + head_radius // 2 - ear_width // 2, head_y - head_radius - ear_height),
        (head_x + head_radius // 2 + ear_width // 2, head_y - head_radius - ear_height)
    ], fill=fur_color)
    
    # Draw legs (rectangles)
    leg_width = tile_size // 8
    leg_height = tile_size // 3
    leg_top = body_y + body_height
    # Front left leg
    draw.rectangle([
        body_x + body_width // 4, leg_top,
        body_x + body_width // 4 + leg_width, leg_top + leg_height
    ], fill=fur_color)
    # Front right leg
    draw.rectangle([
        body_x + body_width // 2, leg_top,
        body_x + body_width // 2 + leg_width, leg_top + leg_height
    ], fill=fur_color)
    # Back left leg
    draw.rectangle([
        body_x, leg_top,
        body_x + leg_width, leg_top + leg_height
    ], fill=fur_color)
    # Back right leg
    draw.rectangle([
        body_x + body_width - leg_width, leg_top,
        body_x + body_width, leg_top + leg_height
    ], fill=fur_color)
    
    # Draw tail (curved rectangle)
    tail_width = tile_size // 8
    tail_height = tile_size // 3
    tail_x = body_x - tail_width
    tail_y = body_y + body_height // 4
    draw.rectangle([
        tail_x, tail_y,
        tail_x + tail_width, tail_y + tail_height
    ], fill=fur_color)
    
    # Draw nose (small triangle)
    nose_size = tile_size // 8
    nose_x = head_x
    nose_y = head_y + head_radius // 2
    draw.polygon([
        (nose_x - nose_size // 2, nose_y),
        (nose_x, nose_y - nose_size),
        (nose_x + nose_size // 2, nose_y)
    ], fill=nose_color)
    
    # Draw eyes
    eye_size = max(1, tile_size // 12)
    eye_y = head_y - head_radius // 4
    # Left eye
    draw.ellipse([
        head_x - head_radius // 3, eye_y - eye_size // 2,
        head_x - head_radius // 3 + eye_size, eye_y + eye_size // 2
    ], fill=eye_color)
    # Right eye
    draw.ellipse([
        head_x + head_radius // 3 - eye_size, eye_y - eye_size // 2,
        head_x + head_radius // 3, eye_y + eye_size // 2
    ], fill=eye_color)
    
    return img


def generate_grass_terrain(tile_size: int) -> Image.Image:
    """Generate a grass terrain tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Grass colors (various shades of green)
    grass_colors = [
        (34, 139, 34, 255),    # Forest green
        (50, 205, 50, 255),    # Lime green
        (144, 238, 144, 255),  # Light green
        (60, 179, 113, 255),   # Medium sea green
        (0, 128, 0, 255)       # Green
    ]
    
    # Fill base with a grass color
    base_color = random.choice(grass_colors)
    draw.rectangle([
        0, 0,
        tile_size, tile_size
    ], fill=base_color)
    
    # Add grass blades (small lines)
    for _ in range(tile_size // 2):
        blade_width = random.randint(1, 2)
        blade_height = random.randint(tile_size // 4, tile_size // 2)
        blade_x = random.randint(0, tile_size - blade_width)
        blade_y = random.randint(tile_size // 2, tile_size - blade_height)
        
        # Slightly darker green for blades
        blade_color = tuple(max(0, c - 30) for c in base_color[:-1]) + (255,)
        draw.rectangle([
            blade_x, blade_y,
            blade_x + blade_width, blade_y + blade_height
        ], fill=blade_color)
    
    # Add some lighter spots for variation
    for _ in range(random.randint(2, 5)):
        spot_size = random.randint(2, 5)
        spot_x = random.randint(0, tile_size - spot_size)
        spot_y = random.randint(0, tile_size - spot_size)
        
        # Lighter green spot
        spot_color = tuple(min(255, c + 30) for c in base_color[:-1]) + (255,)
        draw.ellipse([
            spot_x, spot_y,
            spot_x + spot_size, spot_y + spot_size
        ], fill=spot_color)
    
    return img


def generate_dirt_terrain(tile_size: int) -> Image.Image:
    """Generate a dirt/sand terrain tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Dirt/Sand colors (various shades of brown/tan)
    dirt_colors = [
        (139, 69, 19, 255),    # Saddle brown
        (160, 82, 45, 255),    # Brown
        (210, 180, 140, 255),  # Tan
        (222, 184, 135, 255),  # Burlywood
        (244, 164, 96, 255)    # Sandy brown
    ]
    
    # Fill base with a dirt color
    base_color = random.choice(dirt_colors)
    draw.rectangle([
        0, 0,
        tile_size, tile_size
    ], fill=base_color)
    
    # Add texture/noise
    for _ in range(tile_size * tile_size // 4):
        x = random.randint(0, tile_size - 1)
        y = random.randint(0, tile_size - 1)
        noise_val = random.randint(-20, 20)
        noise_color = tuple(max(0, min(255, c + noise_val)) for c in base_color[:-1]) + (255,)
        draw.point((x, y), fill=noise_color)
    
    # Add some pebbles or small rocks
    for _ in range(random.randint(3, 8)):
        pebble_size = random.randint(2, 5)
        pebble_x = random.randint(0, tile_size - pebble_size)
        pebble_y = random.randint(0, tile_size - pebble_size)
        pebble_color = (100, 100, 100, 255)  # Gray
        
        draw.ellipse([
            pebble_x, pebble_y,
            pebble_x + pebble_size, pebble_y + pebble_size
        ], fill=pebble_color)
    
    return img


def generate_water_terrain(tile_size: int) -> Image.Image:
    """Generate a water terrain tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Water colors (various shades of blue)
    water_colors = [
        (30, 144, 255, 200),   # Dodger blue with transparency
        (0, 191, 255, 180),    # Deep sky blue
        (70, 130, 180, 190),   # Steel blue
        (0, 0, 255, 170),      # Blue
        (135, 206, 235, 190)   # Sky blue
    ]
    
    # Fill base with a water color
    base_color = random.choice(water_colors)
    draw.rectangle([
        0, 0,
        tile_size, tile_size
    ], fill=base_color)
    
    # Add wave-like horizontal lines
    for y in range(0, tile_size, max(1, tile_size // 8)):
        wave_width = random.randint(tile_size // 2, tile_size)
        wave_height = random.randint(1, 2)
        wave_x = random.randint(0, tile_size - wave_width)
        
        # Slightly lighter/darker blue for waves
        wave_var = random.randint(-15, 15)
        wave_color = tuple(max(0, min(255, c + wave_var)) for c in base_color[:-1]) + (base_color[3],)
        draw.rectangle([
            wave_x, y,
            wave_x + wave_width, y + wave_height
        ], fill=wave_color)
    
    # Add some sparkles/reflections
    for _ in range(random.randint(2, 6)):
        sparkle_x = random.randint(0, tile_size - 1)
        sparkle_y = random.randint(0, tile_size - 1)
        sparkle_size = random.randint(1, 2)
        sparkle_color = (255, 255, 255, 100)  # Semi-transparent white
        
        draw.ellipse([
            sparkle_x - sparkle_size, sparkle_y - sparkle_size,
            sparkle_x + sparkle_size, sparkle_y + sparkle_size
        ], fill=sparkle_color)
    
    return img


def generate_stone_terrain(tile_size: int) -> Image.Image:
    """Generate a stone/rock terrain tile."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Stone/Rock colors (various shades of gray)
    stone_colors = [
        (105, 105, 105, 255),   # Dim gray
        (112, 128, 144, 255),   # Slate gray
        (128, 128, 128, 255),   # Gray
        (169, 169, 169, 255),   # Dark gray
        (192, 192, 192, 255)    # Light gray
    ]
    
    # Fill base with a stone color
    base_color = random.choice(stone_colors)
    draw.rectangle([
        0, 0,
        tile_size, tile_size
    ], fill=base_color)
    
    # Add crack-like lines
    for _ in range(random.randint(2, 5)):
        # Random crack
        start_x = random.randint(0, tile_size)
        start_y = random.randint(0, tile_size)
        end_x = start_x + random.randint(-tile_size//3, tile_size//3)
        end_y = start_y + random.randint(-tile_size//3, tile_size//3)
        
        # Keep within bounds
        end_x = max(0, min(tile_size, end_x))
        end_y = max(0, min(tile_size, end_y))
        
        crack_color = (50, 50, 50, 255)  # Dark gray
        draw.line([(start_x, start_y), (end_x, end_y)], fill=crack_color, width=1)
    
    # Add some speckles/noise
    for _ in range(tile_size * tile_size // 6):
        x = random.randint(0, tile_size - 1)
        y = random.randint(0, tile_size - 1)
        noise_val = random.randint(-15, 15)
        noise_color = tuple(max(0, min(255, c + noise_val)) for c in base_color[:-1]) + (255,)
        draw.point((x, y), fill=noise_color)
    
    return img


def generate_walk_animation(tile_size: int, direction: str = "right", frame: int = 0) -> Image.Image:
    """Generate a frame of a walk animation."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Use player entity as base
    base_img = generate_player_entity(tile_size)
    
    # Create walking motion by offsetting limbs
    # Frame 0: feet together
    # Frame 1: left foot forward
    # Frame 2: feet apart
    # Frame 3: right foot forward
    
    # Paste the base image
    img.paste(base_img, (0, 0))
    
    # For animation effect, we'll modify the leg positions based on frame
    if frame == 1:  # Left foot forward
        # Erase and redraw left leg forward
        pass  # Simplified - in a full implementation we'd modify the leg positions
    elif frame == 2:  # Feet apart
        pass  # Simplified
    elif frame == 3:  # Right foot forward
        # Erase and redraw right leg forward
        pass  # Simplified
    
    # For now, just return the base image with a slight modification to indicate animation
    # Add a small marker to differentiate frames
    marker_size = max(1, tile_size // 16)
    marker_color = (255, 255, 0, 128)  # Semi-transparent yellow
    
    if frame == 0:
        draw.rectangle([0, 0, marker_size, marker_size], fill=marker_color)
    elif frame == 1:
        draw.rectangle([tile_size-marker_size, 0, tile_size, marker_size], fill=marker_color)
    elif frame == 2:
        draw.rectangle([0, tile_size-marker_size, marker_size, tile_size], fill=marker_color)
    elif frame == 3:
        draw.rectangle([tile_size-marker_size, tile_size-marker_size, tile_size, tile_size], fill=marker_color)
    
    return img


def generate_attack_animation(tile_size: int, frame: int = 0) -> Image.Image:
    """Generate a frame of an attack animation."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Use player entity as base
    base_img = generate_player_entity(tile_size)
    
    # Paste the base image
    img.paste(base_img, (0, 0))
    
    # For attack animation, we'll modify the arm position
    # Frame 0: arm down
    # Frame 1: arm swinging up
    # Frame 2: arm at peak
    
    # Add a marker to differentiate frames
    marker_size = max(1, tile_size // 16)
    marker_color = (255, 0, 0, 128)  # Semi-transparent red
    
    if frame == 0:
        draw.rectangle([0, tile_size//2, marker_size, tile_size//2+marker_size], fill=marker_color)
    elif frame == 1:
        draw.rectangle([tile_size//2, 0, tile_size//2+marker_size, marker_size], fill=marker_color)
    elif frame == 2:
        draw.rectangle([tile_size-marker_size, tile_size//2, tile_size, tile_size//2+marker_size], fill=marker_color)
    
    return img


def generate_death_animation(tile_size: int, frame: int = 0) -> Image.Image:
    """Generate a frame of a death animation."""
    # Create a transparent image
    img = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Use enemy entity as base
    base_img = generate_enemy_entity(tile_size)
    
    # Paste the base image
    img.paste(base_img, (0, 0))
    
    # For death animation, we'll make it fall over or fade
    # Frame 0: standing
    # Frame 1: leaning
    # Frame 2: more leaning
    # Frame 3: on ground
    
    # Add a marker to differentiate frames
    marker_size = max(1, tile_size // 16)
    marker_color = (0, 255, 0, 128)  # Semi-transparent green
    
    if frame == 0:
        draw.rectangle([0, 0, marker_size, marker_size], fill=marker_color)
    elif frame == 1:
        draw.rectangle([0, tile_size//2, marker_size, tile_size//2+marker_size], fill=marker_color)
    elif frame == 2:
        draw.rectangle([tile_size//2, 0, tile_size//2+marker_size, marker_size], fill=marker_color)
    elif frame == 3:
        draw.rectangle([tile_size-marker_size, tile_size-marker_size, tile_size, tile_size], fill=marker_color)
    
    return img


def generate_tileset(
    def_path: str,
    output_dir: str,
    tile_size: int = 32,
    variant: str = '',
    generate_effects: bool = False,
    generate_entities: bool = False,
    generate_terrain: bool = False,
    generate_animations: bool = False
) -> Dict:
    """Generate tileset atlas from definition."""
    os.makedirs(output_dir, exist_ok=True)
    
    definition = load_tileset_definition(def_path)
    tiles = []
    tile_names = []
    
    # Load regular tiles from definition
    for tile_def in definition.get('tiles', []):
        tile_path = tile_def.get('path')
        if tile_path and os.path.exists(tile_path):
            try:
                tile_img = Image.open(tile_path).convert('RGBA')
                tiles.append(tile_img)
                tile_names.append(tile_def.get('name', f'tile_{len(tile_names)}'))
            except Exception as e:
                print(f"Warning: Could not load {tile_path}: {e}")
    
    # Generate procedural effects if requested
    if generate_effects:
        effect_types = definition.get('effects', ['blood', 'magic', 'flame'])
        for effect_type in effect_types:
            if effect_type == 'blood':
                effect_img = generate_blood_splat_effect(tile_size)
                tiles.append(effect_img)
                tile_names.append(f'blood_splat_{len([n for n in tile_names if n.startswith("blood")])}')
            elif effect_type == 'magic':
                effect_img = generate_magic_effect(tile_size)
                tiles.append(effect_img)
                tile_names.append(f'magic_effect_{len([n for n in tile_names if n.startswith("magic")])}')
            elif effect_type == 'flame':
                effect_img = generate_flame_effect(tile_size)
                tiles.append(effect_img)
                tile_names.append(f'flame_effect_{len([n for n in tile_names if n.startswith("flame")])}')
    
    # Generate procedural entities if requested
    if generate_entities:
        entity_types = definition.get('entities', ['player', 'enemy', 'pet'])
        for entity_type in entity_types:
            if entity_type == 'player':
                entity_img = generate_player_entity(tile_size)
                tiles.append(entity_img)
                tile_names.append(f'player_{len([n for n in tile_names if n.startswith("player")])}')
            elif entity_type == 'enemy':
                entity_img = generate_enemy_entity(tile_size)
                tiles.append(entity_img)
                tile_names.append(f'enemy_{len([n for n in tile_names if n.startswith("enemy")])}')
            elif entity_type == 'pet':
                entity_img = generate_pet_entity(tile_size)
                tiles.append(entity_img)
                tile_names.append(f'pet_{len([n for n in tile_names if n.startswith("pet")])}')
    
    # Generate procedural terrain if requested
    if generate_terrain:
        terrain_types = definition.get('terrain', ['grass', 'dirt', 'water', 'stone'])
        for terrain_type in terrain_types:
            if terrain_type == 'grass':
                terrain_img = generate_grass_terrain(tile_size)
                tiles.append(terrain_img)
                tile_names.append(f'grass_{len([n for n in tile_names if n.startswith("grass")])}')
            elif terrain_type == 'dirt':
                terrain_img = generate_dirt_terrain(tile_size)
                tiles.append(terrain_img)
                tile_names.append(f'dirt_{len([n for n in tile_names if n.startswith("dirt")])}')
            elif terrain_type == 'water':
                terrain_img = generate_water_terrain(tile_size)
                tiles.append(terrain_img)
                tile_names.append(f'water_{len([n for n in tile_names if n.startswith("water")])}')
            elif terrain_type == 'stone':
                terrain_img = generate_stone_terrain(tile_size)
                tiles.append(terrain_img)
                tile_names.append(f'stone_{len([n for n in tile_names if n.startswith("stone")])}')
    
    # Generate procedural animations if requested
    if generate_animations:
        animation_types = definition.get('animations', ['walk', 'attack', 'death'])
        for animation_type in animation_types:
            if animation_type == 'walk':
                # Generate 4 frames of walk animation
                for frame in range(4):
                    anim_img = generate_walk_animation(tile_size, frame=frame)
                    tiles.append(anim_img)
                    tile_names.append(f'walk_frame_{frame}')
            elif animation_type == 'attack':
                # Generate 3 frames of attack animation
                for frame in range(3):
                    anim_img = generate_attack_animation(tile_size, frame=frame)
                    tiles.append(anim_img)
                    tile_names.append(f'attack_frame_{frame}')
            elif animation_type == 'death':
                # Generate 4 frames of death animation
                for frame in range(4):
                    anim_img = generate_death_animation(tile_size, frame=frame)
                    tiles.append(anim_img)
                    tile_names.append(f'death_frame_{frame}')
    
    if not tiles:
        print("No valid tiles found, creating empty atlas")
        tiles = [Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))]
        tile_names = ['empty']
    
    atlas, metadata = create_atlas(tiles, tile_size)
    
    base_name = f"tileset_{tile_size}x{tile_size}"
    if variant:
        base_name += f"_{variant}"
    
    png_path = os.path.join(output_dir, f"{base_name}.png")
    json_path = os.path.join(output_dir, f"{base_name}.json")
    
    atlas.save(png_path)
    
    output_data = {
        'tile_size': tile_size,
        'atlas_width': atlas.width,
        'atlas_height': atlas.height,
        'tile_count': len(tiles),
        'tiles': []
    }
    
    for i, (name, meta) in enumerate(zip(tile_names, metadata)):
        output_data['tiles'].append({
            'name': name,
            'index': i,
            **meta
        })
    
    with open(json_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Generated {png_path} and {json_path}")
    return output_data


def main():
    parser = argparse.ArgumentParser(description='Generate tileset atlas')
    parser.add_argument('--def', dest='def_path', required=True, help='Path to tileset definition JSON')
    parser.add_argument('--output', default='assets/tilesets', help='Output directory')
    parser.add_argument('--size', type=int, default=32, help='Tile size (16 or 32)')
    parser.add_argument('--variant', default='', help='Variant suffix')
    parser.add_argument('--effects', action='store_true', help='Generate procedural effects')
    parser.add_argument('--entities', action='store_true', help='Generate procedural entities')
    parser.add_argument('--terrain', action='store_true', help='Generate procedural terrain')
    parser.add_argument('--animations', action='store_true', help='Generate procedural animations')
    
    args = parser.parse_args()
    generate_tileset(args.def_path, args.output, args.size, args.variant, args.effects, args.entities, args.terrain, args.animations)


if __name__ == '__main__':
    main()