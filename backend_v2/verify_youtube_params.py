#!/usr/bin/env python3
"""
Simple verification of YouTube compatibility parameters in background_manager.py
"""

import re
from pathlib import Path

def check_background_manager():
    """Check background_manager.py for YouTube compatibility parameters."""
    file_path = Path("reddit_story/background_manager.py")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    print("Checking extract_video_clip method in background_manager.py...")
    
    # Find the extract_video_clip method
    method_start = content.find("def extract_video_clip")
    if method_start == -1:
        print("Could not find extract_video_clip method")
        return False
    
    # Find the end of the method (next method or class)
    method_end = content.find("\n    def ", method_start + 1)
    if method_end == -1:
        method_end = content.find("\n\nclass ", method_start + 1)
    if method_end == -1:
        method_end = len(content)
    
    method_content = content[method_start:method_end]
    
    # Look for the ffmpeg command in this method
    # The command should have specific parameters
    checks = {
        '-pix_fmt yuv420p': '-pix_fmt' in method_content and 'yuv420p' in method_content,
        '-movflags +faststart': ('-movflags' in method_content and 
                                ('+faststart' in method_content or 'faststart' in method_content)),
        '-c:a aac': ('-c:a' in method_content and 'aac' in method_content),
    }
    
    all_present = True
    for param, present in checks.items():
        if present:
            print(f"✓ Found {param}")
        else:
            print(f"✗ Missing {param}")
            all_present = False
    
    # Also check the actual command lines
    print("\nChecking actual command lines...")
    lines = method_content.split('\n')
    in_cmd = False
    cmd_lines = []
    
    for i, line in enumerate(lines, 1):
        if "'ffmpeg'" in line or '"ffmpeg"' in line:
            in_cmd = True
            cmd_lines = [line]
        elif in_cmd:
            cmd_lines.append(line)
            if line.strip().endswith(']'):
                # End of command
                cmd_text = ' '.join(' '.join(cmd_lines).split())  # Normalize whitespace
                print(f"\nFound ffmpeg command (approx {len(cmd_text)} chars):")
                print(f"  Contains -pix_fmt yuv420p: {'-pix_fmt' in cmd_text and 'yuv420p' in cmd_text}")
                print(f"  Contains -movflags +faststart: {'-movflags' in cmd_text and ('+faststart' in cmd_text or 'faststart' in cmd_text)}")
                print(f"  Contains -c:a aac: {'-c:a' in cmd_text and 'aac' in cmd_text}")
                in_cmd = False
                cmd_lines = []
    
    return all_present

def check_video_composer():
    """Check video_composer.py for YouTube compatibility parameters."""
    file_path = Path("reddit_story/video_composer.py")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    print("\n\nChecking combine_audio_with_background method in video_composer.py...")
    
    # Find the combine_audio_with_background method
    method_start = content.find("def combine_audio_with_background")
    if method_start == -1:
        print("Could not find combine_audio_with_background method")
        return False
    
    # Find the end of the method (next method or class)
    method_end = content.find("\n    def ", method_start + 1)
    if method_end == -1:
        method_end = content.find("\n\nclass ", method_start + 1)
    if method_end == -1:
        method_end = len(content)
    
    method_content = content[method_start:method_end]
    
    # Look for the ffmpeg command in this method
    checks = {
        '-pix_fmt yuv420p': '-pix_fmt' in method_content and 'yuv420p' in method_content,
        '-movflags +faststart': ('-movflags' in method_content and 
                                ('+faststart' in method_content or 'faststart' in method_content)),
        '-c:a aac': ('-c:a' in method_content and 'aac' in method_content),
    }
    
    all_present = True
    for param, present in checks.items():
        if present:
            print(f"✓ Found {param}")
        else:
            print(f"✗ Missing {param}")
            all_present = False
    
    return all_present

def main():
    print("YouTube Compatibility Parameter Verification")
    print("=" * 60)
    
    bg_ok = check_background_manager()
    vc_ok = check_video_composer()
    
    print("\n" + "=" * 60)
    if bg_ok and vc_ok:
        print("✓ All required YouTube compatibility parameters are present")
        return 0
    else:
        print("✗ Some YouTube compatibility parameters are missing")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())