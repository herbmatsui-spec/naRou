#!/usr/bin/env python3
"""
Audio Conversion Script for Asset Packs
Converts audio files to game-compatible formats (OGG) using ffmpeg.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def convert_audio(input_path: Path, output_path: Path, format: str = "ogg", 
                  sample_rate: int = 44100, bitrate: str = "128k") -> bool:
    """Convert a single audio file using ffmpeg."""
    try:
        cmd = [
            "ffmpeg", "-y",  # overwrite output
            "-i", str(input_path),
            "-ar", str(sample_rate),
            "-b:a", bitrate,
            "-ac", "2",  # stereo
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"Error converting {input_path}: {result.stderr}")
            return False
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg.")
        return False
    except Exception as e:
        print(f"Error converting {input_path}: {e}")
        return False


def process_directory(input_dir: Path, output_dir: Path, target_format: str = "ogg",
                      recursive: bool = False, **kwargs) -> int:
    """Process all audio files in a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    audio_exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
    pattern = "**/*" if recursive else "*"
    count = 0
    
    for audio_path in input_dir.glob(pattern):
        if audio_path.is_file() and audio_path.suffix.lower() in audio_exts:
            rel_path = audio_path.relative_to(input_dir)
            out_name = rel_path.with_suffix(f".{target_format}")
            out_path = output_dir / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            if convert_audio(audio_path, out_path, target_format, **kwargs):
                count += 1
                print(f"Converted: {rel_path} -> {out_name}")
    
    return count


def main():
    parser = argparse.ArgumentParser(description="Convert audio files for asset packs")
    parser.add_argument("input", help="Input directory or file")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--format", default="ogg", help="Target format (default: ogg)")
    parser.add_argument("--sample-rate", type=int, default=44100, help="Sample rate (default: 44100)")
    parser.add_argument("--bitrate", default="128k", help="Bitrate (default: 128k)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    kwargs = {
        "sample_rate": args.sample_rate,
        "bitrate": args.bitrate,
    }
    
    if input_path.is_file():
        output_path.mkdir(parents=True, exist_ok=True)
        out_name = input_path.with_suffix(f".{args.format}")
        if convert_audio(input_path, output_path / out_name.name, args.format, **kwargs):
            print(f"Converted: {input_path.name} -> {out_name.name}")
            return 0
        else:
            return 1
    elif input_path.is_dir():
        count = process_directory(input_path, output_path, args.format, args.recursive, **kwargs)
        print(f"\nProcessed {count} audio files")
        return 0
    else:
        print(f"Input not found: {input_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())