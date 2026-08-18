#!/usr/bin/env python3
"""
Asset validation script for validating processed assets.
Checks integrity, format compliance, and quality of all asset types.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess


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
            required_fields = ['tile_size', 'atlas_width', 'atlas_height', 'tile_count']
            for field in required_fields:
                if field not in metadata:
                    issues.append(f"Missing required field in metadata: {field}")
            
            # Validate tile size
            expected_size = config['tileset']['default_size']
            if 'tile_size' in metadata and metadata['tile_size'] != expected_size:
                issues.append(f"Tile size mismatch: expected {expected_size}, got {metadata['tile_size']}")
                
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in metadata: {e}")
        except Exception as e:
            issues.append(f"Error reading metadata: {e}")
    
    # Validate image file
    try:
        # Would use PIL to validate image in real implementation
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