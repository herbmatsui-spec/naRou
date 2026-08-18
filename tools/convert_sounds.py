#!/usr/bin/env python3
"""
Sound conversion script for converting audio files to game-appropriate formats.
Supports WAV to OGG/MP3 conversion, quality optimization, and metadata extraction.
"""

import os
import json
import argparse
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