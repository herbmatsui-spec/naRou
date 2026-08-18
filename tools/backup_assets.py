#!/usr/bin/env python3
"""
Asset backup script for backing up asset pipeline outputs and configurations.
Supports full backups, incremental backups, and restoration points.
"""

import os
import json
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import time
import hashlib


def load_config(config_path: str = "tools/asset_pipeline_config.json") -> Dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def get_file_hash(file_path: str) -> Optional[str]:
    """Get MD5 hash of a file."""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def backup_full(source_dir: str, backup_dir: str, config: Dict) -> Dict:
    """Create a full backup of the asset directory."""
    stats = {
        'backup_type': 'full',
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'source_directory': source_dir,
        'backup_directory': backup_dir,
        'files_copied': 0,
        'files_skipped': 0,
        'total_size_bytes': 0,
        'errors': []
    }
    
    try:
        print(f"Starting full backup from {source_dir} to {backup_dir}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Walk through source directory
        for root, dirs, files in os.walk(source_dir):
            # Create corresponding directories in backup
            for dir_name in dirs:
                src_dir = os.path.join(root, dir_name)
                rel_path = os.path.relpath(src_dir, source_dir)
                dst_dir = os.path.join(backup_dir, rel_path)
                os.makedirs(dst_dir, exist_ok=True)
            
            # Copy files
            for file_name in files:
                src_file = os.path.join(root, file_name)
                rel_path = os.path.relpath(src_file, source_dir)
                dst_file = os.path.join(backup_dir, rel_path)
                
                try:
                    # Copy file
                    shutil.copy2(src_file, dst_file)
                    
                    # Update stats
                    file_size = os.path.getsize(src_file)
                    stats['files_copied'] += 1
                    stats['total_size_bytes'] += file_size
                    
                except Exception as e:
                    stats['files_skipped'] += 1
                    stats['errors'].append(f"Error copying {src_file}: {e}")
        
        # Create backup manifest
        manifest = {
            'backup_info': {
                'timestamp': stats['timestamp'],
                'datetime': stats['datetime'],
                'backup_type': 'full',
                'source_directory': source_dir,
                'backup_directory': backup_dir,
                'config_version': '1.0.0'
            },
            'file_count': stats['files_copied'],
            'total_size_bytes': stats['total_size_bytes'],
            'file_list': []  # Could be populated if needed
        }
        
        manifest_path = os.path.join(backup_dir, 'backup_manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Full backup completed: {stats['files_copied']} files, {stats['total_size_bytes']} bytes")
        
    except Exception as e:
        stats['errors'].append(f"Backup failed: {e}")
    
    return stats


def backup_incremental(source_dir: str, backup_dir: str, last_backup_time: float, config: Dict) -> Dict:
    """Create an incremental backup since last backup time."""
    stats = {
        'backup_type': 'incremental',
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'source_directory': source_dir,
        'backup_directory': backup_dir,
        'last_backup_time': last_backup_time,
        'files_copied': 0,
        'files_skipped': 0,
        'total_size_bytes': 0,
        'errors': []
    }
    
    try:
        print(f"Starting incremental backup from {source_dir} to {backup_dir}")
        print(f"Last backup time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_backup_time))}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Walk through source directory
        for root, dirs, files in os.walk(source_dir):
            # Create corresponding directories in backup
            for dir_name in dirs:
                src_dir = os.path.join(root, dir_name)
                rel_path = os.path.relpath(src_dir, source_dir)
                dst_dir = os.path.join(backup_dir, rel_path)
                os.makedirs(dst_dir, exist_ok=True)
            
            # Check files for changes since last backup
            for file_name in files:
                src_file = os.path.join(root, file_name)
                rel_path = os.path.relpath(src_file, source_dir)
                dst_file = os.path.join(backup_dir, rel_path)
                
                try:
                    # Check if file is new or modified since last backup
                    file_mtime = os.path.getmtime(src_file)
                    if file_mtime > last_backup_time:
                        # File is new or modified, copy it
                        shutil.copy2(src_file, dst_file)
                        
                        # Update stats
                        file_size = os.path.getsize(src_file)
                        stats['files_copied'] += 1
                        stats['total_size_bytes'] += file_size
                    else:
                        # File unchanged since last backup
                        stats['files_skipped'] += 1
                        
                except Exception as e:
                    stats['errors'].append(f"Error processing {src_file}: {e}")
        
        # Create backup manifest
        manifest = {
            'backup_info': {
                'timestamp': stats['timestamp'],
                'datetime': stats['datetime'],
                'backup_type': 'incremental',
                'source_directory': source_dir,
                'backup_directory': backup_dir,
                'last_backup_time': last_backup_time,
                'config_version': '1.0.0'
            },
            'file_count': stats['files_copied'],
            'total_size_bytes': stats['total_size_bytes']
        }
        
        manifest_path = os.path.join(backup_dir, 'backup_manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Incremental backup completed: {stats['files_copied']} files, {stats['total_size_bytes']} bytes")
        
    except Exception as e:
        stats['errors'].append(f"Backup failed: {e}")
    
    return stats


def create_backup_rotation_policy(backup_dir: str, config: Dict) -> Dict:
    """Apply backup rotation policy to keep only recent backups."""
    stats = {
        'policy_type': 'rotation',
        'timestamp': time.time(),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'backup_directory': backup_dir,
        'backups_removed': 0,
        'space_freed_bytes': 0,
        'errors': []
    }
    
    try:
        # Get rotation policy from config
        max_full_backups = config.get('backup', {}).get('max_full_backups', 5)
        max_incremental_backups = config.get('backup', {}).get('max_incremental_backups', 20)
        max_age_days = config.get('backup', {}).get('max_age_days', 30)
        
        max_age_seconds = max_age_days * 24 * 3600
        current_time = time.time()
        
        # Scan for backup directories
        if not os.path.exists(backup_dir):
            stats['errors'].append(f"Backup directory does not exist: {backup_dir}")
            return stats
        
        backups = []
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            if os.path.isdir(item_path):
                # Try to get timestamp from manifest or directory name
                manifest_path = os.path.join(item_path, 'backup_manifest.json')
                backup_time = None
                
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        backup_time = manifest.get('backup_info', {}).get('timestamp')
                    except Exception:
                        pass
                
                # Fallback to directory modification time
                if backup_time is None:
                    backup_time = os.path.getmtime(item_path)
                
                backups.append({
                    'path': item_path,
                    'name': item,
                    'time': backup_time
                })
        
        # Sort by time (newest first)
        backups.sort(key=lambda x: x['time'], reverse=True)
        
        # Apply age-based pruning
        backups_to_remove = []
        for backup in backups:
            age = current_time - backup['time']
            if age > max_age_seconds:
                backups_to_remove.append(backup)
        
        # Apply count-based pruning for full backups
        full_backups = [b for b in backups if 'full' in b['name'].lower() or 'backup_manifest.json' in os.listdir(b['path'])]
        if len(full_backups) > max_full_backups:
            # Mark excess full backups for removal (keep newest)
            excess_full = full_backups[max_full_backups:]
            backups_to_remove.extend(excess_full)
        
        # Remove marked backups
        for backup in backups_to_remove:
            try:
                # Calculate size before removal
                backup_size = 0
                for root, dirs, files in os.walk(backup['path']):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            try:
                                backup_size += os.path.getsize(file_path)
                            except Exception:
                                pass
                
                # Remove backup directory
                shutil.rmtree(backup['path'])
                
                stats['backups_removed'] += 1
                stats['space_freed_bytes'] += backup_size
                print(f"Removed old backup: {backup['name']}")
                
            except Exception as e:
                stats['errors'].append(f"Error removing backup {backup['path']}: {e}")
        
    except Exception as e:
        stats['errors'].append(f"Backup rotation failed: {e}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backup asset pipeline data')
    parser.add_argument('--config', default='tools/asset_pipeline_config.json',
                       help='Path to configuration file')
    parser.add_argument('--source', default=None,
                       help='Source directory to backup (overrides config output)')
    parser.add_argument('--backup-dir', required=True,
                       help='Directory to store backups')
    parser.add_argument('--type', choices=['full', 'incremental', 'rotate'],
                       default='full', help='Type of backup to perform')
    parser.add_argument('--last-backup', type=float,
                       help='Timestamp of last backup (required for incremental)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Determine source directory
    if args.source:
        source_dir = args.source
    else:
        source_dir = config['directories']['output']
    
    if not os.path.exists(source_dir):
        print(f"Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Ensure backup directory exists
    os.makedirs(args.backup_dir, exist_ok=True)
    
    # Perform requested operation
    result = None
    
    if args.type == 'full':
        result = backup_full(source_dir, args.backup_dir, config)
    elif args.type == 'incremental':
        if args.last_backup is None:
            print("Error: --last-backup is required for incremental backup")
            sys.exit(1)
        result = backup_incremental(source_dir, args.backup_dir, args.last_backup, config)
    elif args.type == 'rotate':
        result = create_backup_rotation_policy(args.backup_dir, config)
    
    # Print results
    if result:
        print(f"\n{'='*60}")
        print(f"BACKUP OPERATION RESULTS")
        print(f"{'='*60}")
        print(f"Operation: {result.get('backup_type', result.get('policy_type', 'unknown'))}")
        print(f"Timestamp: {result.get('datetime', 'N/A')}")
        
        if result.get('backup_type') in ['full', 'incremental']:
            print(f"Source: {result.get('source_directory', 'N/A')}")
            print(f"Backup Destination: {result.get('backup_directory', 'N/A')}")
            print(f"Files Copied: {result.get('files_copied', 0)}")
            print(f"Files Skipped: {result.get('files_skipped', 0)}")
            print(f"Total Size: {result.get('total_size_bytes', 0)} bytes")
            
            if result.get('errors'):
                print(f"Errors: {len(result['errors'])}")
                if args.verbose:
                    for error in result['errors'][:5]:
                        print(f"  - {error}")
                    if len(result['errors']) > 5:
                        print(f"  ... and {len(result['errors']) - 5} more errors")
        
        elif result.get('policy_type') == 'rotation':
            print(f"Backup Directory: {result.get('backup_directory', 'N/A')}")
            print(f"Backups Removed: {result.get('backups_removed', 0)}")
            print(f"Space Freed: {result.get('space_freed_bytes', 0)} bytes")
            
            if result.get('errors'):
                print(f"Errors: {len(result['errors'])}")
                if args.verbose:
                    for error in result['errors'][:5]:
                        print(f"  - {error}")
                    if len(result['errors']) > 5:
                        print(f"  ... and {len(result['errors']) - 5} more errors")
    
    # Determine exit code
    if result and not result.get('errors'):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()