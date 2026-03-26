import asyncio
import logging
import sys
import os
import json
from pathlib import Path

# Fix path logic to support running from both root and backend_v2
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "backend_v2":
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.join(current_dir, "backend_v2"))

from reddit_story.models import AudioChunk, WordTimestamp
from reddit_story.reddit_client import RedditStory
from reddit_story.story_processor import ProcessedStory, StoryPart, SplitStrategy, StoryProcessor
from reddit_story.video_composer import VideoComposer
from reddit_story.image_generator_new import RedditImageGenerator
from reddit_story.audio_utils import remove_silences, map_timestamp_to_new_time
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION FOR MOCK ---
# Updated to the LATEST audio/json found in cache from the last run
CACHE_BASE_NAME = "284f4695b8b0e993e57a2616b1bf1054_1774470702"
MERGED_AUDIO_NAME = "merged_first_part_7b09e751.mp3"

CACHE_DIR = Path(current_dir) / "cache" / "elevenlabs" / "voices"
MERGED_DIR = Path(current_dir) / "cache" / "merged_parts"

# Using the MERGED audio which is what the real pipeline uses for part 1
AUDIO_PATH = MERGED_DIR / MERGED_AUDIO_NAME
# Fallback to lofi if not exists for testing
if not AUDIO_PATH.exists():
    AUDIO_PATH = Path(current_dir) / "assets" / "audio" / "lofi_bg.mp3"

JSON_PATH = CACHE_DIR / f"{CACHE_BASE_NAME}.json"
STORY_TITLE = "AITAH for calling the police on a neighbor who keeps stealing my cat?"

async def mock_pipeline(output_dir_name: str = "test_mock_sync_fix"):
    """
    A mock version of the main pipeline to test synchronization.
    """
    logger.info("🧪 Starting SYNC TEST MOCK Pipeline")
    
    # 0. Setup Output Directory
    final_output_base = settings.OUTPUT_DIR / output_dir_name
    final_output_base.mkdir(parents=True, exist_ok=True)
    
    if not AUDIO_PATH.exists():
        logger.error(f"❌ Required audio file not found at {AUDIO_PATH}")
        return

    try:
        # 1. Mock Story Data
        story = RedditStory(
            id="mock_id_sync_test",
            title=STORY_TITLE,
            text="Mock text content...",
            subreddit="AITAH",
            url="https://reddit.com/mock",
            score=5000,
            upvote_ratio=0.95,
            created_utc=0.0,
            author="CatOwner",
            is_nsfw=False,
            word_count=200,
            estimated_duration=60.0
        )
        
        # 2. Preparation
        image_gen = RedditImageGenerator()
        title_card_path = final_output_base / "title_card.png"
        await image_gen.generate_reddit_post_image(
            title=story.title,
            subreddit=story.subreddit,
            score=story.score,
            author=story.author,
            output_path=title_card_path,
            custom_keywords=["POLICE", "STEALING", "CAT"]
        )
        
        # 3. Prepare Audio Data
        word_timestamps = []
        if JSON_PATH.exists():
            with open(JSON_PATH, 'r') as f:
                raw_data = json.load(f)
                # Handle potential different formats of JSON
                if isinstance(raw_data, dict) and 'alignment' in raw_data:
                    raw_timestamps = raw_data['alignment']['characters']
                else:
                    raw_timestamps = raw_data

            for t in raw_timestamps:
                if isinstance(t, dict):
                    word_timestamps.append(WordTimestamp(
                        word=t.get('word', t.get('character', '')), 
                        start=t['start'], 
                        end=t['end'], 
                        confidence=t.get('confidence', 1.0)
                    ))
        else:
            logger.warning(f"⚠️ JSON Path {JSON_PATH} not found, using dummy timestamps")
            word_timestamps = [
                WordTimestamp(word="TEST", start=0.0, end=1.0),
                WordTimestamp(word="REMOTION", start=1.0, end=2.0),
                WordTimestamp(word="ENGINE", start=2.0, end=3.0)
            ]

        # Timing data (Mocking the router's output)
        timing_data = {
            "title_audio_duration": 2.6, # Based on logs
            "buffer_seconds": 0.5,
            "title_word_count": 12,
            "subtitle_start_time": 2.6 + 0.5 + 0.8,
            "pop_in_duration": 0.6,
            "pop_out_duration": 0.8,
            "card_start_time": 0.0,
            "card_end_time": 2.6 + 0.5
        }
        
        # Create AudioChunk
        chunk = AudioChunk(
            chunk_id="sync_test_chunk",
            audio_path=AUDIO_PATH,
            text=STORY_TITLE,
            word_timestamps=word_timestamps,
            duration_seconds=55.0,
            voice_id="elevenlabs_mock",
            file_size_bytes=0,
            is_first_part=True,
            part_index="1/1"
        )
        
        # 4. Video Composition
        composer = VideoComposer()
        part_output_path = final_output_base / "sync_test_video.mp4"
        
        # IMPORTANT: We DON'T apply remove_silences here because 
        # the MERGED audio is already processed!
        
        result_path = composer.create_video_part(
            audio_chunk=chunk,
            output_path=part_output_path,
            overlay_image_path=title_card_path,
            timing_data=timing_data,
            custom_keywords=["CAT", "POLICE"]
        )
        
        if result_path:
            logger.info(f"✅ SYNC TEST SUCCESS: {result_path}")

    except Exception as e:
        logger.error(f"💥 Mock failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(mock_pipeline())
