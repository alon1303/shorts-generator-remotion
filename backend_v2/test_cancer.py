import asyncio
import json
import os
import subprocess
import warnings
import sys
from pathlib import Path

# השתקת אזהרות גוגל
warnings.filterwarnings("ignore", category=FutureWarning)

# ייבואים
from reddit_story.reddit_client import RedditStory
from reddit_story.models import WordTimestamp, AudioChunk
from reddit_story.story_processor import StoryProcessor
from reddit_story.video_composer import VideoComposer
from reddit_story.image_generator_new import RedditImageGenerator

MOCK_ID = "1da42763580f7d1ac330c3ba521b4d84_1774258959"

# --- תיקון קריטי ל-Windows Encoding ---
# אנחנו מחליפים זמנית את הפונקציה subprocess.run כדי שתמיד תשתמש ב-utf-8
original_run = subprocess.run
def patched_run(*args, **kwargs):
    kwargs['encoding'] = 'utf-8'
    kwargs['errors'] = 'ignore'
    return original_run(*args, **kwargs)
subprocess.run = patched_run
# ---------------------------------------

async def run_fix_test():
    print("🛠️ Starting Clean Mock Pipeline (with Encoding Fix)...")

    # נתיבי קבצים
    cache_dir = Path("cache/elevenlabs/voices")
    mock_audio = cache_dir / f"{MOCK_ID}.mp3"
    mock_json = cache_dir / f"{MOCK_ID}.json"

    if not mock_audio.exists():
        print(f"❌ Error: Missing cache file at {mock_audio}")
        return

    with open(mock_json, "r", encoding="utf-8") as f:
        ts_data = json.load(f)
        word_timestamps = [WordTimestamp(**ts) for ts in ts_data]

    story = RedditStory(
        id="test_fix",
        title="Encoding issue fixed",
        text="Final check of the pipeline. Fixing the Windows charmap error.",
        subreddit="AskReddit",
        url="http://test.com",
        score=15200,
        upvote_ratio=0.98,
        created_utc=0.0,
        author="Alon",
        is_nsfw=False,
        word_count=20,
        estimated_duration=30.0
    )

    processor = StoryProcessor()
    processor.ai_available = False 

    output_dir = Path("outputs/test_fix")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("📸 Generating Title Card...")
    img_gen = RedditImageGenerator()
    title_card = output_dir / "title_card.png"
    await img_gen.generate_reddit_post_image(
        title=story.title, subreddit=story.subreddit, author=story.author,
        score=story.score, output_path=title_card
    )

    print("🎬 Rendering Intermediate Video (This uses FFmpeg)...")
    composer = VideoComposer()
    chunk = AudioChunk(
        chunk_id="fix_v3",
        text=story.text,
        audio_path=mock_audio,
        duration_seconds=30.0,
        word_timestamps=word_timestamps,
        voice_id="adam",
        file_size_bytes=mock_audio.stat().st_size
    )

    temp_path = output_dir / "temp_render.mp4"
    # הקריאה הזו תפעיל את ה-BackgroundManager שקרס קודם
    composer.create_video_part(
        audio_chunk=chunk,
        output_path=temp_path,
        overlay_image_path=title_card,
        timing_data={"card_duration": 3.0}
    )

    final_path = output_dir / "final_fast_video.mp4"
    print("⏩ Applying 1.5x Speedup...")
    
    cmd = [
        'ffmpeg', '-y', '-i', str(temp_path),
        '-filter_complex', "[0:v]setpts=0.666*PTS[v];[0:a]atempo=1.5[a]",
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'ultrafast', str(final_path)
    ]
    
    subprocess.run(cmd, check=True)
    
    if temp_path.exists():
        os.remove(temp_path)

    print(f"✅ Success! Video ready at: {final_path}")

if __name__ == "__main__":
    asyncio.run(run_fix_test())