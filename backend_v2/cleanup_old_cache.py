#!/usr/bin/env python3
"""
Cleanup script for old TTS cache files.
Removes cache files older than specified age to ensure fresh squeaky voice generation.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from reddit_story.edgetts_client import EdgeTTSClient


async def cleanup_cache(max_age_hours: int = 24):
    """
    Clean up cache files older than specified hours.
    
    Args:
        max_age_hours: Maximum age of cache files in hours (default: 24 hours)
    """
    print(f"=== Cleaning up cache files older than {max_age_hours} hours ===")
    
    # Create client to access cache directory
    client = EdgeTTSClient()
    
    # Get cache directory info
    cache_dir = client.cache_dir
    voices_dir = client.voices_dir
    
    print(f"Cache directory: {cache_dir}")
    print(f"Voices directory: {voices_dir}")
    print()
    
    # Count files before cleanup
    wav_files = list(voices_dir.glob("*.wav"))
    json_files = list(voices_dir.glob("*.json"))
    timestamp_files = list(voices_dir.glob("*.timestamps.json"))
    
    print(f"Files before cleanup:")
    print(f"  - WAV files: {len(wav_files)}")
    print(f"  - JSON metadata files: {len(json_files)}")
    print(f"  - Timestamp files: {len(timestamp_files)}")
    print(f"  - Total: {len(wav_files) + len(json_files) + len(timestamp_files)}")
    print()
    
    # Use client's cleanup method
    deleted_count = client.cleanup_old_cache(max_age_hours=max_age_hours)
    
    # Count files after cleanup
    wav_files_after = list(voices_dir.glob("*.wav"))
    json_files_after = list(voices_dir.glob("*.json"))
    timestamp_files_after = list(voices_dir.glob("*.timestamps.json"))
    
    print(f"Files after cleanup:")
    print(f"  - WAV files: {len(wav_files_after)}")
    print(f"  - JSON metadata files: {len(json_files_after)}")
    print(f"  - Timestamp files: {len(timestamp_files_after)}")
    print(f"  - Total: {len(wav_files_after) + len(json_files_after) + len(timestamp_files_after)}")
    print()
    
    print(f"✓ Cleaned up {deleted_count} old cache files")
    
    # Show remaining file ages
    if wav_files_after:
        print("\nRemaining cache files (newest first):")
        sorted_files = sorted(wav_files_after, key=lambda p: p.stat().st_mtime, reverse=True)
        for i, filepath in enumerate(sorted_files[:5]):  # Show top 5
            file_age_hours = (datetime.now().timestamp() - filepath.stat().st_mtime) / 3600
            file_size_kb = filepath.stat().st_size / 1024
            print(f"  {i+1}. {filepath.name} ({file_size_kb:.1f} KB, {file_age_hours:.1f} hours old)")
        
        if len(sorted_files) > 5:
            print(f"  ... and {len(sorted_files) - 5} more files")
    
    await client.close()
    return deleted_count


def get_cache_size_mb():
    """Calculate total cache size in MB."""
    cache_dir = Path("cache/edgetts/voices")
    if not cache_dir.exists():
        return 0
    
    total_bytes = 0
    for filepath in cache_dir.rglob("*"):
        if filepath.is_file():
            total_bytes += filepath.stat().st_size
    
    return total_bytes / (1024 * 1024)


if __name__ == "__main__":
    print("Cache Cleanup Utility")
    print("=" * 40)
    
    # Show current cache size
    cache_size_mb = get_cache_size_mb()
    print(f"Current cache size: {cache_size_mb:.2f} MB")
    print()
    
    # Ask for cleanup age
    print("Cleanup options:")
    print("  1. Clean files older than 24 hours (recommended for squeaky voice update)")
    print("  2. Clean files older than 7 days")
    print("  3. Clean all cache files (force fresh generation)")
    print("  4. Just show cache info, no cleanup")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        max_age_hours = 24
    elif choice == "2":
        max_age_hours = 7 * 24
    elif choice == "3":
        max_age_hours = 0  # Clean all
    elif choice == "4":
        print("\n=== Cache Information ===")
        # Just show info
        cache_dir = Path("cache/edgetts/voices")
        if cache_dir.exists():
            wav_files = list(cache_dir.glob("*.wav"))
            print(f"Total WAV files: {len(wav_files)}")
            
            # Group by age
            now = datetime.now().timestamp()
            age_groups = {
                "0-1 day": 0,
                "1-7 days": 0,
                "7-30 days": 0,
                "30+ days": 0,
            }
            
            for filepath in wav_files:
                file_age_days = (now - filepath.stat().st_mtime) / (3600 * 24)
                if file_age_days < 1:
                    age_groups["0-1 day"] += 1
                elif file_age_days < 7:
                    age_groups["1-7 days"] += 1
                elif file_age_days < 30:
                    age_groups["7-30 days"] += 1
                else:
                    age_groups["30+ days"] += 1
            
            print("\nFiles by age:")
            for age_range, count in age_groups.items():
                if count > 0:
                    print(f"  {age_range}: {count} files")
            
            print(f"\nTotal cache size: {cache_size_mb:.2f} MB")
        else:
            print("Cache directory does not exist.")
        
        sys.exit(0)
    else:
        print("Invalid choice. Using default (24 hours).")
        max_age_hours = 24
    
    print()
    
    # Run cleanup
    try:
        deleted = asyncio.run(cleanup_cache(max_age_hours))
        
        # Show new cache size
        new_cache_size_mb = get_cache_size_mb()
        print(f"\nNew cache size: {new_cache_size_mb:.2f} MB")
        
        if deleted > 0:
            print(f"\n✓ Cleanup complete. {deleted} files removed.")
            print("  New audio generations will use the squeaky voice settings.")
        else:
            print("\n✓ No files needed cleanup.")
            print("  Cache is already fresh.")
            
    except Exception as e:
        print(f"\n✗ Error during cleanup: {e}")
        sys.exit(1)