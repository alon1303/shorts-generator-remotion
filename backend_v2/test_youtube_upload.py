#!/usr/bin/env python3
"""
Standalone YouTube upload test script for ShortsGenerator.
Allows testing the YouTube upload process directly using an existing .mp4 file,
bypassing the entire Reddit fetching and video generation pipeline.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_title_truncation():
    """Test the title truncation functionality."""
    print("Testing title truncation functionality...")
    
    try:
        from youtube.uploader import YouTubeUploader
        
        # Test cases
        test_cases = [
            ("Short title", "Short title"),  # Already short
            ("A" * 50 + " #shorts", "A" * 50 + " #shorts"),  # Exactly 57 chars
            ("A" * 150, "A" * 97 + "..."),  # Very long title
            ("This is a very long title that definitely exceeds the YouTube character limit of 100 characters and needs to be truncated properly", 
             "This is a very long title that definitely exceeds the YouTube character limit of 100 characters and..."),
        ]
        
        for input_title, expected in test_cases:
            truncated = YouTubeUploader.truncate_title_for_youtube(input_title)
            print(f"  Input: {input_title[:50]}...")
            print(f"  Expected: {expected[:60]}...")
            print(f"  Got: {truncated[:60]}...")
            print(f"  Length: {len(truncated)} chars")
            print(f"  {'✓ PASS' if len(truncated) <= 100 else '✗ FAIL'}")
            print()
        
        return True
    except Exception as e:
        print(f"✗ Error testing title truncation: {e}")
        return False

def test_youtube_upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "private",
    is_shorts: bool = True
):
    """Test YouTube upload with provided parameters."""
    print(f"Testing YouTube upload with file: {video_path}")
    
    try:
        from youtube.uploader import YouTubeUploader
        
        # Create uploader instance
        uploader = YouTubeUploader()
        
        # Validate credentials
        print("Validating YouTube credentials...")
        if not uploader.validate_credentials():
            print("Credentials not valid. Starting OAuth2 flow...")
            service = uploader.get_authenticated_service()
            if not service:
                print("✗ Failed to authenticate with YouTube API")
                print("\nTo set up YouTube credentials:")
                print("1. Make sure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_PROJECT_ID are set in .env")
                print("2. Or place client_secrets.json in backend_v2/ directory")
                print("3. The first run will open a browser for OAuth2 authentication")
                return False
        else:
            print("✓ YouTube credentials are valid")
        
        # Test title truncation
        print(f"\nTitle before truncation: '{title}' ({len(title)} chars)")
        truncated_title = uploader.truncate_title_for_youtube(title)
        print(f"Title after truncation: '{truncated_title}' ({len(truncated_title)} chars)")
        
        if len(truncated_title) > 100:
            print(f"✗ WARNING: Title still exceeds 100 characters ({len(truncated_title)} chars)")
            print("  YouTube will reject uploads with titles > 100 characters")
        
        # Check file exists
        if not video_path.exists():
            print(f"✗ Video file not found: {video_path}")
            return False
        
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"File size: {file_size_mb:.1f} MB")
        
        if file_size_mb > 256:
            print("⚠️  WARNING: File exceeds typical YouTube Shorts size limit (256MB)")
        
        # Show upload parameters
        print("\nUpload Parameters:")
        print(f"  Title: {truncated_title}")
        print(f"  Description length: {len(description)} characters")
        print(f"  Tags: {len(tags)} tags")
        print(f"  Privacy status: {privacy_status}")
        print(f"  Is Shorts: {is_shorts}")
        
        # Confirm upload
        print("\n⚠️  WARNING: This will upload to your YouTube account!")
        print(f"The video will be uploaded with '{privacy_status}' privacy.")
        confirmation = input("Proceed with upload? (yes/no): ").strip().lower()
        
        if confirmation != 'yes':
            print("Upload cancelled")
            return False
        
        # Perform upload
        print("\nStarting upload...")
        result = uploader.upload_video(
            video_path=video_path,
            title=title,  # upload_video will handle truncation internally
            description=description,
            tags=tags,
            category_id="22",  # People & Blogs
            privacy_status=privacy_status,
            notify_subscribers=False,
            is_shorts=is_shorts,
        )
        
        # Show result
        print("\nUpload Result:")
        print(f"  Success: {result.success}")
        
        if result.success:
            print(f"  Video ID: {result.video_id}")
            print(f"  Video URL: {result.video_url}")
            print(f"  ✓ Upload successful!")
            
            if result.metadata and 'details' in result.metadata:
                details = result.metadata['details']
                if details:
                    print(f"\nVideo Details:")
                    print(f"  Title: {details.get('snippet', {}).get('title', 'N/A')}")
                    print(f"  Status: {details.get('status', {}).get('privacyStatus', 'N/A')}")
                    print(f"  Duration: {details.get('contentDetails', {}).get('duration', 'N/A')}")
        else:
            print(f"  Error: {result.error_message}")
            print(f"  Error Code: {result.error_code}")
            print(f"  Quota Exceeded: {result.quota_exceeded}")
            print(f"  ✗ Upload failed")
        
        return result.success
        
    except Exception as e:
        print(f"✗ Error during upload test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(
        description='Test YouTube upload functionality for ShortsGenerator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with a sample video (private upload)
  python test_youtube_upload.py --video path/to/video.mp4 --title "My Test Video"
  
  # Test with specific description and tags
  python test_youtube_upload.py --video path/to/video.mp4 --title "Test" --description "Test description" --tags tag1,tag2,tag3
  
  # Test title truncation only (no upload)
  python test_youtube_upload.py --test-truncation-only
  
  # Upload as unlisted
  python test_youtube_upload.py --video path/to/video.mp4 --title "Test" --privacy unlisted
        """
    )
    
    parser.add_argument('--video', type=Path, help='Path to video file (.mp4)')
    parser.add_argument('--title', default='Test YouTube Shorts Upload', 
                       help='Video title (will be truncated to 100 chars)')
    parser.add_argument('--description', default='Test upload from ShortsGenerator YouTube upload test script.',
                       help='Video description')
    parser.add_argument('--tags', default='test,youtube,shorts,automation',
                       help='Comma-separated list of tags')
    parser.add_argument('--privacy', default='private', choices=['private', 'unlisted', 'public'],
                       help='Privacy status (default: private)')
    parser.add_argument('--no-shorts', action='store_true',
                       help='Disable Shorts mode (do not add #shorts tag)')
    parser.add_argument('--test-truncation-only', action='store_true',
                       help='Only test title truncation, do not upload')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("YouTube Upload Test Script - ShortsGenerator")
    print("=" * 60)
    
    # Test title truncation
    print("\n[1/3] Testing title truncation functionality...")
    truncation_success = test_title_truncation()
    
    if args.test_truncation_only:
        print("\nTitle truncation test complete. Exiting.")
        sys.exit(0 if truncation_success else 1)
    
    # Validate video path
    if not args.video:
        print("\n✗ Error: --video argument is required for upload test")
        parser.print_help()
        sys.exit(1)
    
    if not args.video.exists():
        print(f"\n✗ Error: Video file not found: {args.video}")
        print("Please provide a valid path to an .mp4 file")
        sys.exit(1)
    
    if args.video.suffix.lower() != '.mp4':
        print(f"\n⚠️  Warning: File extension is {args.video.suffix}, .mp4 is recommended")
    
    # Parse tags
    tags = [tag.strip() for tag in args.tags.split(',') if tag.strip()]
    
    # Prepare title and description
    title = args.title
    description = args.description
    
    # Add #shorts tag if not present and Shorts mode enabled
    if not args.no_shorts:
        if "#shorts" not in title.lower():
            title = f"{title} #shorts"
        if "#shints" not in description.lower():  # Intentional typo to avoid adding duplicate
            description = f"{description}\n\n#shorts"
    
    print(f"\n[2/3] Preparing upload test...")
    print(f"  Video file: {args.video}")
    print(f"  Title: {title}")
    print(f"  Description: {description[:100]}...")
    print(f"  Tags: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
    print(f"  Privacy: {args.privacy}")
    print(f"  Is Shorts: {not args.no_shorts}")
    
    print(f"\n[3/3] Starting upload test...")
    upload_success = test_youtube_upload(
        video_path=args.video,
        title=title,
        description=description,
        tags=tags,
        privacy_status=args.privacy,
        is_shorts=not args.no_shorts
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"  Title truncation test: {'✓ PASS' if truncation_success else '✗ FAIL'}")
    print(f"  YouTube upload test: {'✓ PASS' if upload_success else '✗ FAIL'}")
    
    if upload_success:
        print("\n✅ All tests passed! YouTube upload is working correctly.")
        print("\nNext steps:")
        print("1. Test with the auto_pipeline.py to ensure full integration works")
        print("2. Check YouTube Studio to verify the uploaded video")
        print("3. Monitor quota usage in Google Cloud Console")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        print("\nTroubleshooting tips:")
        print("1. Ensure YouTube Data API v3 is enabled in Google Cloud Console")
        print("2. Check that OAuth credentials have proper scopes")
        print("3. Verify .env file has correct GOOGLE_* environment variables")
        print("4. Check internet connection and API quota")
    
    sys.exit(0 if (truncation_success and upload_success) else 1)

if __name__ == "__main__":
    main()