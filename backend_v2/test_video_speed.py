import asyncio
import logging
import sys
import os
import json
import subprocess
from pathlib import Path

# Fix path logic to support running from both root and backend_v2
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "backend_v2":
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.join(current_dir, "backend_v2"))

from reddit_story.models import AudioChunk, WordTimestamp
from reddit_story.reddit_client import RedditStory
from reddit_story.story_processor import ProcessedStory, StoryPart, SplitStrategy
from reddit_story.video_composer import VideoComposer
from reddit_story.image_generator_new import RedditImageGenerator
from reddit_story.audio_utils import remove_silences, map_timestamp_to_new_time
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION FOR MOCK ---
# These point to existing cached files to avoid API calls
CACHE_BASE_NAME = "5a09dcd7fd0c64753833187d6619f937_1774346164"
CACHE_DIR = Path(current_dir) / "cache" / "elevenlabs" / "voices"
AUDIO_PATH = CACHE_DIR / f"{CACHE_BASE_NAME}.mp3"
JSON_PATH = CACHE_DIR / f"{CACHE_BASE_NAME}.json"
STORY_TITLE = "im not usually petty but this put a smile on my face"

def get_video_duration(video_path: Path) -> float:
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'json', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            return float(json.loads(result.stdout)['format']['duration'])
    except Exception as e:
        logger.error(f"Failed to get duration: {e}")
    return 0.0

async def mock_pipeline(output_dir_name: str = "mock_pipeline_output", speed: float = 1.0):
    """
    A mock version of the main pipeline. 
    It mimics the structure of main_pipeline_one_vid.py but uses local data.
    """
    logger.info(f"\n🧪 Starting MOCK Pipeline with FINAL_VIDEO_SPEED = {speed}")
    
    settings.FINAL_VIDEO_SPEED = speed
    
    # 0. Setup Output Directory
    final_output_base = settings.OUTPUT_DIR / output_dir_name
    final_output_base.mkdir(parents=True, exist_ok=True)
    
    if not AUDIO_PATH.exists() or not JSON_PATH.exists():
        logger.error(f"❌ Required cache files not found at {CACHE_DIR}")
        return

    try:
        # 1. Mock Story Data (Instead of RedditClient)
        story = RedditStory(
            id="mock_id_123",
            title=STORY_TITLE,
            text="Driving to work on the highway I was cut off by a guy in a convertible...",
            subreddit="pettyrevenge",
            url="https://reddit.com/mock",
            score=1500,
            upvote_ratio=0.98,
            created_utc=0.0,
            author="MockUser",
            is_nsfw=False,
            word_count=100,
            estimated_duration=60.0
        )
        
        # 2. Mock AI Splitting Results (Instead of StoryProcessor)
        processed_story = ProcessedStory(
            story=story,
            parts=[
                StoryPart(
                    part_number=1,
                    text=story.text,
                    word_count=100,
                    estimated_duration=70.0,
                    start_index=0,
                    end_index=len(story.text),
                    power_words=["petty", "smile", "highway", "convertible"]
                )
            ],
            total_parts=1,
            total_duration=70.0,
            strategy_used=SplitStrategy.AI,
            detected_gender="male",
            detected_age=30
        )
        
        # 3. Mock Keywords for Title Card
        title_keywords = ["petty", "smile", "face"]
        
        # 4. Generate Title Card Image (Real generation, but local)
        image_gen = RedditImageGenerator()
        title_card_path = final_output_base / "title_card.png"
        await image_gen.generate_reddit_post_image(
            title=story.title,
            subreddit=story.subreddit,
            score=story.score,
            author=story.author,
            output_path=title_card_path,
            custom_keywords=title_keywords
        )
        
        # 5. Prepare Audio (Loading from Cache instead of TTS)
        with open(JSON_PATH, 'r') as f:
            raw_timestamps = json.load(f)
        
        word_timestamps = [
            WordTimestamp(word=t['word'], start=t['start'], end=t['end'], confidence=t.get('confidence', 1.0))
            for t in raw_timestamps
        ]
        
        # Assuming the first 12 words are the title
        title_end_time = word_timestamps[11].end if len(word_timestamps) > 11 else 4.0
        timing_data = {
            "title_narration_duration": title_end_time,
            "buffer_after_title": 1.5,
            "total_title_display_time": title_end_time + 1.5
        }
        
        # Create an AudioChunk mock
        chunk = AudioChunk(
            chunk_id="mock_chunk",
            audio_path=AUDIO_PATH,
            text=story.title + " " + story.text,
            word_timestamps=word_timestamps,
            duration_seconds=70.0,
            voice_id="mock_voice",
            file_size_bytes=0,
            is_first_part=True,
            part_index="1/1"
        )
        
        # 6. Video Composition
        composer = VideoComposer()
        
        # --- JUMP CUTS / SILENCE REMOVAL (Real processing on mock audio) ---
        if settings.REMOVE_SILENCES:
            cleaned_audio_path, timing_map = remove_silences(chunk.audio_path)
            
            if timing_map:
                chunk.audio_path = cleaned_audio_path
                adjusted_timestamps = []
                for wt in word_timestamps:
                    new_start = map_timestamp_to_new_time(wt.start, timing_map)
                    new_end = map_timestamp_to_new_time(wt.end, timing_map)
                    adjusted_timestamps.append(WordTimestamp(word=wt.word, start=new_start, end=new_end, confidence=wt.confidence))
                chunk.word_timestamps = adjusted_timestamps

        # Compose video
        part_output_path = final_output_base / f"mock_video_speed_{speed}.mp4"
        result_path = composer.create_video_part(
            audio_chunk=chunk,
            output_path=part_output_path,
            overlay_image_path=title_card_path,
            timing_data=timing_data,
            custom_keywords=processed_story.parts[0].power_words
        )
        
        if result_path:
            duration = get_video_duration(Path(result_path))
            logger.info(f"✅ Video generated at speed {speed}: {result_path}")
            logger.info(f"⏱️ FINAL DURATION: {duration:.2f} seconds")
            return duration

    except Exception as e:
        logger.error(f"💥 Mock pipeline failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    return 0.0

async def run_tests():
    duration_1 = await mock_pipeline("test_mock_speed", speed=1.0)
    duration_1_2 = await mock_pipeline("test_mock_speed", speed=1.2)
    
    logger.info("\n" + "="*50)
    logger.info("📊 SUMMARY OF SPEED TEST:")
    logger.info(f"Duration at speed 1.0: {duration_1:.2f}s")
    logger.info(f"Duration at speed 1.2: {duration_1_2:.2f}s")
    
    if duration_1_2 < duration_1:
        logger.info(f"✅ SPEEDUP SUCCESSFUL! Video is {(duration_1 - duration_1_2):.2f}s shorter.")
    else:
        logger.info("❌ SPEEDUP FAILED. Durations are the same or longer.")
    logger.info("="*50)


if __name__ == "__main__":
    asyncio.run(run_tests())
