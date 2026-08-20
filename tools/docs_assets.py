#!/usr/bin/env python3
"""
Documentation generator script for creating documentation about assets.
Generates API references, usage guides, and asset catalogs.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def generate_tileset_docs(tileset_dir: str, output_dir: str, config: Dict) -> Dict:
    """Generate documentation for tileset assets."""
    stats = {
        'assets_documented': 0,
        'files_generated': 0,
        'errors': []
    }
    
    if not os.path.exists(tileset_dir):
        stats['errors'].append(f"Tileset directory does not exist: {tileset_dir}")
        return stats
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual tileset documentation
    for root, dirs, files in os.walk(tileset_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                stats['assets_documented'] += 1
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        # Generate markdown documentation for this tileset
                        tileset_name = os.path.splitext(file)[0]
                        doc_content = f"""# Tileset: {tileset_name}

## Overview
- **Tile Size**: {metadata.get('tile_size', 0)}px
- **Atlas Dimensions**: {metadata.get('atlas_width', 0)}x{metadata.get('atlas_height', 0)}px
- **Total Tiles**: {metadata.get('tile_count', 0)}
- **Atlas File**: `{os.path.basename(png_path)}`
- **Metadata File**: `{os.path.basename(json_path)}`

## Usage
This tileset can be used in game rendering by mapping tile indices to coordinates:

```javascript
// Example usage in JavaScript/TypeScript
function getTileUV(tileIndex, tilesetData) {{
    if (tileIndex < 0 || tileIndex >= tilesetData.tile_count) {{
        return null; // Invalid tile index
    }}
    
    const tile = tilesetData.tiles[tileIndex];
    return {{
        u: tile.u,
        v: tile.v,
        width: tile.uw,
        height: tile.vh
    }};
}}

// Or using row/column calculation
function getTileByPosition(row, col, tilesetData) {{
    const tilesPerRow = Math.floor(tilesetData.atlas_width / tilesetData.tile_size);
    const tileIndex = row * tilesPerRow + col;
    return getTileUV(tileIndex, tilesetData);
}}
```

## Tile Information
"""
                        
                        # Add tile details if available
                        if 'tiles' in metadata and metadata['tiles']:
                            doc_content += "\n| Index | Name | X | Y | Width | Height | U | V | U Width | V Height |\n"
                            doc_content += "|-------|------|---|---|-------|--------|---|---|---------|----------|\n"
                            for tile in metadata['tiles'][:20]:  # Limit to first 20 tiles
                                doc_content += f"| {tile.get('index', 'N/A')} | {tile.get('name', 'unnamed')} | {tile.get('x', 0)} | {tile.get('y', 0)} | {tile.get('width', 0)} | {tile.get('height', 0)} | {tile.get('u', 0):.4f} | {tile.get('v', 0):.4f} | {tile.get('uw', 0):.4f} | {tile.get('vh', 0):.4f} |\n"
                            
                            if len(metadata['tiles']) > 20:
                                doc_content += f"\n*Showing first 20 tiles. Total tiles: {len(metadata['tiles'])}*\n"
                        else:
                            doc_content += "\n*No detailed tile information available*\n"
                        
                        # Add technical details
                        doc_content += f"""
## Technical Details
- **File Size**: {os.path.getsize(png_path)} bytes (PNG) + {os.path.getsize(json_path)} bytes (JSON)
- **Format**: PNG image with JSON metadata
- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Pipeline Version**: {config.get('version', '1.0.0')}
"""
                        
                        # Write documentation file
                        doc_file = os.path.join(output_dir, f"{tileset_name}_docs.md")
                        with open(doc_file, 'w') as f:
                            f.write(doc_content)
                        
                        stats['files_generated'] += 1
                        
                    except Exception as e:
                        stats['errors'].append(f"Error generating docs for {json_path}: {e}")
    
    # Generate index documentation
    try:
        index_content = f"""# Tileset Documentation Index

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline Version: {config.get('version', '1.0.0')}

## Available Tilesets

"""
        
        # List all tilesets
        tileset_files = []
        for root, dirs, files in os.walk(tileset_dir):
            for file in files:
                if file.endswith('.png'):
                    tileset_files.append(os.path.splitext(file)[0])
        
        if tileset_files:
            index_content += "| Tileset Name | Documentation |\n"
            index_content += "|--------------|---------------|\n"
            for tileset_name in sorted(tileset_files):
                index_content += f"| {tileset_name} | [{tileset_name}_docs.md]({tileset_name}_docs.md) |\n"
        else:
            index_content += "*No tilesets found*\n"
        
        index_content += """
## Usage Guidelines

### Loading Tilesets
Tilesets consist of two files:
1. A PNG image containing the tile atlas
2. A JSON file containing metadata and tile coordinates

### Rendering Tiles
To render a specific tile from a tileset:
1. Look up the tile's UV coordinates in the JSON metadata
2. Use those coordinates to sample the appropriate region from the PNG atlas
3. Render the textured quad to the screen

### Tile Coordinate System
- U, V coordinates are normalized (0.0 to 1.0)
- U Width and V Height represent the tile's size in UV space
- Origin (0,0) is typically at the bottom-left or top-left depending on engine convention

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Font Documentation](../fonts/)
- [Sound Documentation](../sounds/)
- [Model Documentation](../models/)
"""
        
        index_file = os.path.join(output_dir, "index.md")
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        stats['files_generated'] += 1
        
    except Exception as e:
        stats['errors'].append(f"Error generating tileset index: {e}")
    
    return stats


def generate_font_docs(font_dir: str, output_dir: str, config: Dict) -> Dict:
    """Generate documentation for font assets."""
    stats = {
        'assets_documented': 0,
        'files_generated': 0,
        'errors': []
    }
    
    if not os.path.exists(font_dir):
        stats['errors'].append(f"Font directory does not exist: {font_dir}")
        return stats
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual font documentation
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                stats['assets_documented'] += 1
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        font_name = os.path.splitext(file)[0]
                        doc_content = f"""# Font: {font_name}

## Overview
- **Font Size**: {metadata.get('font_size', 0)}pt
- **Atlas Dimensions**: {metadata.get('atlas_width', 0)}x{metadata.get('atlas_height', 0)}px
- **Characters Mapped**: {len(metadata.get('metrics', {}))}
- **Atlas File**: `{os.path.basename(png_path)}`
- **Metadata File**: `{os.path.basename(json_path)}`

## Usage
This font atlas can be used for text rendering in games:

```javascript
// Example usage in JavaScript/TypeScript
class FontRenderer {{
    constructor(fontData, atlasImage) {{
        this.fontData = fontData;
        this.atlas = atlasImage;
    }}
    
    renderText(text, x, y, size = 1, color = '#FFFFFF') {{
        let cursorX = x;
        let cursorY = y;
        
        for (const char of text) {{
            const glyph = this.fontData.metrics[char] || this.fontData.metrics['?'];
            if (!glyph) continue;
            
            // Calculate glyph position and size
            const glyphWidth = glyph.width * size;
            const glyphHeight = glyph.height * size;
            const glyphX = cursorX + (glyph.bearing_x * size);
            const glyphY = cursorY - (glyph.height - glyph.bearing_y) * size;
            
            // Texture coordinates
            const u = glyph.u;
            const v = glyph.v;
            const width = glyph.uw;
            const height = glyph.vh;
            
            // Render glyph quad (implementation depends on your graphics API)
            this.renderGlyphQuad(
                glyphX, glyphY, glyphWidth, glyphHeight,
                u, v, width, height,
                color
            ));
            
            // Move cursor for next character
            cursorX += glyph.advance * size;
        }}
    }}
    
    renderGlyphQuad(x, y, width, height, u, v, texWidth, texHeight, color) {{
        // Implementation-specific rendering code
        // This would bind the atlas texture and draw a textured quad
    }}
}}

// Get kerning adjustment (if supported)
function getKerning(fontData, char1, char2) {{
    // Many font formats don't include kerning in basic atlases
    // This would need to be implemented based on your font format
    return 0;
}}
```

## Character Support
"""
                        
                        # Add character coverage information
                        metrics = metadata.get('metrics', {})
                        if metrics:
                            # Group characters by type
                            ascii_chars = [c for c in metrics.keys() if ord(c) < 128]
                            extended_chars = [c for c in metrics.keys() if ord(c) >= 128]
                            
                            doc_content += f"""- **Total Characters**: {len(metrics)}
- **ASCII Characters** (0-127): {len(ascii_chars)}
- **Extended Characters** (≥128): {len(extended_chars)}

### ASCII Character Coverage
"""
                            
                            # Show ASCII characters in a grid
                            doc_content += "```\n"
                            for row in range(16):
                                line = ""
                                for col in range(16):
                                    char_code = row * 16 + col
                                    if char_code < 32 or char_code > 126:  # Non-printable ASCII
                                        line += " . "
                                    else:
                                        char = chr(char_code)
                                        if char in metrics:
                                            line += f" {char} "
                                        else:
                                            line += "   "
                                doc_content += line + "\n"
                            doc_content += "```\n"
                            
                            # List extended characters if any
                            if extended_chars:
                                doc_content += f"\n**Extended Characters**: {''.join(sorted(extended_chars[:50]))}"
                                if len(extended_chars) > 50:
                                    doc_content += f"... and {len(extended_chars) - 50} more"
                        else:
                            doc_content += "\n*No character metrics available*\n"
                        
                        # Add technical details
                        doc_content += f"""
## Technical Details
- **File Size**: {os.path.getsize(png_path)} bytes (PNG) + {os.path.getsize(json_path)} bytes (JSON)
- **Format**: PNG image with JSON metadata
- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Pipeline Version**: {config.get('version', '1.0.0')}
"""
                        
                        # Write documentation file
                        doc_file = os.path.join(output_dir, f"{font_name}_docs.md")
                        with open(doc_file, 'w') as f:
                            f.write(doc_content)
                        
                        stats['files_generated'] += 1
                        
                    except Exception as e:
                        stats['errors'].append(f"Error generating docs for {json_path}: {e}")
    
    # Generate index documentation
    try:
        index_content = f"""# Font Documentation Index

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline Version: {config.get('version', '1.0.0')}

## Available Fonts

"""
        
        # List all fonts
        font_files = []
        for root, dirs, files in os.walk(font_dir):
            for file in files:
                if file.endswith('.png'):
                    font_files.append(os.path.splitext(file)[0])
        
        if font_files:
            index_content += "| Font Name | Documentation |\n"
            index_content += "|-----------|---------------|\n"
            for font_name in sorted(font_files):
                index_content += f"| {font_name} | [{font_name}_docs.md]({font_name}_docs.md) |\n"
        else:
            index_content += "*No fonts found*\n"
        
        index_content += """
## Usage Guidelines

### Loading Fonts
Fonts consist of two files:
1. A PNG image containing the character atlas
2. A JSON file containing metadata and character metrics

### Rendering Text
To render text using a font atlas:
1. Load the PNG atlas as a texture
2. Parse the JSON metadata to get character metrics
3. For each character in the string, look up its UV coordinates and dimensions
4. Render textured quads for each character, advancing the cursor by the character's advance width

### Character Metrics Explained
- **x, y**: Position of character in the atlas (in pixels)
- **width, height**: Dimensions of the character glyph (in pixels)
- **u, v**: Normalized texture coordinates (0.0 to 1.0)
- **uw, vh**: Normalized texture dimensions (0.0 to 1.0)
- **bearing_x, bearing_y**: Offset from cursor to glyph origin
- **advance**: Horizontal distance to advance cursor after rendering glyph

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Sound Documentation](../sounds/)
- [Model Documentation](../models/)
"""
        
        index_file = os.path.join(output_dir, "index.md")
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        stats['files_generated'] += 1
        
    except Exception as e:
        stats['errors'].append(f"Error generating font index: {e}")
    
    return stats


def generate_sound_docs(sound_dir: str, output_dir: str, config: Dict) -> Dict:
    """Generate documentation for sound assets."""
    stats = {
        'assets_documented': 0,
        'files_generated': 0,
        'errors': []
    }
    
    if not os.path.exists(sound_dir):
        stats['errors'].append(f"Sound directory does not exist: {sound_dir}")
        return stats
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual sound documentation
    extensions = ['.ogg', '.mp3', '.wav', '.flac']
    for root, dirs, files in os.walk(sound_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                stats['assets_documented'] += 1
                sound_path = os.path.join(root, file)
                
                try:
                    sound_name = os.path.splitext(file)[0]
                    file_size = os.path.getsize(sound_path)
                    
                    # Try to get metadata (would use audio library in real implementation)
                    duration = 0.0  # Placeholder
                    bitrate = 0     # Placeholder
                    
                    doc_content = f"""# Sound: {sound_name}

## Overview
- **File Name**: {file}
- **File Size**: {file_size} bytes ({file_size / 1024:.1f} KB)
- **Format**: {Path(file).suffix.upper()[1:]}
- **Duration**: {duration:.2f} seconds (estimated)
- **Bitrate**: {bitrate} kbps (estimated)

## Usage
This sound asset can be loaded and played in games:

```javascript
// Example usage in JavaScript/TypeScript with Web Audio API
class SoundManager {{
    constructor(audioContext) {{
        this.context = audioContext;
        this.sounds = new Map(); // Cache for loaded sounds
    }}
    
    async loadSound(name, url) {{
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await this.context.decodeAudioData(arrayBuffer);
        this.sounds.set(name, audioBuffer);
        return audioBuffer;
    }}
    
    playSound(name, options = {{}}) {{
        const buffer = this.sounds.get(name);
        if (!buffer) {{
            console.warn(`Sound not found: {{name}}`);
            return null;
        }}
        
        const source = this.context.createBufferSource();
        source.buffer = buffer;
        
        // Apply options
        const gainNode = this.context.createGain();
        gainNode.gain.value = options.volume || 1.0;
        source.connect(gainNode).connect(this.context.destination);
        
        // Set looping if requested
        source.loop = options.loop || false;
        
        // Play sound
        source.start(0);
        
        // Return source for potential stopping
        return source;
    }}
    
    stopSound(source) {{
        if (source) {{
            source.stop();
        }}
    }}
}}

// Alternative: Using HTML5 Audio (simpler but less control)
function playSoundWithAudioElement(src, volume = 1.0, loop = false) {{
    const audio = new Audio(src);
    audio.volume = volume;
    audio.loop = loop;
    audio.play().catch(e => console.error('Failed to play sound:', e));
    return audio; // Return for potential pausing/stopping
}}
```

## Technical Details
- **File Size**: {file_size} bytes
- **Format**: {Path(file).suffix.upper()[1:]}
- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Pipeline Version**: {config.get('version', '1.0.0')}

## Format-Specific Notes
"""
                    
                    # Add format-specific information
                    ext = Path(file).suffix.lower()
                    if ext == '.ogg':
                        doc_content += """- **OGG Vorbis**: Open-source, lossy compression format. Good balance of quality and file size. Widely supported.
- **Looping**: Supports seamless looping
- **Metadata**: Supports tags (title, artist, album, etc.)"""
                    elif ext == '.mp3':
                        doc_content += """- **MP3**: Widely compatible, lossy compression format. May have licensing considerations.
- **Looping**: May have gaps at loop boundaries due to encoder delay/padding
- **Metadata**: Extensive ID3 tag support"""
                    elif ext == '.wav':
                        doc_content += """- **WAV**: Uncompressed, lossless format. Highest quality but largest file size.
- **Looping**: Supports seamless looping
- **Metadata**: Limited compared to other formats"""
                    elif ext == '.flac':
                        doc_content += """- **FLAC**: Free lossless audio codec. Compression without quality loss.
- **Looping**: Supports seamless looping
- **Metadata**: Extensive tag support like Vorbis comments"""
                    
                    doc_content += f"""
## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Font Documentation](../fonts/)
- [Model Documentation](../models/)
"""
                    
                    # Write documentation file
                    doc_file = os.path.join(output_dir, f"{sound_name}_docs.md")
                    with open(doc_file, 'w') as f:
                        f.write(doc_content)
                    
                    stats['files_generated'] += 1
                    
                except Exception as e:
                    stats['errors'].append(f"Error generating docs for {sound_path}: {e}")
    
    # Generate index documentation
    try:
        index_content = f"""# Sound Documentation Index

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline Version: {config.get('version', '1.0.0')}

## Available Sounds

"""
        
        # List all sounds
        sound_files = []
        for root, dirs, files in os.walk(sound_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in ['.ogg', '.mp3', '.wav', '.flac']):
                    sound_files.append(os.path.splitext(file)[0])
        
        if sound_files:
            index_content += "| Sound Name | Format | Documentation |\n"
            index_content += "|------------|--------|---------------|\n"
            for sound_name in sorted(sound_files):
                # Find the actual file to get extension
                found = False
                for ext in ['.ogg', '.mp3', '.wav', '.flac']:
                    test_path = os.path.join(sound_dir, sound_name + ext)
                    if os.path.exists(test_path):
                        index_content += f"| {sound_name} | {ext.upper()[1:]} | [{sound_name}_docs.md]({sound_name}_docs.md) |\n"
                        found = True
                        break
                if not found:
                    index_content += f"| {sound_name} | unknown | [{sound_name}_docs.md]({sound_name}_docs.md) |\n"
        else:
            index_content += "*No sounds found*\n"
        
        index_content += """
## Usage Guidelines

### Loading Sounds
Sound assets can be loaded using:
- **Web Audio API**: For precise control, positioning, and effects
- **HTML5 Audio Element**: For simpler background music playback
- **Native Audio Libraries**: Depending on your game engine or framework

### Playing Sounds
- **Short Effects** (SFX): Load into memory and play instantly
- **Music/BGM**: Stream from disk or load based on length
- **Voice/Overs**: Similar to SFX but may need speech-specific processing

### Audio Best Practices
1. **Compression**: Use OGG for most game audio (good quality/size ratio)
2. **Looping**: Ensure seamless loops for background music and ambient sounds
3. **Volume**: Normalize audio levels to prevent sudden volume changes
4. **Spatialization**: Use 3D audio for positional sound effects in 3D games
5. **Streaming**: Stream long music tracks instead of loading entirely into memory

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Font Documentation](../fonts/)
- [Model Documentation](../models/)
"""
        
        index_file = os.path.join(output_dir, "index.md")
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        stats['files_generated'] += 1
        
    except Exception as e:
        stats['errors'].append(f"Error generating sound index: {e}")
    
    return stats


def generate_model_docs(model_dir: str, output_dir: str, config: Dict) -> Dict:
    """Generate documentation for model assets."""
    stats = {
        'assets_documented': 0,
        'files_generated': 0,
        'errors': []
    }
    
    if not os.path.exists(model_dir):
        stats['errors'].append(f"Model directory does not exist: {model_dir}")
        return stats
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual model documentation
    extensions = ['.obj', '.fbx', '.gltf', '.glb', '.dae', '.3ds', '.blend', '.ply', '.stl']
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                stats['assets_documented'] += 1
                model_path = os.path.join(root, file)
                
                try:
                    model_name = os.path.splitext(file)[0]
                    file_size = os.path.getsize(model_path)
                    
                    # Try to get metadata (would use assimp or similar in real implementation)
                    vertex_count = 0
                    face_count = 0
                    
                    if file.endswith('.obj'):
                        # Simple OBJ parsing
                        try:
                            with open(model_path, 'r') as f:
                                for line in f:
                                    if line.startswith('v '):
                                        vertex_count += 1
                                    elif line.startswith('f '):
                                        face_count += 1
                        except Exception:
                            pass
                    
                    doc_content = f"""# Model: {model_name}

## Overview
- **File Name**: {file}
- **File Size**: {file_size} bytes ({file_size / 1024:.1f} KB)
- **Format**: {Path(file).suffix.upper()[1:]}
- **Vertices**: {vertex_count:,}
- **Faces**: {face_count:,}
- **Triangles**: {face_count:,} (assuming all faces are triangular)

## Usage
This 3D model can be loaded and rendered in games:

```javascript
// Example usage in JavaScript/TypeScript with WebGL or similar
class ModelLoader {{
    constructor(glContext) {{
        this.gl = glContext;
        this.models = new Map(); // Cache for loaded models
    }}
    
    async loadModel(name, url) {{
        // In a real implementation, you would use a library like:
        // - THREE.js with GLTFLoader
        // - Babylon.js with AssetsManager
        // - Custom parser for OBJ/FBX/etc.
        // 
        // For this example, we'll show the concept:
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        // Parse the format-specific data here
        const modelData = await this.parseModelFormat(arrayBuffer, '{Path(file).suffix}');
        this.models.set(name, modelData);
        return modelData;
    }}
    
    renderModel(name, position = [0, 0, 0], rotation = [0, 0, 0], scale = [1, 1, 1]) {{
        const model = this.models.get(name);
        if (!model) {{
            console.warn(`Model not found: {{name}}`);
            return;
        }}
        
        // Apply transformation matrix
        const modelMatrix = this.createTransformationMatrix(position, rotation, scale);
        
        // Set uniforms and draw
        this.gl.useModelMatrix(modelMatrix);
        this.gl.drawModel(model);
    }}
    
    // Helper methods would go here...
    createTransformationMatrix(position, rotation, scale) {{
        // Implementation depends on your math library
        return identityMatrix;
    }}
    
    parseModelFormat(arrayBuffer, format) {{
        // Format-specific parsing logic
        // This would delegate to specialized parsers
        return {{}}; // Placeholder
    }}
}}

// Alternative: Using a game engine (Unity/Unreal/Godot)
//
// Unity:
//   GameObject model = Instantiate(Resources.Load("{model_name}") as GameObject);
//
// Unreal Engine:
//   StaticMesh* Mesh = LoadObject<StaticMesh>(NULL, TEXT("{model_name}"));
//
// Godot:
//   var model = preload("res://{model_name}.scen").instance()
//   add_child(model)
```

## Technical Details
- **File Size**: {file_size} bytes
- **Format**: {Path(file).suffix.upper()[1:]}
- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Pipeline Version**: {config.get('version', '1.0.0')}

## Format-Specific Information
"""
                    
                    # Add format-specific details
                    ext = Path(file).suffix.lower()
                    format_info = {
                        '.obj': '''**OBJ (Wavefront)**:
- Simple, widely-supported format
- Stores vertices, texture coordinates, normals, and faces
- Does not support animation natively
- Text-based format (human-readable but larger file size)''',
                        '.fbx': '''**FBX (Filmbox)**:
- Autodesk format with broad industry support
- Supports meshes, materials, animations, skeletons
- Binary and ASCII versions available
- Proprietary but well-documented''',
                        '.gltf': '''**glTF (GL Transmission Format)**:
- Open standard by Khronos Group
- Efficient, interoperable format for 3D scenes
- Supports PBR materials, animations, skeletons
- Binary (.glb) and JSON-based (.gltf) versions
- Designed for web and real-time applications''',
                        '.glb': '''**glb (Binary glTF)**:
- Binary version of glTF format
- More compact than JSON-based glTF
- Preferred for distribution due to smaller size''',
                        '.dae': '''**DAE (COLLADA)**:
- XML-based format for 3D asset exchange
- Supports geometries, materials, animations, physics
- Open standard but less commonly used now than glTF''',
                        '.3ds': '''**3DS (3D Studio)**:
- Legacy Autodesk format
- Limited to 65535 vertices per mesh
- Largely superseded by FBX and glTF''',
                        '.blend': '''**BLEND (Blender)**:
- Native format for Blender software
- Contains complete scene data
- Not ideal for distribution; export to glTF/OBJ instead''',
                        '.ply': '''**PLY (Polygon File Format)**:
- Originally for 3D scanners
- Supports vertices, faces, color, normals
- Both ASCII and binary versions''',
                        '.stl': '''**STL (Stereolithography)**:
- Primarily for 3D printing
- Stores only vertex coordinates and facet normals
- No texture or material support'''
                    }
                    
                    if ext in format_info:
                        doc_content += format_info[ext]
                    else:
                        doc_content += f"- **{ext.upper()[1:]}**: Format-specific details not available"
                    
                    doc_content += f"""
## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Font Documentation](../fonts/)
- [Sound Documentation](../sounds/)
"""
                    
                    # Write documentation file
                    doc_file = os.path.join(output_dir, f"{model_name}_docs.md")
                    with open(doc_file, 'w') as f:
                        f.write(doc_content)
                    
                    stats['files_generated'] += 1
                    
                except Exception as e:
                    stats['errors'].append(f"Error generating docs for {model_path}: {e}")
    
    # Generate index documentation
    try:
        index_content = f"""# Model Documentation Index

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline Version: {config.get('version', '1.0.0')}

## Available Models

"""
        
        # List all models
        model_files = []
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in ['.obj', '.fbx', '.gltf', '.glb', '.dae', '.3ds', '.blend', '.ply', '.stl']):
                    model_files.append(os.path.splitext(file)[0])
        
        if model_files:
            index_content += "| Model Name | Format | Documentation |\n"
            index_content += "|------------|--------|---------------|\n"
            for model_name in sorted(model_files):
                # Find the actual file to get extension
                found = False
                for ext in ['.obj', '.fbx', '.gltf', '.glb', '.dae', '.3ds', '.blend', '.ply', '.stl']:
                    test_path = os.path.join(model_dir, model_name + ext)
                    if os.path.exists(test_path):
                        index_content += f"| {model_name} | {ext.upper()[1:]} | [{model_name}_docs.md]({model_name}_docs.md) |\n"
                        found = True
                        break
                if not found:
                    index_content += f"| {model_name} | unknown | [{model_name}_docs.md]({model_name}_docs.md) |\n"
        else:
            index_content += "*No models found*\n"
        
        index_content += """
## Usage Guidelines

### Loading Models
Model assets can be loaded using:
- **Graphics Libraries**: THREE.js, Babylon.js, WebGL-native code
- **Game Engines**: Unity, Unreal Engine, Godot, CryEngine
- **Custom Loaders**: For proprietary or specialized formats

### Model Optimization
For better performance in games:
1. **Level of Detail (LOD)**: Create multiple versions of models at different detail levels
2. **Mesh Compression**: Use techniques like Draco compression for glTF
3. **Texture Atlas**: Combine multiple textures into atlases to reduce draw calls
4. **Instancing**: Render multiple copies of the same model efficiently
5. **Culling**: Frustum, occlusion, and distance culling to avoid rendering invisible models

### Format Recommendations
- **Web Applications**: Use glTF/.glb for best compatibility and performance
- **Game Engines**: Use engine-native formats or FBX for maximum feature support
- **Archival/Exchange**: Use OBJ or FBX for maximum compatibility
- **3D Printing**: Use STL for printable models

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Font Documentation](../fonts/)
- [Sound Documentation](../sounds/)
"""
        
        index_file = os.path.join(output_dir, "index.md")
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        stats['files_generated'] += 1
        
    except Exception as e:
        stats['errors'].append(f"Error generating model index: {e}")
    
    return stats


def generate_overall_docs(config: Dict) -> Dict:
    """Generate overall asset pipeline documentation."""
    stats = {
        'files_generated': 0,
        'errors': []
    }
    
    try:
        # Generate main documentation index
        docs_dir = os.path.join(config['directories']['output'], 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        
        main_content = f"""# naRou Asset Pipeline Documentation

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Pipeline Version: {config.get('version', '1.0.0')}

## Overview
This documentation provides comprehensive information about all assets processed by the naRou asset pipeline.

## Asset Categories

| Category | Description | Documentation |
|----------|-------------|---------------|
| 🧱 [Tilesets](tilesets/) | 2D tile atlases for game worlds and interfaces | [Index](tilesets/index.md) |
| 🔤 [Fonts](fonts/) | Bitmap font atlases for text rendering | [Index](fonts/index.md) |
| 🔊 [Sounds](sounds/) | Audio effects, music, and voiceovers | [Index](sounds/index.md) |
| 🧊 [Models](models/) | 3D models for characters, props, and environments | [Index](models/index.md) |

## Pipeline Documentation

- [Build Process](build_process.md)
- [Validation Procedures](validation.md)
- [Deployment Guide](deployment.md)
- [Configuration Reference](configuration.md)

## Getting Started

### Asset Loading
All assets follow a consistent loading pattern:
1. Locate the asset in the appropriate category directory
2. Load both the asset file and its metadata (when applicable)
3. Initialize the asset in your rendering/audio system
4. Use the asset as needed in your game logic

### Asset Naming Convention
Assets are named descriptively using lowercase letters, numbers, and underscores:
- `tileset_grassland.json` + `tileset_grassland.png`
- `font_ui_16pt.json` + `font_ui_16pt.png`
- `sound_explosion_01.ogg`
- `model_character_hero.gltf`

### Versioning
Assets may include version information in their metadata when applicable.
Check individual asset documentation for specific version details.

## API Reference
For programmatic access to assets, see the [API Reference](api_reference.md).

## Support and Troubleshooting
For issues with assets, please check:
1. Asset validation reports (`validate_assets.py`)
2. Pipeline logs (`assets/logs/`)
3. Statistics and analysis tools (`stats_assets.py`, `analyze_assets.py`)

---
*This documentation was automatically generated by the naRou asset pipeline.*
"""
        
        main_file = os.path.join(docs_dir, "index.md")
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        stats['files_generated'] += 1
        
        # Generate additional documentation files
        additional_docs = [
            ("build_process.md", """# Asset Pipeline Build Process

## Overview
The naRou asset pipeline processes assets through several stages to convert source assets into optimized game-ready formats.

## Stages
1. **Source Validation** - Checking source assets for correctness and completeness
2. **Tileset Processing** - Generating texture atlases from tile collections
3. **Font Processing** - Creating bitmap font atlases from source fonts
4. **Sound Processing** - Converting and optimizing audio files
5. **Model Processing** - Optimizing and converting 3D models
6. **Optimization Pass** - Applying additional optimizations for size/performance
7. **Packaging** - Preparing final asset bundles for deployment
8. **Output Validation** - Verifying that all assets meet quality standards

## Configuration
The build process is controlled by `asset_pipeline_config.json` which specifies:
- Input/output directories
- Processing parameters for each asset type
- Quality thresholds and optimization settings
- Pipeline behavior options

## Customization
To customize the pipeline:
1. Modify the configuration file
2. Create custom processing scripts in the `tools/` directory
3. Extend the build script (`build_assets.py`) for new asset types"""),
            ("validation.md", """# Asset Validation Procedures

## Overview
Asset validation ensures that all processed assets meet quality standards and are ready for use in games.

## Validation Types
1. **Format Validation** - Checking that assets are in correct file formats
2. **Integrity Validation** - Ensuring files are not corrupted or truncated
3. **Metadata Validation** - Verifying that associated metadata is correct and complete
4. **Quality Validation** - Checking that assets meet quality thresholds
5. **Usage Validation** - Ensuring assets can be loaded and used correctly

## Validation Tools
- `validate_assets.py` - Comprehensive asset validation
- Individual asset validators (built into processing scripts)
- Automated validation during the build process

## Common Issues Detected
- Missing or corrupted files
- Incorrect metadata formatting
- Assets exceeding size limits
- Incompatible file formats
- Texture atlases with poor packing efficiency"""),
            ("deployment.md", """# Asset Deployment Guide

## Overview
This guide covers deploying processed assets to various target environments.

## Deployment Methods
1. **Local Deployment** - Copying assets to local directories
2. **Archive Creation** - Creating ZIP/TAR archives for distribution
3. **Network Transfer** - Using FTP/SFTP to transfer assets to servers
4. **Cloud Storage** - Uploading to cloud storage services (AWS S3, etc.)
5. **Content Delivery Networks** - Distributing via CDNs for global access

## Deployment Tools
- `deploy_assets.py` - Main deployment script with multiple methods
- `create_archive.py` - Archive creation utilities
- Custom deployment scripts for specific platforms

## Pre-Deployment Checklist
1. [ ] All assets have been validated
2. [ ] Optimization passes have been completed
3. [ ] File sizes are within expected ranges
4. [ ] Required metadata is present and correct
5. [ ] License compliance verified for third-party assets
6. [ ] Backup of current deployment created

## Post-Deployment Verification
1. [ ] Verify all files were transferred correctly
2. [ ] Check that deployed assets match source in content (accounting for optimization)
3. [ ] Test loading and rendering of key assets
4. [ ] Monitor for any errors in initial usage"""),
            ("configuration.md", """# Asset Pipeline Configuration Reference

## Configuration File
The asset pipeline uses `asset_pipeline_config.json` for all configuration settings.

## Configuration Sections

### Directories
Specifies input and output locations for all asset types:
```json
{
  "directories": {
    "source": "assets/source",
    "output": "assets/build",
    "temp": "assets/temp",
    "cache": "assets/cache",
    "logs": "assets/logs"
  }
}
```

### Tileset Configuration
Controls tileset generation and optimization:
```json
{
  "tileset": {
    "default_size": 32,
    "sizes": [16, 32, 64],
    "padding": 1,
    "max_atlas_size": 2048,
    "formats": ["png"],
    "compression": {
      "enabled": true,
      "level": 6
    }
  }
}
```

### Font Configuration
Controls font atlas generation:
```json
{
  "font": {
    "default_size": 16,
    "sizes": [8, 16, 24, 32],
    "padding": 2,
    "character_set": "ASCII",
    "formats": ["png"]
  }
}
```

### Sound Configuration
Controls audio processing and optimization:
```json
{
  "sound": {
    "sample_rate": 44100,
    "bit_depth": 16,
    "channels": 2,
    "formats": ["ogg", "mp3"],
    "quality": {
      "music": {"bitrate": "192k", "vbr": true},
      "sfx": {"bitrate": "128k", "vbr": false}
    },
    "conversion": {
      "ogg_quality": 5,
      "mp3_quality": 2
    }
  }
}
```

### Model Configuration
Controls 3D model processing:
```json
{
  "models": {
    "formats": ["gltf", "glb", "obj"],
    "optimization": {
      "vertex_cache_optimization": true,
      "overdraw_optimization": true,
      "vertex_compression": true,
      "texture_compression": true
    },
    "validation": {
      "check_winding": true,
      "check_normals": true,
      "check_uvs": true,
      "check_materials": true
    }
  }
}
```

### Pipeline Settings
Controls overall pipeline behavior:
```json
{
  "pipeline": {
    "steps": [
      "validate_source",
      "process_tilesets",
      "process_fonts",
      "process_sounds",
      "process_models",
      "optimize_assets",
      "package_assets",
      "validate_output"
    ],
    "parallel_processing": true,
    "max_workers": 4,
    "continue_on_error": false
  }
}
```

## Environment Variables
The following environment variables can override configuration settings:
- `ASSET_PIPELINE_CONFIG`: Path to configuration file
- `ASSET_SOURCE_DIR`: Override source directory
- `ASSET_OUTPUT_DIR`: Override output directory"""),
            ("api_reference.md", """# Asset Pipeline API Reference

## Overview
This document describes the programmatic interfaces available for working with the naRou asset pipeline.

## Core Modules

### Asset Pipeline Manager
The main interface for coordinating asset processing operations.

```javascript
// Example usage (conceptual - actual implementation language may vary)
const pipeline = new AssetPipelineManager(config);

async function buildAssets() {{
    try {{
        await pipeline.validateSource();
        await pipeline.processTilesets();
        await pipeline.processFonts();
        await pipeline.processSounds();
        await pipeline.processModels();
        await pipeline.optimizeAssets();
        await pipeline.packageAssets();
        await pipeline.validateOutput();
        console.log("Asset pipeline completed successfully!");
    }} catch (error) {{
        console.error("Asset pipeline failed:", error);
        throw error;
    }}
}}
```

### Asset Types
Each asset type has specific interfaces for loading and usage:

#### Tilesets
```javascript
// Loading a tileset
const tileset = await assetLoader.loadTileset("tileset_grassland");

// Getting tile UV coordinates
const uv = tileset.getTileUV(42); // Tile index 42
const sprite = new Sprite(tileset.texture, uv.u, uv.v, uv.width, uv.height);
```

#### Fonts
```javascript
// Loading a font
const font = await assetLoader.loadFont("font_ui_16pt");

// Rendering text
const renderer = new FontRenderer(font);
renderer.renderText("Hello, World!", 100, 100, 24);
```

#### Sounds
```javascript
// Loading a sound
const sound = await assetLoader.loadSound("sound_explosion_01");

// Playing a sound
const audio = audioManager.playSound("sound_explosion_01", {{ volume: 0.8, loop: false }});
```

#### Models
```javascript
// Loading a model
const model = await assetLoader.loadModel("model_character_hero");

// Rendering a model
const transform = new Transform();
transform.position.set(0, 1.5, 0);
transform.rotation.y = Math.PI / 4; // 90 degrees
renderer.renderModel(model, transform);
```

## Error Handling
All pipeline methods return promises that reject with detailed error information:
- `ValidationError`: Asset failed validation checks
- `ProcessingError`: Error during asset processing
- `IOError`: Error reading/writing files
- `ConfigurationError`: Invalid or missing configuration

## Events
The pipeline emits events during processing:
- `asset_processed`: Fired when an individual asset is processed
- `stage_completed`: Fired when a pipeline stage completes
- `pipeline_completed`: Fired when the entire pipeline finishes
- `pipeline_failed`: Fired when the pipeline encounters an error

## Configuration Access
Configuration can be accessed through the pipeline's config property:
```javascript
const maxAtlasSize = pipeline.config.tileset.max_atlas_size;
const workerCount = pipeline.config.pipeline.max_workers;
```

        ]"""),
        ]

        
        for filename, content in additional_docs:
            file_path = os.path.join(docs_dir, filename)
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                stats['files_generated'] += 1
            except Exception as e:
                stats['errors'].append(f"Error generating {filename}: {e}")
        
    except Exception as e:
        stats['errors'].append(f"Error generating overall documentation: {e}")
    
    return stats


def generate_documentation(config: Dict) -> Dict:
    """Generate documentation for all asset types."""
    docs = {
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'results': {}
    }
    
    # Generate documentation for each asset type
    doc_generators = [
        ('tilesets', 'tilesets', generate_tileset_docs),
        ('fonts', 'fonts', generate_font_docs),
        ('sounds', 'sounds', generate_sound_docs),
        ('models', 'models', generate_model_docs)
    ]
    
    for doc_name, dir_key, generator_func in doc_generators:
        dir_path = os.path.join(config['directories']['output'], dir_key)
        docs_dir = os.path.join(config['directories']['output'], 'docs', doc_name)
        print(f"Generating {doc_name} documentation in: {docs_dir}")
        docs['results'][doc_name] = generator_func(dir_path, docs_dir, config)
    
    # Generate overall documentation
    print("Generating overall pipeline documentation...")
    docs['results']['overall'] = generate_overall_docs(config)
    
    # Generate summary
    docs['summary'] = {
        'total_docs_generated': sum(
            result.get('files_generated', 0) 
            for result in docs['results'].values()
        ),
        'total_errors': sum(
            len(result.get('errors', [])) 
            for result in docs['results'].values()
        ),
        'assets_documented': sum(
            result.get('assets_documented', 0) 
            for result in docs['results'].values() 
            if isinstance(result, dict) and 'assets_documented' in result
        )
    }
    
    return docs


def save_documentation(docs: Dict, output_path: str) -> bool:
    """Save documentation to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(docs, f, indent=2)
        print(f"Documentation saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving documentation: {e}")
        return False


def print_documentation_summary(docs: Dict, verbose: bool = False):
    """Print a formatted summary of the documentation generation."""
    print(f"\n{'='*70}")
    print(f"ASSET DOCUMENTATION GENERATION SUMMARY")
    print(f"{'='*70}")
    print(f"Timestamp: {docs['datetime']}")
    
    print(f"\nSUMMARY:")
    summary = docs.get('summary', {})
    print(f"  Total Documentation Files Generated: {summary.get('total_docs_generated', 0)}")
    print(f"  Total Errors Encountered: {summary.get('total_errors', 0)}")
    print(f"  Total Assets Documented: {summary.get('assets_documented', 0)}")
    
    print(f"\nDETAILED RESULTS BY ASSET TYPE:")
    for asset_type, result in docs.get('results', {}).items():
        if isinstance(result, dict):
            print(f"\n  {asset_type.upper()}:")
            if 'assets_documented' in result:
                print(f"    Assets Documented: {result.get('assets_documented', 0)}")
            print(f"    Files Generated: {result.get('files_generated', 0)}")
            print(f"    Errors: {len(result.get('errors', []))}")
            
            if result.get('errors') and verbose:
                print(f"    Error Details:")
                for error in result['errors'][:3]:
                    print(f"      - {error}")
                if len(result['errors']) > 3:
                    print(f"      ... and {len(result['errors']) - 3} more errors")
        else:
            print(f"\n  {asset_type.upper()}: {result}")


def main():
    parser = argparse.ArgumentParser(description='Generate documentation for assets')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--output', default=None,
                       help='Output file for documentation (JSON)')
    parser.add_argument('--assets', nargs='+',
                       choices=['tilesets', 'fonts', 'sounds', 'models', 'all'],
                       default=['all'], help='Asset types to document')
    parser.add_argument('--summary-only', action='store_true',
                       help='Print only summary, not full JSON output')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Determine which assets to document
    if args.assets == ['all']:
        assets_to_document = ['tilesets', 'fonts', 'sounds', 'models']
    else:
        assets_to_document = args.assets
    
    # Generate documentation
    docs = generate_documentation(config)
    
    # Filter results if needed
    if args.assets != ['all']:
        filtered_results = {
            k: v for k, v in docs['results'].items() 
            if k in assets_to_document
        }
        docs['results'] = filtered_results
        
        # Recalculate summary
        total_files_generated = sum(
            result.get('files_generated', 0) 
            for result in docs['results'].values()
        )
        total_errors = sum(
            len(result.get('errors', [])) 
            for result in docs['results'].values()
        )
        total_assets_documented = sum(
            result.get('assets_documented', 0) 
            for result in docs['results'].values() 
            if isinstance(result, dict) and 'assets_documented' in result
        )
        
        docs['summary'] = {
            'total_docs_generated': total_files_generated,
            'total_errors': total_errors,
            'total_assets_documented': total_assets_documented
        }
    
    # Save or output results
    if args.output:
        if not save_documentation(docs, args.output):
            sys.exit(1)
    
    if not args.summary_only:
        # Print full JSON
        print(json.dumps(docs, indent=2))
    else:
        # Print formatted summary
        print_documentation_summary(docs, verbose=args.verbose)
    
    sys.exit(0)


if __name__ == '__main__':
    main()