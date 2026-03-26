#!/usr/bin/env python3
"""
Quick Preview Tool for Reddit Title Card UI Testing
This script generates a 3-5 second preview that perfectly simulates the production video generation pipeline.
It uses all the same classes and methods as the real pipeline in main.py and video_composer.py.
"""

import logging
import sys
import argparse
import asyncio
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to the Python path (since it's now inside backend_v2)
sys.path.insert(0, str(Path(__file__).parent))

from reddit_story.image_generator_new import RedditImageGenerator
from reddit_story.video_composer import VideoComposer
from reddit_story.background_manager import BackgroundManager
from reddit_story.subtitle_generator import SubtitleGenerator
from reddit_story.tts_router import generate_title_and_story_audio
from config.settings import settings


async def generate_mock_title_card() -> Path:
    """Helper to generate a title card for testing."""
    gen = RedditImageGenerator()
    return await gen.generate_reddit_post_image(
        title="AITA for refusing to give my mom my savings after she 'accidentally' spent her rent money on a vacation?",
        author="u/JusticeSeeker99",
        subreddit="r/AmItheAsshole",
        score=15400,
        comments=1200
    )


async def create_production_preview() -> Path:
    """
    Creates a production-accurate 3-5 second preview.
    Uses the exact same classes and logic as the main production pipeline.
    """
    logger.info("🚀 Starting production-accurate preview generation...")
    
    # Setup mock data
    title_text = "AITA for refusing to give my mom my savings after she 'accidentally' spent her rent money on a vacation?"
    story_chunks = ["I know the title sounds bad, but hear me out. I'm 22 and I've been saving up for a house."]
    
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        output_path = Path("production_preview.mp4")
        
        # Step 1: Generate Audio using the configured TTS Engine (Edge or ElevenLabs)
        # For preview, we force Edge TTS if ElevenLabs is not configured
        engine = settings.TTS_ENGINE
        if engine == "elevenlabs" and not settings.is_elevenlabs_configured():
            logger.warning("ElevenLabs API key not set, falling back to Edge TTS for preview")
            engine = "edge"
            
        logger.info(f"Step 1/6: Generating audio using engine: {engine}")
        
        # Get the correct voice ID based on settings
        voice_id = settings.get_voice_id(engine=engine)
        
        final_audio_path, audio_chunks, title_duration, timing_data = await generate_title_and_story_audio(
            title=title_text,
            story_text_chunks=story_chunks,
            voice=voice_id,
            engine=engine
        )
        
        # Step 2: Generate Title Card
        logger.info("Step 2/6: Generating title card image...")
        title_card_path = await generate_mock_title_card()
        
        # Step 3: Get Background Video
        logger.info("Step 3/6: Selecting background video...")
        bg_manager = BackgroundManager(settings.BACKGROUNDS_DIR)
        
        # Try to find any background if the default theme is empty
        bg_video = bg_manager.get_random_background(settings.DEFAULT_BACKGROUND_THEME)
        
        if not bg_video:
            # Try "food" or "oddly satisfying" which we saw had videos
            for theme in ["food", "oddly satisfying"]:
                logger.info(f"Retrying with theme: {theme}")
                bg_video = bg_manager.get_random_background(theme)
                if bg_video:
                    break
        
        if not bg_video:
            raise RuntimeError(f"No background videos found in {settings.BACKGROUNDS_DIR}. Please add videos to assets/backgrounds")

        # Step 4: Generate Subtitles
        logger.info("Step 4/6: Generating subtitles...")
        sub_gen = SubtitleGenerator()
        subtitle_path = temp_dir / "subtitles.ass"
        
        # audio_chunks is a list of AudioChunk objects from generate_title_and_story_audio
        # We need the word_timestamps from the first chunk (which includes title)
        word_timestamps = audio_chunks[0].word_timestamps if audio_chunks else []
        
        # Calculate total duration for subtitles
        total_audio_duration = audio_chunks[0].duration_seconds if audio_chunks else 0
        
        sub_gen.generate_ass_from_word_timestamps(
            word_timestamps=word_timestamps,
            audio_duration=total_audio_duration,
            output_path=subtitle_path
        )
        
        # Step 5: Compose Video
        logger.info("Step 5/6: Composing final video...")
        composer = VideoComposer()
        
        # We use create_complete_shorts_video since it's the main production method
        # audio_chunks[0] already contains merged title + first part
        output_path = composer.create_complete_shorts_video(
            audio_chunks=[audio_chunks[0]], # Only use first chunk for preview
            theme=None, # Uses default theme
            output_path=output_path,
            overlay_image_path=title_card_path,
            pop_sfx_path=None, # Settings will handle this if configured
            timing_data=timing_data
        )
        
        logger.info("Step 6/6: Verifying output...")
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"✅ Production preview created successfully: {output_path}")
            return output_path
        else:
            raise RuntimeError(f"Output video not created: {output_path}")


async def main_async(args):
    """Async main function."""
    try:
        output_path = await create_production_preview()
        
        print("\n" + "=" * 60)
        print("🎉 PRODUCTION PREVIEW COMPLETE!")
        print("=" * 60)
        print(f"Output video: {output_path}")
        print(f"Using TTS Engine: {settings.TTS_ENGINE}")
            
    except Exception as e:
        logger.error(f"❌ Preview generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Production-accurate preview for Reddit Stories pipeline")
    parser.add_argument("--mode", choices=["preview", "subtitle_test"], default="preview")
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
