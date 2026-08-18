#!/usr/bin/env python3
"""
Asset statistics script for generating comprehensive statistics about assets.
Analyzes asset collections, generates reports, and provides insights.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import collections


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def analyze_tileset_collection(tileset_dir: str, config: Dict) -> Dict:
    """Analyze a collection of tilesets."""
    stats = {
        'total_tilesets': 0,
        'total_tiles': 0,
        'total_size_bytes': 0,
        'size_distribution': {},
        'tile_size_distribution': {},
        'format_distribution': {},
        'largest_tileset': None,
        'smallest_tileset': None,
        'average_tiles_per_tileset': 0,
        'duplicate_tiles': 0
    }
    
    if not os.path.exists(tileset_dir):
        return stats
    
    tilesets = []
    all_tile_signatures = []  # For duplicate detection
    
    for root, dirs, files in os.walk(tileset_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        tile_count = metadata.get('tile_count', 0)
                        total_size = os.path.getsize(json_path) + os.path.getsize(png_path)
                        
                        tileset_info = {
                            'name': os.path.splitext(file)[0],
                            'path': json_path,
                            'png_path': png_path,
                            'tile_count': tile_count,
                            'total_size': total_size,
                            'tile_size': metadata.get('tile_size', 0),
                            'atlas_width': metadata.get('atlas_width', 0),
                            'atlas_height': metadata.get('atlas_height', 0)
                        }
                        
                        tilesets.append(tileset_info)
                        stats['total_tilesets'] += 1
                        stats['total_tiles'] += tile_count
                        stats['total_size_bytes'] += total_size
                        
                        # Track tile size distribution
                        tile_size = metadata.get('tile_size', 0)
                        stats['tile_size_distribution'][str(tile_size)] = stats['tile_size_distribution'].get(str(tile_size), 0) + 1
                        
                        # Track atlas size categories
                        area = metadata.get('atlas_width', 0) * metadata.get('atlas_height', 0)
                        if area < 256*256:
                            size_cat = 'small (<256px)'
                        elif area < 512*512:
                            size_cat = 'medium (<512px)'
                        elif area < 1024*1024:
                            size_cat = 'large (<1024px)'
                        else:
                            size_cat = 'very large (>=1024px)'
                        stats['size_distribution'][size_cat] = stats['size_distribution'].get(size_cat, 0) + 1
                        
                        # For duplicate detection, create a signature based on tile count and sizes
                        signature = f"{tile_count}_{metadata.get('tile_size', 0)}_{metadata.get('atlas_width', 0)}x{metadata.get('atlas_height', 0)}"
                        all_tile_signatures.append(signature)
                        
                    except Exception:
                        pass  # Skip invalid tilesets
    
    # Calculate averages
    if stats['total_tilesets'] > 0:
        stats['average_tiles_per_tileset'] = stats['total_tiles'] / stats['total_tilesets']
    
    # Find largest and smallest
    if tilesets:
        largest = max(tilesets, key=lambda x: x['total_size'])
        smallest = min(tilesets, key=lambda x: x['total_size'])
        stats['largest_tileset'] = {
            'name': largest['name'],
            'size_bytes': largest['total_size'],
            'tile_count': largest['tile_count']
        }
        stats['smallest_tileset'] = {
            'name': smallest['name'],
            'size_bytes': smallest['total_size'],
            'tile_count': smallest['tile_count']
        }
    
    # Count duplicates
    counter = collections.Counter(all_tile_signatures)
    stats['duplicate_tiles'] = sum(count - 1 for count in counter.values() if count > 1)
    
    return stats


def analyze_font_collection(font_dir: str, config: Dict) -> Dict:
    """Analyze a collection of font atlases."""
    stats = {
        'total_fonts': 0,
        'total_characters': 0,
        'total_size_bytes': 0,
        'font_size_distribution': {},
        'character_coverage': {},
        'largest_font': None,
        'smallest_font': None,
        'average_chars_per_font': 0
    }
    
    if not os.path.exists(font_dir):
        return stats
    
    fonts = []
    all_chars = set()
    
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        char_count = len(metadata.get('metrics', {}))
                        total_size = os.path.getsize(json_path) + os.path.getsize(png_path)
                        
                        font_info = {
                            'name': os.path.splitext(file)[0],
                            'path': json_path,
                            'png_path': png_path,
                            'character_count': char_count,
                            'total_size': total_size,
                            'font_size': metadata.get('font_size', 0),
                            'atlas_width': metadata.get('atlas_width', 0),
                            'atlas_height': metadata.get('atlas_height', 0)
                        }
                        
                        fonts.append(font_info)
                        stats['total_fonts'] += 1
                        stats['total_characters'] += char_count
                        stats['total_size_bytes'] += total_size
                        
                        # Track font size distribution
                        font_size = metadata.get('font_size', 0)
                        stats['font_size_distribution'][str(font_size)] = stats['font_size_distribution'].get(str(font_size), 0) + 1
                        
                        # Collect all characters for coverage analysis
                        metrics = metadata.get('metrics', {})
                        all_chars.update(metrics.keys())
                        
                    except Exception:
                        pass  # Skip invalid fonts
    
    # Calculate averages
    if stats['total_fonts'] > 0:
        stats['average_chars_per_font'] = stats['total_characters'] / stats['total_fonts']
    
    # Character coverage (ASCII printable)
    ascii_printable = set(chr(i) for i in range(32, 127))
    covered_chars = all_chars & ascii_printable
    stats['character_coverage'] = {
        'ascii_printable_total': len(ascii_printable),
        'covered': len(covered_chars),
        'percentage': (len(covered_chars) / len(ascii_printable)) * 100 if ascii_printable else 0,
        'missing_chars': sorted(list(ascii_printable - covered_chars))
    }
    
    # Find largest and smallest
    if fonts:
        largest = max(fonts, key=lambda x: x['total_size'])
        smallest = min(fonts, key=lambda x: x['total_size'])
        stats['largest_font'] = {
            'name': largest['name'],
            'size_bytes': largest['total_size'],
            'character_count': largest['character_count']
        }
        stats['smallest_font'] = {
            'name': smallest['name'],
            'size_bytes': smallest['total_size'],
            'character_count': smallest['character_count']
        }
    
    return stats


def analyze_sound_collection(sound_dir: str, config: Dict) -> Dict:
    """Analyze a collection of sound files."""
    stats = {
        'total_sounds': 0,
        'total_duration_seconds': 0,
        'total_size_bytes': 0,
        'duration_distribution': {},
        'format_distribution': {},
        'bitrate_distribution': {},
        'largest_sound': None,
        'smallest_sound': None,
        'average_duration': 0
    }
    
    if not os.path.exists(sound_dir):
        return stats
    
    sounds = []
    extensions = ['.ogg', '.mp3', '.wav', '.flac']
    
    for root, dirs, files in os.walk(sound_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                sound_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(sound_path)
                    
                    # Try to get metadata (would use audio library in real implementation)
                    # For now, use placeholder values
                    duration = 0.0  # Would extract from file
                    
                    sound_info = {
                        'name': file,
                        'path': sound_path,
                        'size_bytes': file_size,
                        'duration_seconds': duration,
                        'format': Path(file).suffix.lower()[1:],
                        'bitrate': 0  # Would calculate
                    }
                    
                    sounds.append(sound_info)
                    stats['total_sounds'] += 1
                    stats['total_size_bytes'] += file_size
                    stats['total_duration_seconds'] += duration
                    
                    # Track format distribution
                    fmt = sound_info['format']
                    stats['format_distribution'][fmt] = stats['format_distribution'].get(fmt, 0) + 1
                    
                    # Track duration categories
                    if duration < 10:
                        dur_cat = 'short (<10s)'
                    elif duration < 60:
                        dur_cat = 'medium (<1min)'
                    elif duration < 300:
                        dur_cat = 'long (<5min)'
                    else:
                        dur_cat = 'very long (>=5min)'
                    stats['duration_distribution'][dur_cat] = stats['duration_distribution'].get(dur_cat, 0) + 1
                    
                except Exception:
                    pass  # Skip invalid sound files
    
    # Calculate averages
    if stats['total_sounds'] > 0:
        stats['average_duration'] = stats['total_duration_seconds'] / stats['total_sounds']
    
    # Find largest and smallest
    if sounds:
        largest = max(sounds, key=lambda x: x['size_bytes'])
        smallest = min(sounds, key=lambda x: x['size_bytes'])
        stats['largest_sound'] = {
            'name': largest['name'],
            'size_bytes': largest['size_bytes'],
            'duration_seconds': largest['duration_seconds']
        }
        stats['smallest_sound'] = {
            'name': smallest['name'],
            'size_bytes': smallest['size_bytes'],
            'duration_seconds': smallest['duration_seconds']
        }
    
    return stats


def analyze_model_collection(model_dir: str, config: Dict) -> Dict:
    """Analyze a collection of 3D models."""
    stats = {
        'total_models': 0,
        'total_vertices': 0,
        'total_faces': 0,
        'total_size_bytes': 0,
        'vertex_distribution': {},
        'format_distribution': {},
        'complexity_distribution': {},
        'largest_model': None,
        'smallest_model': None,
        'average_vertices_per_model': 0,
        'average_faces_per_model': 0
    }
    
    if not os.path.exists(model_dir):
        return stats
    
    models = []
    extensions = ['.obj', '.fbx', '.gltf', '.glb', '.dae', '.3ds', '.blend', '.ply', '.stl']
    
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                model_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(model_path)
                    
                    # Try to get metadata (would use assimp or similar in real implementation)
                    # For now, use placeholder values or simple parsing
                    vertex_count = 0
                    face_count = 0
                    
                    if file.endswith('.obj'):
                        # Simple OBJ parsing for vertex/face count
                        try:
                            with open(model_path, 'r') as f:
                                for line in f:
                                    if line.startswith('v '):
                                        vertex_count += 1
                                    elif line.startswith('f '):
                                        face_count += 1
                        except Exception:
                            pass
                    
                    model_info = {
                        'name': file,
                        'path': model_path,
                        'size_bytes': file_size,
                        'vertex_count': vertex_count,
                        'face_count': face_count,
                        'format': Path(file).suffix.lower()[1:]
                    }
                    
                    models.append(model_info)
                    stats['total_models'] += 1
                    stats['total_vertices'] += vertex_count
                    stats['total_faces'] += face_count
                    stats['total_size_bytes'] += file_size
                    
                    # Track format distribution
                    fmt = model_info['format']
                    stats['format_distribution'][fmt] = stats['format_distribution'].get(fmt, 0) + 1
                    
                    # Track vertex count distribution
                    if vertex_count < 100:
                        vert_cat = 'low (<100 verts)'
                    elif vertex_count < 1000:
                        vert_cat = 'medium (<1k verts)'
                    elif vertex_count < 10000:
                        vert_cat = 'high (<10k verts)'
                    else:
                        vert_cat = 'very high (>=10k verts)'
                    stats['vertex_distribution'][vert_cat] = stats['vertex_distribution'].get(vert_cat, 0) + 1
                    
                    # Track complexity (faces as proxy)
                    if face_count < 100:
                        complex_cat = 'simple (<100 faces)'
                    elif face_count < 1000:
                        complex_cat = 'moderate (<1k faces)'
                    elif face_count < 10000:
                        complex_cat = 'complex (<10k faces)'
                    else:
                        complex_cat = 'very complex (>=10k faces)'
                    stats['complexity_distribution'][complex_cat] = stats['complexity_distribution'].get(complex_cat, 0) + 1
                    
                except Exception:
                    pass  # Skip invalid model files
    
    # Calculate averages
    if stats['total_models'] > 0:
        stats['average_vertices_per_model'] = stats['total_vertices'] / stats['total_models']
        stats['average_faces_per_model'] = stats['total_faces'] / stats['total_models']
    
    # Find largest and smallest
    if models:
        largest = max(models, key=lambda x: x['size_bytes'])
        smallest = min(models, key=lambda x: x['size_bytes'])
        stats['largest_model'] = {
            'name': largest['name'],
            'size_bytes': largest['size_bytes'],
            'vertex_count': largest['vertex_count'],
            'face_count': largest['face_count']
        }
        stats['smallest_model'] = {
            'name': smallest['name'],
            'size_bytes': smallest['size_bytes'],
            'vertex_count': smallest['vertex_count'],
            'face_count': smallest['face_count']
        }
    
    return stats


def generate_collection_stats(config: Dict) -> Dict:
    """Generate statistics for all asset collections."""
    stats = {
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'collections': {}
    }
    
    # Analyze each asset type
    collections_to_analyze = [
        ('tilesets', 'tilesets', analyze_tileset_collection),
        ('fonts', 'fonts', analyze_font_collection),
        ('sounds', 'sounds', analyze_sound_collection),
        ('models', 'models', analyze_model_collection)
    ]
    
    for collection_name, dir_key, analyze_func in collections_to_analyze:
        dir_path = os.path.join(config['directories']['output'], dir_key)
        print(f"Analyzing {collection_name} collection in: {dir_path}")
        stats['collections'][collection_name] = analyze_func(dir_path, config)
    
    # Generate summary
    stats['summary'] = {
        'total_collections': len(collections_to_analyze),
        'total_assets': sum(
            stats['collections'].get(coll, {}).get('total_tilesets', 0) +
            stats['collections'].get(coll, {}).get('total_fonts', 0) +
            stats['collections'].get(coll, {}).get('total_sounds', 0) +
            stats['collections'].get(coll, {}).get('total_models', 0)
            for coll, _, _ in collections_to_analyze
        ),
        'total_size_bytes': sum(
            stats['collections'].get(coll, {}).get('total_size_bytes', 0)
            for coll, _, _ in collections_to_analyze
        )
    }
    
    return stats


def save_stats(stats: Dict, output_path: str) -> bool:
    """Save statistics to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Statistics saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving statistics: {e}")
        return False


def print_stats_summary(stats: Dict):
    """Print a formatted summary of the statistics."""
    print(f"\n{'='*70}")
    print(f"ASSET COLLECTION STATISTICS REPORT")
    print(f"{'='*70}")
    print(f"Timestamp: {stats['datetime']}")
    
    print(f"\nSUMMARY:")
    summary = stats.get('summary', {})
    print(f"  Total Collections Analyzed: {summary.get('total_collections', 0)}")
    print(f"  Total Assets: {summary.get('total_assets', 0)}")
    print(f"  Total Size: {summary.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
    
    print(f"\nCOLLECTION BREAKDOWN:")
    for coll_name, coll_stats in stats.get('collections', {}).items():
        print(f"  {coll_name.upper()}:")
        if coll_name == 'tilesets':
            print(f"    Tilesets: {coll_stats.get('total_tilesets', 0)}")
            print(f"    Total Tiles: {coll_stats.get('total_tiles', 0)}")
            print(f"    Size: {coll_stats.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
            if coll_stats.get('largest_tileset'):
                lt = coll_stats['largest_tileset']
                print(f"    Largest: {lt['name']} ({lt['size_bytes']/(1024*1024):.2f} MB, {lt['tile_count']} tiles)")
        elif coll_name == 'fonts':
            print(f"    Fonts: {coll_stats.get('total_fonts', 0)}")
            print(f"    Total Characters: {coll_stats.get('total_characters', 0)}")
            print(f"    Size: {coll_stats.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
            coverage = coll_stats.get('character_coverage', {})
            if coverage:
                print(f"    ASCII Coverage: {coverage.get('percentage', 0):.1f}%")
        elif coll_name == 'sounds':
            print(f"    Sounds: {coll_stats.get('total_sounds', 0)}")
            print(f"    Total Duration: {coll_stats.get('total_duration_seconds', 0):.1f} seconds")
            print(f"    Size: {coll_stats.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
        elif coll_name == 'models':
            print(f"    Models: {coll_stats.get('total_models', 0)}")
            print(f"    Total Vertices: {coll_stats.get('total_vertices', 0):,}")
            print(f"    Total Faces: {coll_stats.get('total_faces', 0):,}")
            print(f"    Size: {coll_stats.get('total_size_bytes', 0) / (1024*1024):.2f} MB")
            print(f"    Avg Vertices/Model: {coll_stats.get('average_vertices_per_model', 0):.1f}")
            print(f"    Avg Faces/Model: {coll_stats.get('average_faces_per_model', 0):.1f}")


def main():
    parser = argparse.ArgumentParser(description='Generate asset collection statistics')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--output', default=None,
                       help='Output file for statistics (JSON)')
    parser.add_argument('--collections', nargs='+',
                       choices=['tilesets', 'fonts', 'sounds', 'models', 'all'],
                       default=['all'], help='Asset collections to analyze')
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
    
    # Determine which collections to analyze
    if args.collections == ['all']:
        collections_to_analyze = ['tilesets', 'fonts', 'sounds', 'models']
    else:
        collections_to_analyze = args.collections
    
    # Generate statistics
    stats = generate_collection_stats(config)
    
    # Filter collections if needed
    if args.collections != ['all']:
        filtered_collections = {
            k: v for k, v in stats['collections'].items() 
            if k in collections_to_analyze
        }
        stats['collections'] = filtered_collections
        
        # Recalculate summary
        total_assets = sum(
            filtered_collections.get(coll, {}).get('total_tilesets', 0) +
            filtered_collections.get(coll, {}).get('total_fonts', 0) +
            filtered_collections.get(coll, {}).get('total_sounds', 0) +
            filtered_collections.get(coll, {}).get('total_models', 0)
            for coll in collections_to_analyze
        )
        total_size = sum(
            filtered_collections.get(coll, {}).get('total_size_bytes', 0)
            for coll in collections_to_analyze
        )
        stats['summary'] = {
            'total_collections': len(collections_to_analyze),
            'total_assets': total_assets,
            'total_size_bytes': total_size
        }
    
    # Save or output results
    if args.output:
        if not save_stats(stats, args.output):
            sys.exit(1)
    
    if not args.summary_only:
        # Print full JSON
        print(json.dumps(stats, indent=2))
    else:
        # Print formatted summary
        print_stats_summary(stats)
    
    sys.exit(0)


if __name__ == '__main__':
    main()