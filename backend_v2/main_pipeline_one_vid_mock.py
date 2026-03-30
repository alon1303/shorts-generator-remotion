import asyncio
import logging
import sys
import os
import json
import subprocess
import tempfile
import shutil
import uuid
from pathlib import Path

# Fix path logic to support running from both root and backend_v2
current_dir = os.path.dirname(os.path.abspath(__file__))
base_path = Path(current_dir)
if base_path.name == "backend_v2":
    root_path = base_path.parent
    sys.path.append(current_dir)
else:
    root_path = base_path
    sys.path.append(os.path.join(current_dir, "backend_v2"))

from reddit_story.models import AudioChunk, WordTimestamp
from reddit_story.reddit_client import RedditStory
from reddit_story.video_composer import VideoComposer
from reddit_story.image_generator_new import RedditImageGenerator
from reddit_story.audio_utils import (
    remove_silences,
    map_timestamp_to_new_time,
    adjust_word_timestamps,
    get_audio_duration,
)
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION FOR MOCK ---
STORY_CACHE_ID = "422901226a0375edd82df25cff55d4c6_1774258814"
TITLE_CACHE_ID = "422e12bc2d279215785a9ce9bb6f121e_1774258806"

# נתיבים מדויקים מקריאת תיקיית השורש
CACHE_DIR = base_path / "cache" / "elevenlabs" / "voices"

BG_MUSIC_PATH = root_path / "backend_v2" / "assets" / "audio" / "lofi_bg.mp3"
if not BG_MUSIC_PATH.exists():
    BG_MUSIC_PATH = root_path / "assets" / "audio" / "lofi_bg.mp3"

STORY_TITLE = "AITA for cutting off my son after his mom past away?"


def load_timestamps(json_path: Path):
    if not json_path.exists():
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        if isinstance(raw_data, dict) and "alignment" in raw_data:
            raw_timestamps = raw_data["alignment"]["characters"]
        else:
            raw_timestamps = raw_data

    word_timestamps = []
    for t in raw_timestamps:
        if isinstance(t, dict):
            word_timestamps.append(
                WordTimestamp(
                    word=t.get("word", t.get("character", "")),
                    start=t["start"],
                    end=t["end"],
                    confidence=t.get("confidence", 1.0),
                )
            )
    return word_timestamps


async def mock_pipeline(output_dir_name: str = "test_mock_sync_fix"):
    logger.info("🧪 Starting RAW MOCK Pipeline with LoFi & 1.4x Speed")

    # הגדרת המהירות הסופית של הסרטון (וידאו + אודיו) ל-1.4
    settings.FINAL_VIDEO_SPEED = 1.4

    # 0. Setup Output Directory
    final_output_base = settings.OUTPUT_DIR / output_dir_name
    final_output_base.mkdir(parents=True, exist_ok=True)

    title_audio_raw = CACHE_DIR / f"{TITLE_CACHE_ID}.mp3"
    title_json_raw = CACHE_DIR / f"{TITLE_CACHE_ID}.json"
    story_audio_raw = CACHE_DIR / f"{STORY_CACHE_ID}.mp3"

    # Support both .mp3 and .wav extensions for cache
    if not story_audio_raw.exists():
        story_audio_raw = CACHE_DIR / f"{STORY_CACHE_ID}.wav"
    if not title_audio_raw.exists():
        title_audio_raw = CACHE_DIR / f"{TITLE_CACHE_ID}.wav"

    story_json_raw = CACHE_DIR / f"{STORY_CACHE_ID}.json"

    if not story_audio_raw.exists() or not title_audio_raw.exists():
        logger.error(f"❌ קבצי הגלם לא נמצאו בתיקייה: {CACHE_DIR}")
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
            estimated_duration=60.0,
        )

        # 2. Extract Keywords using Gemini
        ai_keywords = []
        try:
            # Import the keyword extractor
            from reddit_story.keyword_extractor import keyword_extractor

            logger.info("Extracting keywords using Gemini...")
            ai_keywords = await keyword_extractor.extract_keywords(story.title)
            logger.info(f"AI extracted keywords: {ai_keywords}")
        except Exception as e:
            logger.error(f"Failed to extract keywords with Gemini: {e}")
            # Fallback to heuristic keywords
            ai_keywords = ["POLICE", "STEALING", "CAT"]

        # 3. Preparation (Image)
        image_gen = RedditImageGenerator()
        title_card_path = final_output_base / "title_card.png"
        await image_gen.generate_reddit_post_image(
            title=story.title,
            subreddit=story.subreddit,
            score=story.score,
            author=story.author,
            output_path=title_card_path,
            custom_keywords=ai_keywords,
        )

        # 3. Process Title Audio & JSON
        logger.info("Processing Title...")
        title_timestamps = load_timestamps(title_json_raw)
        cleaned_title_path, title_timing_map = remove_silences(title_audio_raw)
        title_duration = get_audio_duration(cleaned_title_path)

        if title_timing_map and title_timestamps:
            for ts in title_timestamps:
                ts.start = map_timestamp_to_new_time(ts.start, title_timing_map)
                ts.end = map_timestamp_to_new_time(ts.end, title_timing_map)

        # 4. Process Story Audio & JSON
        logger.info("Processing Story...")
        story_timestamps = load_timestamps(story_json_raw)
        cleaned_story_path, story_timing_map = remove_silences(story_audio_raw)
        story_duration = get_audio_duration(cleaned_story_path)

        if story_timing_map and story_timestamps:
            for ts in story_timestamps:
                ts.start = map_timestamp_to_new_time(ts.start, story_timing_map)
                ts.end = map_timestamp_to_new_time(ts.end, story_timing_map)

        # 5. Merge Exactly like tts_router.py
        buffer_seconds = 0.5
        pop_out_duration = 0.8
        card_end_time = title_duration + buffer_seconds
        total_gap = buffer_seconds + pop_out_duration
        delay_ms = int(total_gap * 1000)
        story_start_time = title_duration + total_gap

        logger.info(
            f"Merging audio. Title duration: {title_duration}s, Gap: {total_gap}s, Story starts at: {story_start_time}s"
        )

        merged_audio_path = (
            final_output_base / f"merged_mock_{uuid.uuid4().hex[:8]}.wav"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(cleaned_title_path),
            "-i",
            str(cleaned_story_path),
        ]

        if BG_MUSIC_PATH.exists():
            logger.info("🎵 Adding Lo-Fi background music...")
            cmd.extend(["-stream_loop", "-1", "-i", str(BG_MUSIC_PATH)])
            # הגדלנו את הווליום ל-25% והוספנו normalize=0 כדי לא להחליש את הקריין
            filter_str = (
                f"[1:a]adelay={delay_ms}|{delay_ms}[delayed_story];"
                f"[0:a][delayed_story]concat=n=2:v=0:a=1[voice];"
                f"[2:a]atrim=start=17,asetpts=PTS-STARTPTS,volume=0.25[bg];"
                f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[out]"
            )
        else:
            logger.warning("⚠️ Lo-Fi background music not found. Merging without it.")
            filter_str = (
                f"[1:a]adelay={delay_ms}|{delay_ms}[delayed_story];"
                f"[0:a][delayed_story]concat=n=2:v=0:a=1[out]"
            )

        cmd.extend(
            [
                "-filter_complex",
                filter_str,
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(merged_audio_path),
            ]
        )

        process = subprocess.run(cmd, capture_output=True, text=True)

        # הדפסת שגיאות אם ffmpeg נכשל מסיבה כלשהי
        if process.returncode != 0:
            logger.error(f"❌ FFmpeg merge failed! Error:\n{process.stderr}")
            return

        # 6. Adjust Timestamps & Create Final Chunk
        adjusted_story_timestamps = adjust_word_timestamps(
            story_timestamps, story_start_time
        )
        combined_timestamps = title_timestamps + adjusted_story_timestamps
        total_duration = title_duration + total_gap + story_duration

        chunk = AudioChunk(
            chunk_id="sync_test_chunk",
            audio_path=merged_audio_path,
            text=STORY_TITLE,
            word_timestamps=combined_timestamps,
            duration_seconds=total_duration,
            voice_id="elevenlabs_mock",
            file_size_bytes=merged_audio_path.stat().st_size,
            is_first_part=True,
            part_index="1/1",
            title_word_count=len(title_timestamps),
        )

        timing_data = {
            "title_audio_duration": title_duration,
            "buffer_seconds": buffer_seconds,
            "title_word_count": chunk.title_word_count,
            "subtitle_start_time": story_start_time,
            "pop_in_duration": 0.6,
            "pop_out_duration": pop_out_duration,
            "card_start_time": 0.0,
            "card_end_time": card_end_time,
        }

        # 7. Video Composition
        logger.info("Composing Final Video...")
        composer = VideoComposer()
        part_output_path = final_output_base / "sync_test_video.mp4"

        result_path = composer.create_video_part(
            audio_chunk=chunk,
            output_path=part_output_path,
            overlay_image_path=title_card_path,
            timing_data=timing_data,
            custom_keywords=ai_keywords,
        )

        if result_path:
            logger.info(f"✅ SYNC TEST SUCCESS: {result_path}")

    except Exception as e:
        logger.error(f"💥 Mock failed: {e}")
        import traceback

        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(mock_pipeline())
