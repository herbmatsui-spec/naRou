#!/usr/bin/env python3
"""
Frontend Preview Generator for Asset Packs
Generates HTML preview pages for tiny rogue tiles, audio, and emote assets.
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path
from asset_manager import ASSET_MANAGER


def generate_tile_preview(output_path: Path) -> None:
    """Generate HTML preview for tiny rogue tiles."""
    meta = ASSET_MANAGER.get_tiny_rogue_atlas_meta()
    if not meta:
        print("No atlas metadata available")
        return
    
    tiles = meta.get("tiles", {})
    atlas_path = "assets/tiles/tiny_rogue_atlas_16x16.png"
    
    # Group tiles by category
    categories = {}
    for tile_id, info in tiles.items():
        prefix = tile_id.split("_")[0] + "_" + tile_id.split("_")[1] if "_" in tile_id else tile_id
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append((tile_id, info))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tiny Rogue Tiles Preview</title>
    <style>
        body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ color: #ffd700; }}
        .category {{ margin-bottom: 30px; }}
        .category h2 {{ color: #00ff88; border-bottom: 1px solid #333; padding-bottom: 5px; }}
        .tile-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .tile {{ text-align: center; background: #222; padding: 10px; border-radius: 4px; min-width: 80px; }}
        .tile img {{ width: 64px; height: 64px; image-rendering: pixelated; }}
        .tile-name {{ font-size: 11px; color: #aaa; margin-top: 5px; word-break: break-all; }}
        .tile-info {{ font-size: 10px; color: #666; }}
        .atlas-img {{ border: 1px solid #444; image-rendering: pixelated; max-width: 100%; }}
    </style>
</head>
<body>
    <h1>Tiny Rogue Tile Atlas Preview</h1>
    <p>Atlas: <code>{atlas_path}</code> ({meta.get('atlas_width', '?')}x{meta.get('atlas_height', '?')})</p>
    <img class="atlas-img" src="{atlas_path}" alt="Full Atlas">
    
    <h2>Individual Tiles</h2>
"""
    
    for cat_name, tiles_list in sorted(categories.items()):
        html += f'<div class="category"><h2>{cat_name} ({len(tiles_list)} tiles)</h2><div class="tile-grid">'
        for tile_id, info in sorted(tiles_list):
            x, y = info['x'], info['y']
            w, h = info['width'], info['height']
            anim = "🔄" if info.get('animated') else ""
            dirs = info.get('directions', 1)
            frames = info.get('frames', 1)
            
            # Create a data URI for the cropped tile
            html += f'''
            <div class="tile">
                <img src="{atlas_path}#xywh={x},{y},{w},{h}" alt="{tile_id}">
                <div class="tile-name">{tile_id}</div>
                <div class="tile-info">{w}x{h} {anim} dirs={dirs} frames={frames}</div>
            </div>'''
        html += '</div></div>'
    
    html += """
</body>
</html>"""
    
    output_path.write_text(html)
    print(f"Generated tile preview: {output_path}")


def generate_audio_preview(output_path: Path) -> None:
    """Generate HTML preview for audio SFX."""
    manifest = ASSET_MANAGER.get_audio_manifest()
    if not manifest:
        print("No audio manifest available")
        return
    
    # Group by category
    categories = {}
    for entry in manifest:
        cat = entry.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(entry)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Audio SFX Preview</title>
    <style>
        body { font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { color: #ffd700; }
        .category { margin-bottom: 30px; }
        .category h2 { color: #00ff88; border-bottom: 1px solid #333; padding-bottom: 5px; }
        .audio-row { display: flex; align-items: center; gap: 15px; padding: 8px; background: #222; margin: 5px 0; border-radius: 4px; }
        .audio-name { min-width: 200px; font-family: monospace; }
        .audio-category { color: #888; font-size: 12px; min-width: 80px; }
        .audio-suggested { color: #ffd700; font-size: 12px; min-width: 150px; }
        audio { width: 200px; }
    </style>
</head>
<body>
    <h1>Audio SFX Preview</h1>
    <p>Total files: """ + str(len(manifest)) + """</p>
"""
    
    for cat_name, entries in sorted(categories.items()):
        html += f'<div class="category"><h2>{cat_name} ({len(entries)} sounds)</h2>'
        for entry in sorted(entries, key=lambda x: x['filename']):
            filename = entry['filename']
            suggested = entry.get('suggested_id', '')
            stem = filename.replace('.ogg', '').replace('.wav', '')
            audio_path = f"assets/audio/{filename}"
            html += f'''
            <div class="audio-row">
                <span class="audio-name">{filename}</span>
                <span class="audio-category">{cat_name}</span>
                <span class="audio-suggested">{suggested}</span>
                <audio controls preload="none"><source src="{audio_path}" type="audio/ogg"></audio>
            </div>'''
        html += '</div>'
    
    html += """
</body>
</html>"""
    
    output_path.write_text(html)
    print(f"Generated audio preview: {output_path}")


def generate_emote_preview(output_path: Path) -> None:
    """Generate HTML preview for emote sprites."""
    sprites = ASSET_MANAGER.list_emote_sprites()
    
    # Group by style/type
    categories = {}
    for sprite in sprites:
        parts = sprite.split('/')
        if len(parts) > 1:
            cat = parts[0]
        else:
            cat = "tilesheets"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(sprite)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Emote Sprites Preview</title>
    <style>
        body { font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { color: #ffd700; }
        .category { margin-bottom: 30px; }
        .category h2 { color: #00ff88; border-bottom: 1px solid #333; padding-bottom: 5px; }
        .sprite-grid { display: flex; flex-wrap: wrap; gap: 15px; }
        .sprite { text-align: center; background: #222; padding: 10px; border-radius: 4px; }
        .sprite img { max-width: 128px; max-height: 128px; image-rendering: pixelated; background: #000; }
        .sprite-name { font-size: 11px; color: #aaa; margin-top: 5px; word-break: break-all; max-width: 150px; }
    </style>
</head>
<body>
    <h1>Emote Sprites Preview</h1>
    <p>Total sprites: """ + str(len(sprites)) + """</p>
"""
    
    for cat_name, sprites_list in sorted(categories.items()):
        html += f'<div class="category"><h2>{cat_name} ({len(sprites_list)} sprites)</h2><div class="sprite-grid">'
        for sprite in sorted(sprites_list):
            path = f"assets/emote/{sprite}.png" if not sprite.endswith('.png') else f"assets/emote/{sprite}"
            if not Path(path).exists():
                # Try with .png
                path = f"assets/emote/{sprite}.png"
            html += f'''
            <div class="sprite">
                <img src="{path}" alt="{sprite}" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; color:#666; font-size:10px;">Image not found</div>
                <div class="sprite-name">{sprite}</div>
            </div>'''
        html += '</div></div>'
    
    html += """
</body>
</html>"""
    
    output_path.write_text(html)
    print(f"Generated emote preview: {output_path}")


def main():
    """Generate all previews."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    ASSET_MANAGER.initialize(config)
    
    output_dir = Path("output/previews")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generate_tile_preview(output_dir / "tiles.html")
    generate_audio_preview(output_dir / "audio.html")
    generate_emote_preview(output_dir / "emotes.html")
    
    # Generate index
    index_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Asset Pack Previews</title>
    <style>
        body { font-family: sans-serif; background: #1a1a2e; color: #eee; padding: 40px; text-align: center; }
        h1 { color: #ffd700; }
        .links { display: flex; justify-content: center; gap: 30px; margin-top: 40px; flex-wrap: wrap; }
        .link-btn { display: inline-block; padding: 20px 40px; background: #2a2a4a; color: #ffd700; 
                    text-decoration: none; border-radius: 8px; font-size: 18px; border: 2px solid #444;
                    transition: all 0.2s; }
        .link-btn:hover { background: #3a3a5a; border-color: #ffd700; transform: translateY(-2px); }
    </style>
</head>
<body>
    <h1>Asset Pack Previews</h1>
    <div class="links">
        <a class="link-btn" href="tiles.html">🗺️ Tiny Rogue Tiles</a>
        <a class="link-btn" href="audio.html">🔊 Audio SFX</a>
        <a class="link-btn" href="emotes.html">😊 Emote Sprites</a>
    </div>
</body>
</html>"""
    (output_dir / "index.html").write_text(index_html)
    print(f"Generated index: {output_dir / 'index.html'}")


if __name__ == "__main__":
    main()