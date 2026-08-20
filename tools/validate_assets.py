#!/usr/bin/env python3
"""
Asset validation script for validating processed assets.
Checks integrity, format compliance, and quality of all asset types.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def validate_tileset(tile_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Validate a tileset atlas and its metadata."""
    issues = []
    
    if not os.path.exists(tile_path):
        issues.append(f"Tileset file does not exist: {tile_path}")
        return False, issues
    
    # Check for corresponding JSON metadata
    json_path = tile_path.rsplit('.', 1)[0] + '.json'
    if not os.path.exists(json_path):
        issues.append(f"Missing metadata file: {json_path}")
    else:
        try:
            with open(json_path, 'r') as f:
                metadata = json.load(f)
            
            # Validate required fields
            required_fields = ['tile_size', 'atlas_width', 'atlas_height', 'tiles']
            for field in required_fields:
                if field not in metadata:
                    issues.append(f"Missing required field in metadata: {field}")
            
            # Validate tile size against the configured set of allowed sizes.
            allowed_sizes = config['tileset'].get('sizes', [config['tileset']['default_size']])
            if 'tile_size' in metadata and metadata['tile_size'] not in allowed_sizes:
                issues.append(f"Tile size {metadata['tile_size']} not in allowed sizes {allowed_sizes}")

            # Validate declared atlas dimensions match the actual PNG.
            if {'atlas_width', 'atlas_height'} <= set(metadata):
                try:
                    from PIL import Image
                    with Image.open(tile_path) as im:
                        if (im.width, im.height) != (metadata['atlas_width'], metadata['atlas_height']):
                            issues.append(
                                f"Atlas dimension mismatch: png={im.size} "
                                f"meta=({metadata['atlas_width']}, {metadata['atlas_height']})"
                            )
                        if im.width == 0 or im.height == 0:
                            issues.append("Atlas image has zero dimensions")
                except Exception as e:
                    issues.append(f"Could not read atlas image: {e}")
                
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in metadata: {e}")
        except Exception as e:
            issues.append(f"Error reading metadata: {e}")
    
    # Validate image file is non-empty.
    try:
        file_size = os.path.getsize(tile_path)
        if file_size == 0:
            issues.append("Tileset image file is empty")
    except Exception as e:
        issues.append(f"Error reading tileset image: {e}")
    
    return len(issues) == 0, issues


def validate_font(font_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Validate a font atlas and its metadata."""
    issues = []
    
    if not os.path.exists(font_path):
        issues.append(f"Font file does not exist: {font_path}")
        return False, issues
    
    # Check for corresponding JSON metadata
    json_path = font_path.rsplit('.', 1)[0] + '.json'
    if not os.path.exists(json_path):
        issues.append(f"Missing font metadata file: {json_path}")
    else:
        try:
            with open(json_path, 'r') as f:
                metadata = json.load(f)
            
            # Validate required fields
            required_fields = ['font_size', 'atlas_width', 'atlas_height', 'metrics']
            for field in required_fields:
                if field not in metadata:
                    issues.append(f"Missing required field in font metadata: {field}")
                    
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in font metadata: {e}")
        except Exception as e:
            issues.append(f"Error reading font metadata: {e}")
    
    # Validate image file
    try:
        file_size = os.path.getsize(font_path)
        if file_size == 0:
            issues.append("Font image file is empty")
    except Exception as e:
        issues.append(f"Error reading font image: {e}")
    
    return len(issues) == 0, issues


def validate_sound(sound_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Validate a sound file."""
    issues = []
    
    if not os.path.exists(sound_path):
        issues.append(f"Sound file does not exist: {sound_path}")
        return False, issues
    
    # Check file size
    try:
        file_size = os.path.getsize(sound_path)
        if file_size == 0:
            issues.append("Sound file is empty")
    except Exception as e:
        issues.append(f"Error reading sound file size: {e}")
    
    # Validate format
    ext = Path(sound_path).suffix.lower()
    allowed_formats = config['sound']['formats']
    if ext[1:] not in allowed_formats:  # Remove the dot
        issues.append(f"Unsupported sound format: {ext}. Allowed: {allowed_formats}")
    
    return len(issues) == 0, issues


def validate_model(model_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Validate a 3D model file."""
    issues = []
    
    if not os.path.exists(model_path):
        issues.append(f"Model file does not exist: {model_path}")
        return False, issues
    
    # Check file size
    try:
        file_size = os.path.getsize(model_path)
        if file_size == 0:
            issues.append("Model file is empty")
    except Exception as e:
        issues.append(f"Error reading model file size: {e}")
    
    # Validate format
    ext = Path(model_path).suffix.lower()
    allowed_formats = config['models']['formats']
    if ext[1:] not in allowed_formats:  # Remove the dot
        issues.append(f"Unsupported model format: {ext}. Allowed: {allowed_formats}")
    
    return len(issues) == 0, issues


def validate_manifest(manifest_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Validate the asset manifest."""
    issues = []
    
    if not os.path.exists(manifest_path):
        issues.append(f"Manifest file does not exist: {manifest_path}")
        return False, issues
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check required fields
        required_fields = ['version', 'generated_at', 'directories', 'asset_counts']
        for field in required_fields:
            if field not in manifest:
                issues.append(f"Missing required field in manifest: {field}")
        
        # Validate asset counts are non-negative integers
        if 'asset_counts' in manifest:
            for asset_type, count in manifest['asset_counts'].items():
                if not isinstance(count, int) or count < 0:
                    issues.append(f"Invalid asset count for {asset_type}: {count}")
                    
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON in manifest: {e}")
    except Exception as e:
        issues.append(f"Error reading manifest: {e}")
    
    return len(issues) == 0, issues


def validate_directory(directory: str, config: Dict, asset_type: str) -> Tuple[bool, List[str], Dict]:
    """Validate all assets of a specific type in a directory."""
    if not os.path.exists(directory):
        return False, [f"Directory does not exist: {directory}"], {}
    
    all_issues = []
    stats = {
        'total_files': 0,
        'valid_files': 0,
        'invalid_files': 0,
        'files': []
    }
    
    # Get validation function based on asset type
    validators = {
        'tilesets': validate_tileset,
        'fonts': validate_font,
        'sounds': validate_sound,
        'models': validate_model
    }
    
    validator = validators.get(asset_type)
    if not validator:
        return False, [f"No validator for asset type: {asset_type}"], {}
    
    # Supported extensions for each type
    extensions = {
        'tilesets': ['.png'],
        'fonts': ['.png'],
        'sounds': ['.ogg', '.mp3', '.wav'],
        'models': ['.gltf', '.glb', '.obj', '.fbx']
    }
    
    allowed_exts = extensions.get(asset_type, [])
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Check extension
            if allowed_exts and not any(file.lower().endswith(ext) for ext in allowed_exts):
                continue
            
            stats['total_files'] += 1
            
            is_valid, issues = validator(file_path, config)
            file_info = {
                'path': file_path,
                'valid': is_valid,
                'issues': issues
            }
            stats['files'].append(file_info)
            
            if is_valid:
                stats['valid_files'] += 1
            else:
                stats['invalid_files'] += 1
                all_issues.extend([f"{file_path}: {issue}" for issue in issues])
    
    return len(all_issues) == 0, all_issues, stats


def validate_tileset_coverage(assets_dir: str, config: Dict) -> Tuple[bool, List[str]]:
    """Verify every tile defined in a tileset definition exists in the atlas.

    Implements the plan requirement: "定義済み全タイルIDがアトラスに存在するか".
    """
    issues: List[str] = []

    # Locate the tileset definition(s).
    def_dirs = [
        os.path.join(config['directories']['source'], 'tilesets'),
        os.path.join('assets', 'source', 'tilesets'),
    ]
    def_files: List[str] = []
    for d in def_dirs:
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.json'):
                    def_files.append(os.path.join(d, f))

    if not def_files:
        issues.append("No tileset definition files found to validate against")
        return False, issues

    for def_path in def_files:
        try:
            with open(def_path, 'r') as fh:
                definition = json.load(fh)
        except Exception as e:
            issues.append(f"Could not read tileset definition {def_path}: {e}")
            continue

        defined = definition.get('tiles', {})
        if not isinstance(defined, dict) or not defined:
            issues.append(f"Tileset definition {def_path} defines no tiles")
            continue

        # The generated atlas JSON for the definition's tile_size.
        tile_size = int(definition.get('tile_size', config['tileset']['default_size']))
        atlas_json = os.path.join(assets_dir, f"tileset_{tile_size}x{tile_size}.json")
        if not os.path.exists(atlas_json):
            issues.append(f"Missing generated atlas metadata: {atlas_json}")
            continue

        try:
            with open(atlas_json, 'r') as fh:
                atlas = json.load(fh)
        except Exception as e:
            issues.append(f"Could not read atlas metadata {atlas_json}: {e}")
            continue

        atlas_tiles = atlas.get('tiles', {})
        for name, tdef in defined.items():
            if name not in atlas_tiles:
                issues.append(f"Tile '{name}' defined in {os.path.basename(def_path)} "
                              f"is missing from {os.path.basename(atlas_json)}")
                continue
            expected_frames = int(tdef.get('frames', 1))
            actual_frames = int(atlas_tiles[name].get('frames', 1))
            if expected_frames != actual_frames:
                issues.append(f"Tile '{name}' frame count mismatch: "
                              f"def={expected_frames} atlas={actual_frames}")

    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description='Validate processed assets')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--assets-dir', default=None,
                       help='Directory containing processed assets (overrides config)')
    parser.add_argument('--types', nargs='+',
                       choices=['tilesets', 'fonts', 'sounds', 'models', 'manifest', 'all'],
                       default=['all'], help='Asset types to validate')
    parser.add_argument('--output', default=None,
                       help='Output file for validation report (JSON)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Determine assets directory
    if args.assets_dir:
        assets_dir = args.assets_dir
    else:
        assets_dir = config['directories']['output']
    
    # Determine which types to validate
    if args.types == ['all']:
        types_to_validate = ['tilesets', 'fonts', 'sounds', 'models', 'manifest']
    else:
        types_to_validate = args.types
    
    # Run validation
    all_valid = True
    validation_results = {
        'timestamp': time.time(),
        'assets_directory': assets_dir,
        'validations': {},
        'summary': {
            'total_validations': len(types_to_validate),
            'passed_validations': 0,
            'failed_validations': 0
        }
    }
    
    for asset_type in types_to_validate:
        if args.verbose:
            print(f"Validating {asset_type}...")
        
        valid = False
        issues = []
        stats = {}
        
        try:
            if asset_type == 'manifest':
                manifest_path = os.path.join(assets_dir, 'manifest.json')
                valid, issues = validate_manifest(manifest_path, config)
                stats = {}  # Manifest validation doesn't produce file stats
            elif asset_type == 'tilesets':
                # Atlas PNG/JSON files live directly under assets_dir.
                valid, issues, stats = validate_directory(assets_dir, config, 'tilesets')
                cov_valid, cov_issues = validate_tileset_coverage(assets_dir, config)
                if not cov_valid:
                    valid = False
                    issues.extend(cov_issues)
            else:
                asset_dir = os.path.join(assets_dir, asset_type)
                valid, issues, stats = validate_directory(asset_dir, config, asset_type)
            
            validation_results['validations'][asset_type] = {
                'valid': valid,
                'issues': issues,
                'stats': stats
            }
            
            if valid:
                validation_results['summary']['passed_validations'] += 1
                if args.verbose:
                    print(f"  ✓ {asset_type}: PASSED")
            else:
                validation_results['summary']['failed_validations'] += 1
                all_valid = False
                if args.verbose:
                    print(f"  ✗ {asset_type}: FAILED")
                    for issue in issues[:5]:  # Show first 5 issues
                        print(f"    - {issue}")
                    if len(issues) > 5:
                        print(f"    ... and {len(issues) - 5} more issues")
        
        except Exception as e:
            validation_results['validations'][asset_type] = {
                'valid': False,
                'issues': [f"Validation error: {e}"],
                'stats': {}
            }
            validation_results['summary']['failed_validations'] += 1
            all_valid = False
            if args.verbose:
                print(f"  ✗ {asset_type}: ERROR - {e}")
    
    # Output results
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(validation_results, f, indent=2)
            print(f"Validation report saved to: {args.output}")
        except Exception as e:
            print(f"Error writing validation report: {e}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"ASSET VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Assets directory: {assets_dir}")
    print(f"Total validations: {validation_results['summary']['total_validations']}")
    print(f"Passed: {validation_results['summary']['passed_validations']}")
    print(f"Failed: {validation_results['summary']['failed_validations']}")
    
    if not all_valid:
        print("\nVALIDATION FAILED")
        sys.exit(1)
    else:
        print("\nALL VALIDATIONS PASSED")
        sys.exit(0)


if __name__ == '__main__':
    import time
    main()