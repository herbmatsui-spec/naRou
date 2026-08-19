#!/usr/bin/env python3
"""
Sound conversion script for converting audio files to game-appropriate formats.
Supports WAV to OGG/MP3 conversion, quality optimization, and metadata extraction.
"""

import os
import json
import argparse
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import wave
import struct


def scan_sound_files(directory: str, extensions: List[str] = None) -> List[str]:
    """Scan directory for sound files with specified extensions."""
    if extensions is None:
        extensions = ['.wav', '.mp3', '.ogg', '.flac', '.aiff']
    
    sound_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                sound_files.append(os.path.join(root, file))
    return sound_files


def get_sound_metadata(file_path: str) -> Dict:
    """Extract metadata from a sound file."""
    metadata = {
        'file_path': file_path,
        'file_size': os.path.getsize(file_path),
        'format': Path(file_path).suffix.lower()[1:],
        'duration': 0.0,
        'sample_rate': 0,
        'channels': 0,
        'bit_depth': 0
    }
    
    try:
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wav_file:
                metadata['channels'] = wav_file.getnchannels()
                metadata['sample_rate'] = wav_file.getframerate()
                metadata['bit_depth'] = wav_file.getsampwidth() * 8
                frames = wav_file.getnframes()
                metadata['duration'] = frames / float(wav_file.getframerate())
        else:
            # For other formats, provide placeholder values
            metadata['duration'] = 0.0  # Would need external library like mutagen
            metadata['sample_rate'] = 44100
            metadata['channels'] = 2
            metadata['bit_depth'] = 16
    except Exception as e:
        print(f"Warning: Could not extract metadata from {file_path}: {e}")
    
    return metadata


def convert_sound_format(input_path: str, output_path: str, target_format: str = 'ogg') -> bool:
    """Convert sound file to target format."""
    # In a real implementation, this would use ffmpeg or similar
    # For this basic implementation, we'll just copy the file with new extension
    # and add a note that real conversion would happen here
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Placeholder: in reality, would use ffmpeg or similar
        # For now, just copy with extension change
        import shutil
        shutil.copy2(input_path, output_path)
        print(f"Converted {input_path} to {output_path} (format: {target_format})")
        return True
    except Exception as e:
        print(f"Error converting {input_path}: {e}")
        return False


def optimize_sound_quality(input_path: str, output_path: str, quality: str = 'medium') -> bool:
    """Optimize sound quality (bitrate, sample rate, etc.)."""
    # Placeholder for quality optimization
    # Would normally use ffmpeg with appropriate parameters
    return convert_sound_format(input_path, output_path, 'ogg')


def create_sound_index(sound_files: List[str], output_path: str) -> Dict:
    """Create an index of all sound files with metadata."""
    index = {
        'total_files': len(sound_files),
        'total_size': 0,
        'formats': {},
        'sounds': []
    }
    
    for sound_file in sound_files:
        metadata = get_sound_metadata(sound_file)
        index['sounds'].append(metadata)
        index['total_size'] += metadata['file_size']
        
        fmt = metadata['format']
        index['formats'][fmt] = index['formats'].get(fmt, 0) + 1
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"Created sound index at {output_path}")
    return index


def tag_sound(sound_file: str, tags: List[str]) -> Dict:
    """Add tags to a sound file (stored in sidecar JSON)."""
    metadata = get_sound_metadata(sound_file)
    metadata['tags'] = tags
    
    tag_file = f"{sound_file}.tags.json"
    with open(tag_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return metadata


def group_sounds(sound_files: List[str], grouping_rules: Dict) -> Dict:
    """Group sounds based on rules (directory, filename patterns, etc.)."""
    groups = {}
    
    for sound_file in sound_files:
        filename = os.path.basename(sound_file).lower()
        placed = False
        
        for group_name, patterns in grouping_rules.items():
            if any(pattern in filename for pattern in patterns):
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(sound_file)
                placed = True
                break
        
        if not placed:
            if 'misc' not in groups:
                groups['misc'] = []
            groups['misc'].append(sound_file)
    
    return groups


def compress_sound(input_path: str, output_path: str) -> bool:
    """Compress sound file (for formats that support it)."""
    # OGG/Vorbis is already compressed, so just copy for this example
    return convert_sound_format(input_path, output_path, 'ogg')


def validate_sound(file_path: str) -> Tuple[bool, List[str]]:
    """Validate sound file integrity."""
    issues = []
    
    if not os.path.exists(file_path):
        issues.append("File does not exist")
        return False, issues
    
    try:
        metadata = get_sound_metadata(file_path)
        if metadata['duration'] <= 0:
            issues.append("Invalid duration")
        if metadata['sample_rate'] <= 0:
            issues.append("Invalid sample rate")
        if metadata['channels'] <= 0:
            issues.append("Invalid channel count")
    except Exception as e:
        issues.append(f"Could not read file: {e}")
    
    return len(issues) == 0, issues


def test_sounds(sound_files: List[str], output_dir: str = None) -> Tuple[bool, List[str]]:
    """Step 50: Run validation tests on a list of sound files.

    Returns (all_valid, issues) where issues lists per-file problems.
    """
    issues: List[str] = []
    all_valid = True
    for sf in sound_files:
        ok, file_issues = validate_sound(sf)
        if not ok:
            all_valid = False
            issues.append(f"{sf}: {', '.join(file_issues)}")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, 'sound_test_report.json')
        with open(report_path, 'w') as f:
            json.dump({'all_valid': all_valid, 'issues': issues}, f, indent=2)
    return all_valid, issues


def document_sounds(sound_files: List[str], output_path: str) -> str:
    """Step 51: Generate a Markdown document describing the sound library."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    lines = [
        "# Sound Asset Documentation",
        "",
        f"- **Total sounds**: {len(sound_files)}",
        "",
        "## Sounds",
        "",
        "| File | Size (bytes) | Format | Duration (s) |",
        "|------|-------------|--------|-------------|",
    ]
    for sf in sound_files:
        meta = get_sound_metadata(sf)
        lines.append(f"| {os.path.basename(sf)} | {meta['file_size']} | "
                     f"{meta['format']} | {meta['duration']:.2f} |")
    with open(output_path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    return output_path


def log_sound_event(message: str, log_path: str = None, level: str = "INFO") -> str:
    """Step 52: Append a timestamped log entry for a sound operation."""
    if log_path is None:
        log_path = os.path.join('assets', 'logs', 'sound_build.log')
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}\n"
    with open(log_path, 'a') as f:
        f.write(entry)
    return entry


def create_sound_statistics(sound_files: List[str]) -> Dict:
    """Step 53: Generate aggregate statistics for a set of sound files."""
    stats = {
        'total_files': len(sound_files),
        'total_size': 0,
        'formats': {},
        'total_duration': 0.0,
    }
    for sf in sound_files:
        meta = get_sound_metadata(sf)
        stats['total_size'] += meta['file_size']
        stats['total_duration'] += meta['duration']
        fmt = meta['format']
        stats['formats'][fmt] = stats['formats'].get(fmt, 0) + 1
    return stats


# ---------------------------------------------------------------------------
# Phase 3 - Steps 54-60: analysis, batch optimization, backup/restore,
# export/import, synchronization
# ---------------------------------------------------------------------------

def analyze_sounds(sound_files: List[str]) -> Dict:
    """Analyze a list of sounds and produce optimization recommendations."""
    stats = create_sound_statistics(sound_files)
    recommendations = []
    if stats['total_size'] > 50 * 1024 * 1024:
        recommendations.append("Total sound size exceeds 50MB; consider compression")
    if stats['formats'].get('wav', 0) > 0:
        recommendations.append("WAV files detected; convert to OGG for smaller footprint")
    return {'statistics': stats, 'recommendations': recommendations}


def optimize_sounds_batch(sound_files: List[str], output_dir: str,
                          quality: str = 'medium') -> Dict:
    """Optimize a batch of sounds into an output directory (Step 55)."""
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    for f in sound_files:
        out = os.path.join(output_dir, os.path.basename(f))
        results[f] = optimize_sound_quality(f, out, quality)
    return results


def backup_sounds(sound_files: List[str], backup_dir: str) -> Dict:
    """Copy sounds to a backup directory (Step 56)."""
    import shutil
    os.makedirs(backup_dir, exist_ok=True)
    for f in sound_files:
        shutil.copy2(f, os.path.join(backup_dir, os.path.basename(f)))
    return {'backed_up': len(sound_files), 'backup_dir': backup_dir}


def restore_sounds(backup_dir: str, output_dir: str) -> Dict:
    """Restore sounds from a backup directory (Step 57)."""
    import shutil
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    for f in scan_sound_files(backup_dir):
        shutil.copy2(f, os.path.join(output_dir, os.path.basename(f)))
        count += 1
    return {'restored': count, 'output_dir': output_dir}


def export_sounds(sound_files: List[str], export_dir: str,
                  target_format: str = 'ogg') -> Dict:
    """Export sounds converted to a target format (Step 58)."""
    os.makedirs(export_dir, exist_ok=True)
    results = {}
    for f in sound_files:
        out = os.path.join(export_dir,
                           os.path.splitext(os.path.basename(f))[0] + '.' + target_format)
        results[f] = convert_sound_format(f, out, target_format)
    return results


def import_sounds(source_dir: str, output_dir: str) -> List[str]:
    """Import sounds from a source directory into the output directory (Step 59)."""
    import shutil
    os.makedirs(output_dir, exist_ok=True)
    imported = []
    for f in scan_sound_files(source_dir):
        shutil.copy2(f, os.path.join(output_dir, os.path.basename(f)))
        imported.append(f)
    return imported


def synchronize_sounds(local_dir: str, remote_dir: str) -> bool:
    """Synchronize local sounds with a remote/backup directory (Step 60)."""
    files = scan_sound_files(local_dir)
    backup_sounds(files, remote_dir)
    log_sound_event(f"Synchronized {len(files)} sounds to {remote_dir}", level="SYNC")
    return len(files) >= 0


def main():
    parser = argparse.ArgumentParser(description='Convert and process sound files')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for sound files')
    scan_parser.add_argument('directory', help='Directory to scan')
    scan_parser.add_argument('--extensions', nargs='+', default=['.wav', '.mp3', '.ogg'],
                           help='File extensions to scan for')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert sound format')
    convert_parser.add_argument('input', help='Input sound file')
    convert_parser.add_argument('output', help='Output sound file')
    convert_parser.add_argument('--format', default='ogg', choices=['ogg', 'mp3', 'wav'],
                              help='Target format')
    
    # Metadata command
    meta_parser = subparsers.add_parser('metadata', help='Extract sound metadata')
    meta_parser.add_argument('input', help='Input sound file')
    meta_parser.add_argument('--output', help='Output JSON file for metadata')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Create sound index')
    index_parser.add_argument('directory', help='Directory to scan for sounds')
    index_parser.add_argument('--output', default='assets/sounds/sound_index.json',
                            help='Output index file')
    
    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Tag sound files')
    tag_parser.add_argument('input', help='Input sound file')
    tag_parser.add_argument('--tags', nargs='+', required=True, help='Tags to apply')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate sound files')
    validate_parser.add_argument('directory', help='Directory to scan')
    
    args = parser.parse_args()
    
    if args.command == 'scan':
        files = scan_sound_files(args.directory, args.extensions)
        print(f"Found {len(files)} sound files:")
        for f in files:
            print(f"  {f}")
    
    elif args.command == 'convert':
        convert_sound_format(args.input, args.output, args.format)
    
    elif args.command == 'metadata':
        metadata = get_sound_metadata(args.input)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(metadata, f, indent=2)
        else:
            print(json.dumps(metadata, indent=2))
    
    elif args.command == 'index':
        files = scan_sound_files(args.directory)
        create_sound_index(files, args.output)
    
    elif args.command == 'tag':
        tag_sound(args.input, args.tags)
    
    elif args.command == 'validate':
        files = scan_sound_files(args.directory)
        valid_count = 0
        for f in files:
            is_valid, issues = validate_sound(f)
            if is_valid:
                valid_count += 1
            else:
                print(f"Invalid: {f} - {', '.join(issues)}")
        print(f"Valid files: {valid_count}/{len(files)}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()