import asyncio
import logging
import sys
import os
import shutil
import re
from pathlib import Path

# Fix path logic to support running from both root and backend_v2
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "backend_v2":
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.join(current_dir, "backend_v2"))

from reddit_story.reddit_client import RedditClient
from reddit_story.story_processor import StoryProcessor
from reddit_story.tts_router import generate_title_and_story_audio
from reddit_story.video_composer import VideoComposer
from reddit_story.keyword_extractor import keyword_extractor
from reddit_story.image_generator_new import RedditImageGenerator
from reddit_story.audio_utils import remove_silences, map_timestamp_to_new_time
from reddit_story.models import WordTimestamp
from config.settings import settings

# Setup logging with UTF-8 support for file and safer terminal output
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_").strip("_")[:50]

async def main_pipeline(url: str, output_dir_name: str = None, tts_engine: str = None):
    """
    The main entry point for creating a video from a Reddit URL.
    This script follows the full automated pipeline.
    """
    logger.info(f"Starting Main Pipeline for URL: {url} (Engine: {tts_engine or settings.TTS_ENGINE})")
    
    try:
        # 1. Fetch Story from Reddit
        reddit_client = RedditClient()
        story = await reddit_client.fetch_story_from_url(url)
        if not story:
            logger.error("Failed to fetch story from Reddit.")
            return

        logger.info(f"Fetched story: '{story.title}' by {story.author}")

        # 0. Setup Output Directory (Now that we have the story title)
        if not output_dir_name:
            output_dir_name = sanitize_filename(story.title)
            
        final_output_base = settings.OUTPUT_DIR / output_dir_name
        final_output_base.mkdir(parents=True, exist_ok=True)
        
        # 2. AI Content Analysis & Splitting
        processor = StoryProcessor()
        processed_story = await processor.process_story(story, split_into_parts=False)
        
        logger.info(f"AI Analysis: {processed_story.total_parts} parts detected.")
        logger.info(f"Gender: {processed_story.detected_gender}, Age: {processed_story.detected_age}")
        
        # 3. Extract Keywords for Title Card (Gemini)
        logger.info("Extracting high-impact keywords for title card...")
        title_keywords = await keyword_extractor.extract_keywords(story.title)
        
        # 4. Generate Professional Title Card
        image_gen = RedditImageGenerator()
        title_card_path = final_output_base / "title_card.png"
        await image_gen.generate_reddit_post_image(
            title=story.title,
            subreddit=story.subreddit,
            score=story.score,
            author=story.author or "RedditUser",
            output_path=title_card_path,
            custom_keywords=title_keywords
        )
        logger.info(f"Title card generated at: {title_card_path}")
        
        # 5. Generate Audio & Synchronize
        logger.info("Generating narration and calculating word timestamps...")
        story_texts = [p.text for p in processed_story.parts]
        
        # This handles the complex logic of title card duration vs story start
        # generate_title_and_story_audio already handles REMOVE_SILENCES inside it!
        title_audio_path, audio_chunks, subtitle_start_time, timing_data = await generate_title_and_story_audio(
            title=story.title,
            story_text_chunks=story_texts,
            gender=processed_story.detected_gender,
            engine=tts_engine
        )
        
        # 6. Video Composition (Part by Part)
        composer = VideoComposer()
        final_videos = []
        
        for i, chunk in enumerate(audio_chunks):
            part_num = i + 1
            logger.info(f"Composing Video Part {part_num}/{len(audio_chunks)}...")
            
            try:
                # --- JUMP CUTS / SILENCE REMOVAL REMOVED FROM HERE ---
                # It is already done inside generate_title_and_story_audio for Part 1
                # and inside generate_audio_chunks for other parts.
                # Re-running it here (on first part especially) was causing sync issues!
                
                # Compose the video
                part_output_path = final_output_base / f"part_{part_num}.mp4"
                part_ai_data = processed_story.parts[i]
                
                result_path = composer.create_video_part(
                    audio_chunk=chunk,
                    output_path=part_output_path,
                    overlay_image_path=title_card_path if chunk.is_first_part else None,
                    timing_data=timing_data if chunk.is_first_part else None,
                    custom_keywords=part_ai_data.power_words # Red highlights for story parts
                )
                
                if result_path:
                    logger.info(f"Part {part_num} SUCCESS: {result_path}")
                    final_videos.append(result_path)
                
            except Exception as part_err:
                logger.error(f"Error in Part {part_num}: {part_err}")
                continue

        logger.info("="*50)
        logger.info(f"PIPELINE COMPLETED: {len(final_videos)} videos generated.")
        logger.info(f"Location: {final_output_base}")
        logger.info("="*50)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def run_interactive():
    """Run the pipeline with interactive user input."""
    # Ensure stdout handles unicode safely
    if sys.platform == 'win32':
        import subprocess
        # Try to set code page to UTF-8
        try:
            subprocess.run(['chcp', '65001'], capture_output=True, shell=True)
        except:
            pass

    print("\n" + "="*50)
    print("SHORTS GENERATOR - VIDEO PIPELINE")
    print("="*50)
    
    # 1. URL Choice
    choice = input("\n❓ Do you want to enter a specific Reddit URL? (y/n): ").lower().strip()
    target_url = None
    
    if choice == 'y':
        target_url = input("🔗 Please enter the Reddit URL: ").strip()
        if not target_url:
            print("❌ Error: No URL provided.")
            return
    else:
        print("🔍 Searching for a trending story...")
        reddit_client = RedditClient()
        stories = await reddit_client.fetch_trending_stories(limit=1, time_filter="day")
        if not stories:
            print("❌ Error: No trending stories found.")
            return
        
        story = stories[0]
        target_url = story.url
        print(f"✨ Found trending story: '{story.title}' (Score: {story.score})")
        print(f"🔗 URL: {target_url}")

    # 2. TTS Choice
    print("\n🎙️ SELECT TTS ENGINE:")
    print("1. Edge TTS (Free, Reliable)")
    print("2. ElevenLabs (Premium, Realistic)")
    
    tts_choice = input("Enter choice (1/2, default 1): ").strip()
    tts_engine = "edge"
    if tts_choice == '2':
        tts_engine = "elevenlabs"
    
    print(f"✅ Using Engine: {tts_engine.upper()}")

    # Run the pipeline
    await main_pipeline(target_url, tts_engine=tts_engine)

if __name__ == "__main__":
    # Run the interactive pipeline
    try:
        asyncio.run(run_interactive())
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
