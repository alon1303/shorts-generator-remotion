
import asyncio
import json
from pathlib import Path
from reddit_story.models import WordTimestamp, AudioChunk
from reddit_story.video_composer import VideoComposer
from config.settings import settings
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_video_generation_from_cache():
    print("Starting full video generation test using EXISTING CACHE (ElevenLabs)...")
    
    # 1. Setup paths
    cache_dir = Path("cache/elevenlabs/voices")
    output_dir = Path("outputs/test_cache_video")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Use specific cached MP3 and JSON files
    target_id = "1da42763580f7d1ac330c3ba521b4d84_1774258959"
    test_mp3 = cache_dir / f"{target_id}.mp3"
    test_json = cache_dir / f"{target_id}.json"
    
    if not test_mp3.exists() or not test_json.exists():
        print(f"Error: Could not find cached files for ID {target_id} in {cache_dir}")
        return

    print(f"Using cached files for video test:")
    print(f"  MP3: {test_mp3}")
    print(f"  JSON: {test_json}")
    
    # 3. Load timestamps and prepare AudioChunk
    with open(test_json, "r", encoding='utf-8') as f:
        data = json.load(f)
        word_timestamps = [WordTimestamp.from_dict(w) for w in data]
    
    from reddit_story.audio_utils import get_audio_duration
    
    # IMPORTANT: We need to trigger the silence removal logic that we just implemented
    # Since we are manually creating the AudioChunk here, we should use the ElevenLabsClient 
    # to load it if possible, or manually apply the logic.
    # To be safe and test the ACTUAL integration, we'll use the ElevenLabsClient with a mock.
    
    from reddit_story.elevenlabs_client import ElevenLabsClient
    client = ElevenLabsClient()
    
    # Mock the cache key to point to our chosen file
    cache_key = test_mp3.name.split('_')[0]
    client._generate_cache_key = lambda text, voice: cache_key
    
    print("Loading audio through ElevenLabsClient to trigger silence removal...")
    # This will trigger the silence removal and timestamp adjustment we just added
    path, duration, adjusted_timestamps = await client.text_to_speech_with_timestamps("dummy text")
    
    print(f"Original duration: {get_audio_duration(test_mp3):.2f}s")
    print(f"New duration (after silence removal): {duration:.2f}s")
    
    chunk = AudioChunk(
        chunk_id=str(uuid.uuid4())[:8],
        text="This is a test story from cache.", # Placeholder
        audio_path=path,
        duration_seconds=duration,
        word_timestamps=adjusted_timestamps,
        voice_id="adam",
        file_size_bytes=path.stat().st_size if path else 0
    )
    
    # 4. Initialize VideoComposer and generate video
    composer = VideoComposer()
    
    output_path = output_dir / "test_cache_silence.mp4"
    
    print("\nComposing video...")
    # Using the existing method name from VideoComposer
    video_path = composer.create_complete_shorts_video(
        audio_chunks=[chunk],
        theme="minecraft",
        output_path=output_path
    )
    
    print(f"\nSUCCESS! Video generated at: {video_path}")
    print("You can check the subtitles in the video to ensure they are synced with the trimmed audio.")

if __name__ == "__main__":
    # Ensure we are in the right directory if run from root
    if Path("backend_v2").exists() and not Path("reddit_story").exists():
        os.chdir("backend_v2")
    
    import os
    asyncio.run(test_video_generation_from_cache())
