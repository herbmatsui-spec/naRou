#!/usr/bin/env python3
"""
Asset analysis script for performing deeper analysis on assets.
Includes quality analysis, optimization recommendations, and asset usage patterns.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import time


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def analyze_tileset_quality(tileset_dir: str, config: Dict) -> Dict:
    """Analyze tileset quality and provide optimization recommendations."""
    analysis = {
        'total_analyzed': 0,
        'quality_issues': [],
        'optimization_opportunities': [],
        'recommendations': [],
        'metrics': {}
    }
    
    if not os.path.exists(tileset_dir):
        return analysis
    
    max_atlas_size = config.get('tileset', {}).get('max_atlas_size', 2048)
    
    for root, dirs, files in os.walk(tileset_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    analysis['total_analyzed'] += 1
                    
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        tile_size = metadata.get('tile_size', 0)
                        atlas_width = metadata.get('atlas_width', 0)
                        atlas_height = metadata.get('atlas_height', 0)
                        tile_count = metadata.get('tile_count', 0)
                        
                        # Check for inefficient atlas usage
                        if atlas_width > 0 and atlas_height > 0:
                            atlas_area = atlas_width * atlas_height
                            used_area = tile_count * (tile_size * tile_size)
                            usage_ratio = used_area / atlas_area if atlas_area > 0 else 0
                            
                            if usage_ratio < 0.5:
                                analysis['optimization_opportunities'].append({
                                    'type': 'low_atlas_usage',
                                    'asset': os.path.splitext(file)[0],
                                    'usage_ratio': usage_ratio,
                                    'description': f"Atlas only {usage_ratio*100:.1f}% used ({tile_count} tiles of {tile_size}px in {atlas_width}x{atlas_height} atlas)"
                                })
                        
                        # Check for oversized atlases
                        if atlas_width > max_atlas_size or atlas_height > max_atlas_size:
                            analysis['quality_issues'].append({
                                'type': 'oversized_atlas',
                                'asset': os.path.splitext(file)[0],
                                'atlas_width': atlas_width,
                                'atlas_height': atlas_height,
                                'max_allowed': max_atlas_size,
                                'description': f"Atlas dimensions {atlas_width}x{atlas_height} exceed maximum {max_atlas_size}"
                            })
                        
                        # Check for non-power-of-two dimensions (if required by engine)
                        if atlas_width & (atlas_width - 1) != 0:  # Not power of 2
                            analysis['optimization_opportunities'].append({
                                'type': 'non_power_of_two',
                                'asset': os.path.splitext(file)[0],
                                'dimension': 'width',
                                'value': atlas_width,
                                'description': f"Atlas width {atlas_width} is not a power of 2"
                            })
                        
                        if atlas_height & (atlas_height - 1) != 0:  # Not power of 2
                            analysis['optimization_opportunities'].append({
                                'type': 'non_power_of_two',
                                'asset': os.path.splitext(file)[0],
                                'dimension': 'height',
                                'value': atlas_height,
                                'description': f"Atlas height {atlas_height} is not a power of 2"
                            })
                            
                    except Exception as e:
                        analysis['quality_issues'].append({
                            'type': 'parse_error',
                            'asset': os.path.splitext(file)[0],
                            'error': str(e),
                            'description': f"Failed to parse tileset metadata: {e}"
                        })
    
    # Generate recommendations based on findings
    if analysis['optimization_opportunities']:
        analysis['recommendations'].append("Consider regenerating atlases with better packing efficiency")
    
    if any(issue['type'] == 'oversized_atlas' for issue in analysis['quality_issues']):
        analysis['recommendations'].append("Reduce atlas dimensions to meet engine requirements")
    
    if any(op['type'] == 'non_power_of_two' for op in analysis['optimization_opportunities']):
        analysis['recommendations'].append("Use power-of-two dimensions for better GPU compatibility")
    
    if analysis['total_analyzed'] == 0:
        analysis['recommendations'].append("No tilesets found for analysis")
    
    return analysis


def analyze_font_quality(font_dir: str, config: Dict) -> Dict:
    """Analyze font quality and provide optimization recommendations."""
    analysis = {
        'total_analyzed': 0,
        'quality_issues': [],
        'optimization_opportunities': [],
        'recommendations': [],
        'metrics': {}
    }
    
    if not os.path.exists(font_dir):
        return analysis
    
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith('.json') and not file.endswith('_manifest.json'):
                json_path = os.path.join(root, file)
                png_path = json_path.replace('.json', '.png')
                
                if os.path.exists(png_path):
                    analysis['total_analyzed'] += 1
                    
                    try:
                        with open(json_path, 'r') as f:
                            metadata = json.load(f)
                        
                        font_size = metadata.get('font_size', 0)
                        atlas_width = metadata.get('atlas_width', 0)
                        atlas_height = metadata.get('atlas_height', 0)
                        metrics = metadata.get('metrics', {})
                        
                        # Check for inefficient atlas usage
                        if len(metrics) > 0 and atlas_width > 0 and atlas_height > 0:
                            # Estimate used area based on character metrics
                            used_width = sum(m.get('width', 0) for m in metrics.values())
                            used_height = max((m.get('height', 0) for m in metrics.values()), default=0)
                            # Add padding estimation
                            used_width += 2 * len(metrics)  # Rough padding estimate
                            used_height += 4  # Rough padding estimate
                            
                            atlas_area = atlas_width * atlas_height
                            used_area = used_width * used_height
                            usage_ratio = used_area / atlas_area if atlas_area > 0 else 0
                            
                            if usage_ratio < 0.3:
                                analysis['optimization_opportunities'].append({
                                    'type': 'low_font_atlas_usage',
                                    'asset': os.path.splitext(file)[0],
                                    'usage_ratio': usage_ratio,
                                    'description': f"Font atlas only {usage_ratio*100:.1f}% used"
                                })
                        
                        # Check for excessive font sizes
                        if font_size > 72:
                            analysis['quality_issues'].append({
                                'type': 'excessive_font_size',
                                'asset': os.path.splitext(file)[0],
                                'font_size': font_size,
                                'description': f"Font size {font_size}pt may be excessively large for UI"
                            })
                        
                        # Check character coverage
                        ascii_chars = sum(1 for c in metrics.keys() if ord(c) < 128)
                        total_chars = len(metrics)
                        if total_chars > 0:
                            ascii_ratio = ascii_chars / total_chars
                            if ascii_ratio < 0.8:
                                analysis['optimization_opportunities'].append({
                                    'type': 'limited_character_set',
                                    'asset': os.path.splitext(file)[0],
                                    'ascii_ratio': ascii_ratio,
                                    'description': f"Only {ascii_ratio*100:.1f}% of characters are ASCII"
                                })
                                
                    except Exception as e:
                        analysis['quality_issues'].append({
                            'type': 'parse_error',
                            'asset': os.path.splitext(file)[0],
                            'error': str(e),
                            'description': f"Failed to parse font metadata: {e}"
                        })
    
    # Generate recommendations
    if analysis['optimization_opportunities']:
        analysis['recommendations'].append("Consider regenerating font atlases with better character packing")
    
    if analysis['total_analyzed'] == 0:
        analysis['recommendations'].append("No fonts found for analysis")
    
    return analysis


def analyze_sound_quality(sound_dir: str, config: Dict) -> Dict:
    """Analyze sound quality and provide optimization recommendations."""
    analysis = {
        'total_analyzed': 0,
        'quality_issues': [],
        'optimization_opportunities': [],
        'recommendations': [],
        'metrics': {}
    }
    
    if not os.path.exists(sound_dir):
        return analysis
    
    # Quality thresholds from config
    music_bitrate_threshold = config.get('sound', {}).get('quality', {}).get('music', {}).get('bitrate', '192k')
    sfx_bitrate_threshold = config.get('sound', {}).get('quality', {}).get('sfx', {}).get('bitrate', '128k')
    
    # Convert bitrate strings to numeric values for comparison
    def bitrate_to_kbps(br):
        if isinstance(br, str):
            if br.endswith('k'):
                return int(br[:-1])
            elif br.endswith('kbps'):
                return int(br[:-4])
        return 0
    
    music_threshold_kbps = bitrate_to_kbps(music_bitrate_threshold)
    sfx_threshold_kbps = bitrate_to_kbps(sfx_bitrate_threshold)
    
    extensions = ['.ogg', '.mp3', '.wav', '.flac']
    
    for root, dirs, files in os.walk(sound_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                sound_path = os.path.join(root, file)
                analysis['total_analyzed'] += 1
                
                try:
                    file_size = os.path.getsize(sound_path)
                    
                    # Try to extract metadata (would use audio library in real implementation)
                    # For now, use placeholder analysis
                    
                    # Check file size for potential issues
                    size_mb = file_size / (1024 * 1024)
                    if size_mb > 50:  # Arbitrary large file threshold
                        analysis['quality_issues'].append({
                            'type': 'excessive_file_size',
                            'asset': file,
                            'size_mb': size_mb,
                            'description': f"Sound file is {size_mb:.1f}MB, consider compression or trimming"
                        })
                    
                    # Check format
                    ext = Path(file).suffix.lower()
                    if ext == '.wav':
                        analysis['optimization_opportunities'].append({
                            'type': 'uncompressed_format',
                            'asset': file,
                            'current_format': 'WAV',
                            'recommended_format': 'OGG',
                            'description': "WAV files are uncompressed; consider converting to OGG for smaller size"
                        })
                    elif ext == '.flac':
                        analysis['optimization_opportunities'].append({
                            'type': 'lossless_format',
                            'asset': file,
                            'current_format': 'FLAC',
                            'recommended_format': 'OGG',
                            'description': "FLAC is lossless; consider OGG for game audio unless lossless quality is required"
                        })
                    
                    # Estimate bitrate (rough approximation)
                    # Would need actual duration for accurate calculation
                    # For now, skip bitrate analysis
                    
                except Exception as e:
                    analysis['quality_issues'].append({
                        'type': 'analysis_error',
                        'asset': file,
                        'error': str(e),
                        'description': f"Failed to analyze sound file: {e}"
                    })
    
    # Generate recommendations
    if analysis['optimization_opportunities']:
        analysis['recommendations'].append("Consider converting uncompressed audio to compressed formats (OGG/MP3)")
    
    if analysis['total_analyzed'] == 0:
        analysis['recommendations'].append("No sound files found for analysis")
    
    return analysis


def analyze_model_quality(model_dir: str, config: Dict) -> Dict:
    """Analyze 3D model quality and provide optimization recommendations."""
    analysis = {
        'total_analyzed': 0,
        'quality_issues': [],
        'optimization_opportunities': [],
        'recommendations': [],
        'metrics': {}
    }
    
    if not os.path.exists(model_dir):
        return analysis
    
    # Thresholds for optimization
    high_vertex_threshold = 50000  # Vertices
    high_face_threshold = 100000   # Faces
    large_file_threshold = 50 * 1024 * 1024  # 50MB
    
    extensions = ['.obj', '.fbx', '.gltf', '.glb', '.dae', '.3ds', '.blend', '.ply', '.stl']
    
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                model_path = os.path.join(root, file)
                analysis['total_analyzed'] += 1
                
                try:
                    file_size = os.path.getsize(model_path)
                    
                    # Analyze based on file type
                    if file.endswith('.obj'):
                        # Simple OBJ analysis
                        vertex_count = 0
                        face_count = 0
                        try:
                            with open(model_path, 'r') as f:
                                for line in f:
                                    if line.startswith('v '):
                                        vertex_count += 1
                                    elif line.startswith('f '):
                                        face_count += 1
                        except Exception:
                            pass
                        
                        # Check for high polygon count
                        if vertex_count > high_vertex_threshold:
                            analysis['quality_issues'].append({
                                'type': 'high_vertex_count',
                                'asset': file,
                                'vertex_count': vertex_count,
                                'threshold': high_vertex_threshold,
                                'description': f"Model has {vertex_count:,} vertices (>{high_vertex_threshold:,})"
                            })
                        
                        if face_count > high_face_threshold:
                            analysis['quality_issues'].append({
                                'type': 'high_face_count',
                                'asset': file,
                                'face_count': face_count,
                                'threshold': high_face_threshold,
                                'description': f"Model has {face_count:,} faces (>{high_face_threshold:,})"
                            })
                        
                        # Check file size
                        if file_size > large_file_threshold:
                            analysis['quality_issues'].append({
                                'type': 'large_file_size',
                                'asset': file,
                                'size_mb': file_size / (1024 * 1024),
                                'threshold_mb': large_file_threshold / (1024 * 1024),
                                'description': f"Model file is {file_size/(1024*1024):.1f}MB (>{large_file_threshold/(1024*1024):.0f}MB)"
                            })
                        
                        # Optimization opportunities
                        if vertex_count > 1000:
                            analysis['optimization_opportunities'].append({
                                'type': 'vertex_optimization_possible',
                                'asset': file,
                                'current_vertices': vertex_count,
                                'description': f"Model may benefit from vertex optimization ({vertex_count:,} vertices)"
                            })
                        
                        if file_size > 5 * 1024 * 1024:  # 5MB
                            analysis['optimization_opportunities'].append({
                                'type': 'compression_possible',
                                'asset': file,
                                'current_format': 'OBJ',
                                'suggested_format': 'GLTF',
                                'description': f"Large OBJ file; consider converting to GLTF with compression"
                            })
                            
                    else:
                        # For other formats, do basic checks
                        if file_size > large_file_threshold:
                            analysis['quality_issues'].append({
                                'type': 'large_file_size',
                                'asset': file,
                                'size_mb': file_size / (1024 * 1024),
                                'threshold_mb': large_file_threshold / (1024 * 1024),
                                'description': f"Model file is {file_size/(1024*1024):.1f}MB (>{large_file_threshold/(1024*1024):.0f}MB)"
                            })
                            
                except Exception as e:
                    analysis['quality_issues'].append({
                        'type': 'analysis_error',
                        'asset': file,
                        'error': str(e),
                        'description': f"Failed to analyze model file: {e}"
                    })
    
    # Generate recommendations
    if analysis['optimization_opportunities']:
        analysis['recommendations'].append("Consider optimizing high-polygon models for real-time performance")
    
    if any(issue['type'] == 'large_file_size' for issue in analysis['quality_issues']):
        analysis['recommendations'].append("Apply mesh compression or consider LOD models for large assets")
    
    if analysis['total_analyzed'] == 0:
        analysis['recommendations'].append("No model files found for analysis")
    
    return analysis


def generate_analysis_report(config: Dict) -> Dict:
    """Generate a comprehensive analysis report for all asset types."""
    report = {
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'analyses': {}
    }
    
    # Analyze each asset type
    analyses_to_run = [
        ('tilesets', 'tilesets', analyze_tileset_quality),
        ('fonts', 'fonts', analyze_font_quality),
        ('sounds', 'sounds', analyze_sound_quality),
        ('models', 'models', analyze_model_quality)
    ]
    
    for analysis_name, dir_key, analyze_func in analyses_to_run:
        dir_path = os.path.join(config['directories']['output'], dir_key)
        print(f"Analyzing {analysis_name} quality in: {dir_path}")
        report['analyses'][analysis_name] = analyze_func(dir_path, config)
    
    # Generate summary
    total_issues = 0
    total_opportunities = 0
    total_recommendations = set()  # Use set to avoid duplicates
    
    for analysis_name, analysis in report['analyses'].items():
        total_issues += len(analysis.get('quality_issues', []))
        total_opportunities += len(analysis.get('optimization_opportunities', []))
        total_recommendations.update(analysis.get('recommendations', []))
    
    report['summary'] = {
        'total_analyses': len(analyses_to_run),
        'total_quality_issues': total_issues,
        'total_optimization_opportunities': total_opportunities,
        'total_unique_recommendations': len(total_recommendations),
        'recommendations_list': list(total_recommendations)
    }
    
    return report


def save_analysis(report: Dict, output_path: str) -> bool:
    """Save analysis report to a JSON file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Analysis report saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving analysis report: {e}")
        return False


def print_analysis_summary(report: Dict):
    """Print a formatted summary of the analysis."""
    print(f"\n{'='*70}")
    print(f"ASSET QUALITY ANALYSIS REPORT")
    print(f"{'='*70}")
    print(f"Timestamp: {report['datetime']}")
    
    print(f"\nSUMMARY:")
    summary = report.get('summary', {})
    print(f"  Analyses Performed: {summary.get('total_analyses', 0)}")
    print(f"  Quality Issues Found: {summary.get('total_quality_issues', 0)}")
    print(f"  Optimization Opportunities: {summary.get('total_optimization_opportunities', 0)}")
    print(f"  Unique Recommendations: {summary.get('total_unique_recommendations', 0)}")
    
    if summary.get('recommendations_list'):
        print(f"\nKEY RECOMMENDATIONS:")
        for i, rec in enumerate(summary['recommendations_list'][:10], 1):  # Show top 10
            print(f"  {i}. {rec}")
        if len(summary['recommendations_list']) > 10:
            print(f"  ... and {len(summary['recommendations_list']) - 10} more recommendations")
    
    print(f"\nDETAILED FINDINGS BY ASSET TYPE:")
    for analysis_name, analysis in report.get('analyses', {}).items():
        print(f"\n  {analysis_name.upper()}:")
        print(f"    Analyzed: {analysis.get('total_analyzed', 0)} assets")
        print(f"    Quality Issues: {len(analysis.get('quality_issues', []))}")
        print(f"    Optimization Opportunities: {len(analysis.get('optimization_opportunities', []))}")
        
        # Show top issues
        issues = analysis.get('quality_issues', [])
        if issues:
            print(f"    Top Quality Issues:")
            for issue in issues[:3]:
                print(f"      - {issue.get('description', 'No description')}")
            if len(issues) > 3:
                print(f"      ... and {len(issues) - 3} more issues")
        
        # Show top opportunities
        opportunities = analysis.get('optimization_opportunities', [])
        if opportunities:
            print(f"    Top Optimization Opportunities:")
            for opp in opportunities[:3]:
                print(f"      - {opp.get('description', 'No description')}")
            if len(opportunities) > 3:
                print(f"      ... and {len(opportunities) - 3} more opportunities")


def main():
    parser = argparse.ArgumentParser(description='Analyze assets for quality and optimization opportunities')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--output', default=None,
                       help='Output file for analysis (JSON)')
    parser.add_argument('--assets', nargs='+',
                       choices=['tilesets', 'fonts', 'sounds', 'models', 'all'],
                       default=['all'], help='Asset types to analyze')
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
    
    # Determine which assets to analyze
    if args.assets == ['all']:
        assets_to_analyze = ['tilesets', 'fonts', 'sounds', 'models']
    else:
        assets_to_analyze = args.assets
    
    # Generate analysis report
    report = generate_analysis_report(config)
    
    # Filter analyses if needed
    if args.assets != ['all']:
        filtered_analyses = {
            k: v for k, v in report['analyses'].items() 
            if k in assets_to_analyze
        }
        report['analyses'] = filtered_analyses
        
        # Recalculate summary
        total_issues = 0
        total_opportunities = 0
        total_recommendations = set()
        
        for analysis_name, analysis in report['analyses'].items():
            total_issues += len(analysis.get('quality_issues', []))
            total_opportunities += len(analysis.get('optimization_opportunities', []))
            total_recommendations.update(analysis.get('recommendations', []))
        
        report['summary'] = {
            'total_analyses': len(assets_to_analyze),
            'total_quality_issues': total_issues,
            'total_optimization_opportunities': total_opportunities,
            'total_unique_recommendations': len(total_recommendations),
            'recommendations_list': list(total_recommendations)
        }
    
    # Save or output results
    if args.output:
        if not save_analysis(report, args.output):
            sys.exit(1)
    
    if not args.summary_only:
        # Print full JSON
        print(json.dumps(report, indent=2))
    else:
        # Print formatted summary
        print_analysis_summary(report)
    
    sys.exit(0)


if __name__ == '__main__':
    main()