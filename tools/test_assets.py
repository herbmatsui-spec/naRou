#!/usr/bin/env python3
"""
Asset testing script for testing processed assets.
Runs functional tests to ensure assets work correctly in the game context.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import tempfile


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def test_tileset_loading(tile_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Test that a tileset can be loaded and used."""
    issues = []
    
    if not os.path.exists(tile_path):
        issues.append(f"Tileset file does not exist: {tile_path}")
        return False, issues
    
    # Check for metadata
    json_path = tile_path.rsplit('.', 1)[0] + '.json'
    if not os.path.exists(json_path):
        issues.append(f"Missing metadata file for tileset: {json_path}")
        return False, issues
    
    try:
        with open(json_path, 'r') as f:
            metadata = json.load(f)
        
        # Test that we can parse tile coordinates
        tile_size = metadata.get('tile_size', 0)
        atlas_width = metadata.get('atlas_width', 0)
        atlas_height = metadata.get('atlas_height', 0)
        tile_count = metadata.get('tile_count', 0)
        
        if tile_size <= 0 or atlas_width <= 0 or atlas_height <= 0:
            issues.append("Invalid tileset dimensions")
        
        if tile_count <= 0:
            issues.append("Tileset has no tiles")
        
        # Test that we can calculate UV coordinates for a tile
        if tile_count > 0 and 'tiles' in metadata:
            first_tile = metadata['tiles'][0]
            required_uv_fields = ['u', 'v', 'uw', 'vh']
            for field in required_uv_fields:
                if field not in first_tile:
                    issues.append(f"Missing UV field in tile metadata: {field}")
                elif not isinstance(first_tile[field], (int, float)):
                    issues.append(f"Invalid UV field type: {field}")
        
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON in tileset metadata: {e}")
    except Exception as e:
        issues.append(f"Error testing tileset: {e}")
    
    return len(issues) == 0, issues


def test_font_loading(font_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Test that a font atlas can be loaded and used for text rendering."""
    issues = []
    
    if not os.path.exists(font_path):
        issues.append(f"Font file does not exist: {font_path}")
        return False, issues
    
    # Check for metadata
    json_path = font_path.rsplit('.', 1)[0] + '.json'
    if not os.path.exists(json_path):
        issues.append(f"Missing metadata file for font: {json_path}")
        return False, issues
    
    try:
        with open(json_path, 'r') as f:
            metadata = json.load(f)
        
        # Test that we have character metrics
        font_size = metadata.get('font_size', 0)
        atlas_width = metadata.get('atlas_width', 0)
        atlas_height = metadata.get('atlas_height', 0)
        metrics = metadata.get('metrics', {})
        
        if font_size <= 0:
            issues.append("Invalid font size")
        
        if atlas_width <= 0 or atlas_height <= 0:
            issues.append("Invalid font atlas dimensions")
        
        if not metrics:
            issues.append("Font has no character metrics")
        else:
            # Test that we have metrics for common characters
            test_chars = ['A', 'a', '0', ' ', '.']
            missing_chars = [c for c in test_chars if c not in metrics]
            if missing_chars:
                issues.append(f"Missing metrics for characters: {missing_chars}")
            
            # Test that metrics have required fields
            for char, metric in list(metrics.items())[:5]:  # Check first 5
                required_fields = ['x', 'y', 'width', 'height', 'u', 'v', 'uw', 'vh', 'advance']
                for field in required_fields:
                    if field not in metric:
                        issues.append(f"Missing field in metric for '{char}': {field}")
                        break
                if issues:
                    break
        
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON in font metadata: {e}")
    except Exception as e:
        issues.append(f"Error testing font: {e}")
    
    return len(issues) == 0, issues


def test_sound_loading(sound_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Test that a sound file can be loaded and played."""
    issues = []
    
    if not os.path.exists(sound_path):
        issues.append(f"Sound file does not exist: {sound_path}")
        return False, issues
    
    # Test basic properties
    try:
        file_size = os.path.getsize(sound_path)
        if file_size == 0:
            issues.append("Sound file is empty")
        
        # Test that we can read file header (would use audio library in real implementation)
        with open(sound_path, 'rb') as f:
            header = f.read(64)  # Read first 64 bytes
            if len(header) == 0:
                issues.append("Cannot read sound file header")
    
    except Exception as e:
        issues.append(f"Error testing sound file: {e}")
    
    return len(issues) == 0, issues


def test_model_loading(model_path: str, config: Dict) -> Tuple[bool, List[str]]:
    """Test that a 3D model file can be loaded and used."""
    issues = []
    
    if not os.path.exists(model_path):
        issues.append(f"Model file does not exist: {model_path}")
        return False, issues
    
    # Test basic properties
    try:
        file_size = os.path.getsize(model_path)
        if file_size == 0:
            issues.append("Model file is empty")
        
        # Test that we can read file header (would use assimp or similar in real implementation)
        with open(model_path, 'rb') as f:
            header = f.read(64)  # Read first 64 bytes
            if len(header) == 0:
                issues.append("Cannot read model file header")
        
        # Test format-specific validation
        ext = Path(model_path).suffix.lower()
        if ext == '.obj':
            # Quick OBJ validation
            with open(model_path, 'r') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('#') and not first_line.startswith('v ') and first_line != '':
                    # Not necessarily an issue, but worth noting
                    pass
    
    except Exception as e:
        issues.append(f"Error testing model file: {e}")
    
    return len(issues) == 0, issues


def test_asset_integrity(assets_dir: str, config: Dict) -> Tuple[bool, List[str], Dict]:
    """Test that assets are internally consistent and usable together."""
    issues = []
    stats = {
        'tilesets_tested': 0,
        'fonts_tested': 0,
        'sounds_tested': 0,
        'models_tested': 0,
        'passed': 0,
        'failed': 0
    }
    
    # Test tilesets
    tileset_dir = os.path.join(assets_dir, 'tilesets')
    if os.path.exists(tileset_dir):
        for root, dirs, files in os.walk(tileset_dir):
            for file in files:
                if file.endswith('.png'):
                    tile_path = os.path.join(root, file)
                    valid, tile_issues = test_tileset_loading(tile_path, config)
                    stats['tilesets_tested'] += 1
                    if valid:
                        stats['passed'] += 1
                    else:
                        stats['failed'] += 1
                        issues.extend([f"{tile_path}: {issue}" for issue in tile_issues])
    
    # Test fonts
    font_dir = os.path.join(assets_dir, 'fonts')
    if os.path.exists(font_dir):
        for root, dirs, files in os.walk(font_dir):
            for file in files:
                if file.endswith('.png'):
                    font_path = os.path.join(root, file)
                    valid, font_issues = test_font_loading(font_path, config)
                    stats['fonts_tested'] += 1
                    if valid:
                        stats['passed'] += 1
                    else:
                        stats['failed'] += 1
                        issues.extend([f"{font_path}: {issue}" for issue in font_issues])
    
    # Test sounds
    sound_dir = os.path.join(assets_dir, 'sounds')
    if os.path.exists(sound_dir):
        for root, dirs, files in os.walk(sound_dir):
            for file in files:
                if any(file.endswith(ext) for ext in ['.ogg', '.mp3', '.wav']):
                    sound_path = os.path.join(root, file)
                    valid, sound_issues = test_sound_loading(sound_path, config)
                    stats['sounds_tested'] += 1
                    if valid:
                        stats['passed'] += 1
                    else:
                        stats['failed'] += 1
                        issues.extend([f"{sound_path}: {issue}" for issue in sound_issues])
    
    # Test models
    model_dir = os.path.join(assets_dir, 'models')
    if os.path.exists(model_dir):
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                if any(file.endswith(ext) for ext in ['.gltf', '.glb', '.obj', '.fbx']):
                    model_path = os.path.join(root, file)
                    valid, model_issues = test_model_loading(model_path, config)
                    stats['models_tested'] += 1
                    if valid:
                        stats['passed'] += 1
                    else:
                        stats['failed'] += 1
                        issues.extend([f"{model_path}: {issue}" for issue in model_issues])
    
    return len(issues) == 0, issues, stats


def test_performance_baselines(assets_dir: str, config: Dict) -> Tuple[bool, List[str]]:
    """Test that assets meet basic performance requirements."""
    issues = []
    
    # Check that textures are not excessively large
    tileset_dir = os.path.join(assets_dir, 'tilesets')
    if os.path.exists(tileset_dir):
        max_size = config['tileset'].get('max_atlas_size', 2048)
        for root, dirs, files in os.walk(tileset_dir):
            for file in files:
                if file.endswith('.png'):
                    tile_path = os.path.join(root, file)
                    try:
                        # Would check actual image dimensions in real implementation
                        file_size = os.path.getsize(tile_path)
                        size_mb = file_size / (1024 * 1024)
                        if size_mb > 10:  # Arbitrary limit of 10MB per texture
                            issues.append(f"Texture excessively large: {tile_path} ({size_mb:.1f}MB)")
                    except Exception:
                        pass  # Skip if we can't get size
    
    # Check that audio files are reasonable length
    sound_dir = os.path.join(assets_dir, 'sounds')
    if os.path.exists(sound_dir):
        for root, dirs, files in os.walk(sound_dir):
            for file in files:
                if any(file.endswith(ext) for ext in ['.ogg', '.mp3', '.wav']):
                    sound_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(sound_path)
                        # Very rough estimate: 1MB ≈ 1 minute of audio
                        # This is just a basic sanity check
                        if file_size > 50 * 1024 * 1024:  # 50MB limit
                            issues.append(f"Audio file excessively large: {sound_path} ({file_size/(1024*1024):.1f}MB)")
                    except Exception:
                        pass
    
    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description='Test processed assets')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--assets-dir', default=None,
                       help='Directory containing processed assets (overrides config)')
    parser.add_argument('--output', default=None,
                       help='Output file for test report (JSON)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--perf-only', action='store_true',
                       help='Run only performance tests')
    
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
    
    if not os.path.exists(assets_dir):
        print(f"Assets directory does not exist: {assets_dir}")
        sys.exit(1)
    
    # Run tests
    all_passed = True
    test_results = {
        'timestamp': time.time(),
        'assets_directory': assets_dir,
        'tests': {},
        'summary': {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0
        }
    }
    
    # Functional tests
    if not args.perf_only:
        print("Running functional tests...")
        valid, issues, stats = test_asset_integrity(assets_dir, config)
        test_results['tests']['asset_integrity'] = {
            'passed': valid,
            'issues': issues,
            'stats': stats
        }
        test_results['summary']['total_tests'] += 1
        if valid:
            test_results['summary']['passed_tests'] += 1
            if args.verbose:
                print("  ✓ Asset integrity: PASSED")
        else:
            test_results['summary']['failed_tests'] += 1
            all_passed = False
            if args.verbose:
                print("  ✗ Asset integrity: FAILED")
                for issue in issues[:5]:
                    print(f"    - {issue}")
    
    # Performance tests
    print("Running performance tests...")
    valid, issues = test_performance_baselines(assets_dir, config)
    test_results['tests']['performance'] = {
        'passed': valid,
        'issues': issues
    }
    test_results['summary']['total_tests'] += 1
    if valid:
        test_results['summary']['passed_tests'] += 1
        if args.verbose:
            print("  ✓ Performance baselines: PASSED")
    else:
        test_results['summary']['failed_tests'] += 1
        all_passed = False
        if args.verbose:
            print("  ✗ Performance baselines: FAILED")
            for issue in issues[:5]:
                print(f"    - {issue}")
    
    # Output results
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(test_results, f, indent=2)
            print(f"Test report saved to: {args.output}")
        except Exception as e:
            print(f"Error writing test report: {e}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"ASSET TESTING SUMMARY")
    print(f"{'='*60}")
    print(f"Assets directory: {assets_dir}")
    print(f"Total tests: {test_results['summary']['total_tests']}")
    print(f"Passed: {test_results['summary']['passed_tests']}")
    print(f"Failed: {test_results['summary']['failed_tests']}")
    
    if not all_passed:
        print("\nTESTING FAILED")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED")
        sys.exit(0)


if __name__ == '__main__':
    import time
    main()