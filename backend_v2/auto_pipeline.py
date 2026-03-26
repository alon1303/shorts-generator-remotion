"""
End-to-End automation orchestrator for ShortsGenerator project.
Fetches stories, generates videos sequentially, and uploads to YouTube Shorts.
"""

import asyncio
import logging
import time
import json
import re
import shutil
import subprocess
import traceback
import signal
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Project imports
from config.settings import settings
from reddit_story.reddit_client import RedditClient, RedditStory
from reddit_story.story_processor import StoryProcessor
from reddit_story.tts_router import generate_title_and_story_audio
from reddit_story.video_composer import VideoComposer, create_shorts_video
from reddit_story.image_generator_new import RedditImageGenerator
from youtube.uploader import YouTubeUploader, AsyncYouTubeUploader, YouTubeUploadResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.OUTPUT_DIR / 'auto_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PipelineStats:
    """Statistics tracker for the automation pipeline."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_stories_processed = 0
        self.successful_videos = 0
        self.failed_videos = 0
        self.quota_exceeded = 0
        self.network_errors = 0
        self.processing_errors = 0
        self.upload_errors = 0
        self.story_durations = []
        self.video_durations = []
        
        # Create stats file
        self.stats_file = settings.DATA_DIR / "pipeline_stats.json"
        self._load_stats()
    
    def _load_stats(self):
        """Load previous stats from file."""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.total_stories_processed = data.get('total_stories_processed', 0)
                    self.successful_videos = data.get('successful_videos', 0)
                    self.failed_videos = data.get('failed_videos', 0)
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")
    
    def save_stats(self):
        """Save current stats to file."""
        try:
            data = {
                'total_stories_processed': self.total_stories_processed,
                'successful_videos': self.successful_videos,
                'failed_videos': self.failed_videos,
                'quota_exceeded': self.quota_exceeded,
                'network_errors': self.network_errors,
                'processing_errors': self.processing_errors,
                'upload_errors': self.upload_errors,
                'last_updated': datetime.now().isoformat(),
                'runtime_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
                'average_story_duration': self.average_story_duration,
                'average_video_duration': self.average_video_duration,
                'success_rate': self.success_rate,
            }
            
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save stats: {e}")
    
    @property
    def average_story_duration(self) -> float:
        if self.story_durations:
            return sum(self.story_durations) / len(self.story_durations)
        return 0.0
    
    @property
    def average_video_duration(self) -> float:
        if self.video_durations:
            return sum(self.video_durations) / len(self.video_durations)
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_stories_processed == 0:
            return 0.0
        return (self.successful_videos / self.total_stories_processed) * 100
    
    def add_story_processed(self, success: bool, story_duration: float = 0, video_duration: float = 0):
        self.total_stories_processed += 1
        if success:
            self.successful_videos += 1
            if story_duration > 0:
                self.story_durations.append(story_duration)
            if video_duration > 0:
                self.video_durations.append(video_duration)
        else:
            self.failed_videos += 1
        self.save_stats()
    
    def add_error(self, error_type: str):
        if error_type == 'quota': self.quota_exceeded += 1
        elif error_type == 'network': self.network_errors += 1
        elif error_type == 'processing': self.processing_errors += 1
        elif error_type == 'upload': self.upload_errors += 1
        self.save_stats()
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            'runtime': str(datetime.now() - self.start_time),
            'total_stories_processed': self.total_stories_processed,
            'successful_videos': self.successful_videos,
            'failed_videos': self.failed_videos,
            'success_rate': f"{self.success_rate:.1f}%",
            'average_story_duration': f"{self.average_story_duration:.1f}s",
            'average_video_duration': f"{self.average_video_duration:.1f}s",
            'quota_exceeded': self.quota_exceeded,
            'network_errors': self.network_errors,
            'processing_errors': self.processing_errors,
            'upload_errors': self.upload_errors,
        }

class AutoPipeline:
    def __init__(self, subreddits=None, stories_per_run=3, max_video_duration_minutes=3, theme=None, 
                 voice_id=None, upload_to_youtube=True, youtube_privacy_status="private", 
                 delay_between_uploads_seconds=300, max_retries_per_story=2, skip_processed_posts=True,
                 data_dir=None, bg_music_path=None):
        
        self.subreddits = subreddits or ["AmItheAsshole", "tifu", "TrueOffMyChest", "pettyrevenge", "EntitledParents"]
        self.stories_per_run = stories_per_run
        self.max_video_duration = max_video_duration_minutes * 60
        self.theme = theme or settings.DEFAULT_BACKGROUND_THEME
        self.voice_id = voice_id or settings.DEFAULT_VOICE_ID
        self.bg_music_path = bg_music_path or settings.DEFAULT_BGM_PATH
        self.upload_to_youtube = upload_to_youtube
        self.youtube_privacy_status = youtube_privacy_status
        self.delay_between_uploads = delay_between_uploads_seconds
        self.max_retries = max_retries_per_story
        self.skip_processed_posts = skip_processed_posts
        self.data_dir = Path(data_dir) if data_dir else settings.DATA_DIR / "pipeline"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.reddit_client = None
        self.youtube_uploader = None
        self.async_youtube_uploader = None
        self.stats = PipelineStats()
        self.is_running = False
        self.last_upload_time = None

    async def initialize(self):
        try:
            logger.info("Initializing pipeline components...")
            self.reddit_client = RedditClient()
            await self.reddit_client.initialize()
            if self.upload_to_youtube:
                self.youtube_uploader = YouTubeUploader()
                self.async_youtube_uploader = AsyncYouTubeUploader(self.youtube_uploader)
                if not self.youtube_uploader.validate_credentials():
                    service = self.youtube_uploader.get_authenticated_service()
                    if not service:
                        self.upload_to_youtube = False
            return True
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            return False

    async def cleanup(self):
        if self.reddit_client:
            await self.reddit_client.close()

    async def fetch_stories(self) -> List[RedditStory]:
        try:
            stories = await self.reddit_client.fetch_trending_stories(
                subreddit=self.subreddits, time_filter="day", limit=self.stories_per_run * 2,
                min_score=settings.MIN_STORY_SCORE, min_text_length=settings.MIN_STORY_LENGTH,
                max_text_length=settings.MAX_STORY_LENGTH, exclude_nsfw=settings.EXCLUDE_NSFW,
                exclude_processed=self.skip_processed_posts,
            )
            filtered = [s for s in stories if s.estimated_duration <= self.max_video_duration]
            return filtered[:self.stories_per_run]
        except Exception as e:
            logger.error(f"Failed to fetch stories: {e}")
            self.stats.add_error('network')
            return []

    async def process_story(self, story: RedditStory) -> Optional[Path]:
        logger.info(f"Processing story: '{story.title[:50]}...'")
        try:
            processor = StoryProcessor(
                min_part_duration=settings.MIN_PART_DURATION,
                max_part_duration=settings.MAX_PART_DURATION,

            )
            processed_story = await processor.process_story(story, split_into_parts=True)
            
            sanitized_title = re.sub(r'[^\w\s-]', '', story.title).strip().replace(' ', '_')[:50]
            post_output_dir = settings.OUTPUT_DIR / "reddit_stories" / f"{sanitized_title}_{story.id[:8]}"
            post_output_dir.mkdir(parents=True, exist_ok=True)
            
            title_card_gen = RedditImageGenerator()
            title_card_path = post_output_dir / "title_card.png"
            await title_card_gen.generate_reddit_post_image(
                title=story.title, subreddit=story.subreddit, score=story.score,
                author=story.author, theme_mode="dark", output_path=title_card_path
            )
            
            text_chunks = []
            for i, part in enumerate(processed_story.parts, 1):
                text = part.text
                if i < len(processed_story.parts):
                    text += f" Like and subscribe for part {i + 1}!"
                text_chunks.append(text)

            # --- התיקון הקריטי כאן: הוספת await לקריאה לפונקציית ה-TTS ---
            final_audio_path, story_audio_chunks, title_duration, timing_data = await generate_title_and_story_audio(
                title=story.title, story_text_chunks=text_chunks, voice=self.voice_id,
                gender=processed_story.detected_gender, engine=settings.TTS_ENGINE.lower(),
                buffer_seconds=1.0
            )
            
            if final_audio_path is None or story_audio_chunks is None:
                logger.error(f"TTS generation failed for story: {story.id}")
                return None
            
            composer = VideoComposer()
            video_parts = []
            for i, audio_chunk in enumerate(story_audio_chunks, 1):
                if audio_chunk.duration_seconds <= 0: continue
                part_path = post_output_dir / f"part_{i}.mp4"
                video_part = composer.create_video_part(
                    audio_chunk=audio_chunk, theme=self.theme, output_path=part_path,
                    overlay_image_path=title_card_path if i == 1 else None,
                    timing_data=timing_data if i == 1 else None, bg_music_path=self.bg_music_path
                )
                video_parts.append(video_part)
            
            final_video_path = post_output_dir / f"{sanitized_title}_final.mp4"
            if len(video_parts) == 1:
                shutil.copy2(video_parts[0], final_video_path)
            else:
                composer.concatenate_videos(video_parts, final_video_path)
            
            self.reddit_client.mark_post_as_processed(story.id)
            self.stats.add_story_processed(success=True, story_duration=story.estimated_duration)
            return final_video_path

        except Exception as e:
            logger.error(f"Failed to process story: {e}")
            self.stats.add_error('processing')
            self.stats.add_story_processed(success=False)
            return None

    async def upload_to_youtube_if_enabled(self, video_path: Path, story: RedditStory):
        if not self.upload_to_youtube or not video_path.exists(): return None
        if self.last_upload_time:
            elapsed = (datetime.now() - self.last_upload_time).total_seconds()
            if elapsed < self.delay_between_uploads:
                await asyncio.sleep(self.delay_between_uploads - elapsed)
        
        try:
            title = self.youtube_uploader.truncate_title_for_youtube(f"{story.title} #shorts")
            description = self.youtube_uploader.generate_description(story.title, story.subreddit, story.url)
            tags = self.youtube_uploader.generate_default_tags(story.subreddit, story.title)
            
            result = await self.async_youtube_uploader.upload_video_async(
                video_path=video_path, title=title, description=description, tags=tags,
                category_id="22", privacy_status=self.youtube_privacy_status, is_shorts=True
            )
            self.last_upload_time = datetime.now()
            if not result.success: self.stats.add_error('quota' if result.quota_exceeded else 'upload')
            return result
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            self.stats.add_error('upload')
            return None

    async def process_story_with_retry(self, story: RedditStory) -> bool:
        for attempt in range(self.max_retries + 1):
            video_path = await self.process_story(story)
            if video_path:
                if self.upload_to_youtube:
                    await self.upload_to_youtube_if_enabled(video_path, story)
                return True
            await asyncio.sleep((attempt + 1) * 10)
        return False

    async def run_single_cycle(self):
        stories = await self.fetch_stories()
        for i, story in enumerate(stories, 1):
            await self.process_story_with_retry(story)
            if i < len(stories): await asyncio.sleep(5)

    async def run_continuous(self, interval_minutes=60, max_cycles=None, stop_on_quota_exceeded=True):
        self.is_running = True
        def handler(s, f): self.is_running = False
        signal.signal(signal.SIGINT, handler)
        
        cycle = 0
        while self.is_running:
            if max_cycles and cycle >= max_cycles: break
            cycle += 1
            await self.run_single_cycle()
            if stop_on_quota_exceeded and self.stats.quota_exceeded > 2: break
            if self.is_running: await asyncio.sleep(interval_minutes * 60)
        await self.cleanup()

    def print_stats(self):
        s = self.stats.get_summary()
        for k, v in s.items(): logger.info(f"{k}: {v}")

async def run_pipeline_from_cli():
    pipeline = AutoPipeline()
    if await pipeline.initialize():
        await pipeline.run_single_cycle()
        pipeline.print_stats()
        await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(run_pipeline_from_cli())