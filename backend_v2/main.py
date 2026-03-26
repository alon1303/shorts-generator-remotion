from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import asyncio
from pydantic import BaseModel
import logging
import subprocess

from video_processor import create_shorts_with_captions, batch_process_shorts

# Import Reddit Stories modules
from reddit_story.reddit_client import RedditClient, RedditStory
from reddit_story.story_processor import StoryProcessor
from reddit_story.tts_router import get_tts_client, generate_story_audio_compat as generate_story_audio
from reddit_story.video_composer import VideoComposer, create_shorts_video
from reddit_story.background_manager import BackgroundManager
from reddit_story.keyword_extractor import keyword_extractor

# Import settings
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ShortsGenerator Backend v2 - Automated Pipeline", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class Subtitle(BaseModel):
    text: str
    start: float
    end: float

class VideoUploadResponse(BaseModel):
    success: bool
    message: str
    original_path: Optional[str] = None
    processed_path: Optional[str] = None
    subtitles: Optional[List[Subtitle]] = None

class ProcessVideoRequest(BaseModel):
    input_path: str
    model_size: Optional[str] = "base"

class ProcessVideoResponse(BaseModel):
    success: bool
    message: str
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    segments_count: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BatchProcessRequest(BaseModel):
    input_dir: str
    output_dir: Optional[str] = None
    model_size: Optional[str] = "base"

class BatchProcessResponse(BaseModel):
    success: bool
    message: str
    total: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    failed_files: Optional[List[Dict[str, str]]] = None
    processed_files: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class RedditStoryRequest(BaseModel):
    story_url: Optional[str] = None
    story_text: Optional[str] = None
    subreddit: Optional[str] = "AskReddit"
    theme: Optional[str] = None
    voice_id: Optional[str] = None
    max_duration_minutes: Optional[int] = 3
    split_strategy: Optional[str] = "HYBRID"
    split_into_parts: Optional[bool] = True

class RedditStoryResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    story_id: Optional[str] = None
    estimated_duration: Optional[float] = None
    parts_count: Optional[int] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RedditStoryStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    story_id: Optional[str] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

_jobs: Dict[str, Dict[str, Any]] = {}

@app.get("/")
async def root():
    return {"message": "ShortsGenerator Backend v2", "version": "2.0.0"}

async def process_reddit_story_background(job_id: str, request: RedditStoryRequest):
    try:
        _jobs[job_id]["status"] = "processing"
        _jobs[job_id]["progress"] = 0.1
        _jobs[job_id]["message"] = "Fetching Reddit story..."
        
        reddit_client = RedditClient()
        story = None
        if request.story_url:
            story = await reddit_client.fetch_story_from_url(request.story_url)
        elif request.story_text:
            story = RedditStory(id=str(uuid.uuid4()), title="Custom", text=request.story_text, subreddit=request.subreddit or "AskReddit", url="", score=100, upvote_ratio=0.95, created_utc=0.0, author="custom", is_nsfw=False, word_count=len(request.story_text.split()), estimated_duration=len(request.story_text.split())/150*60)
        elif request.subreddit:
            stories = await reddit_client.fetch_trending_stories(subreddit=request.subreddit, limit=1)
            if stories: story = stories[0]
        
        if not story: raise ValueError("Failed to fetch story")
        
        _jobs[job_id]["story_id"] = story.id
        _jobs[job_id]["metadata"] = {"title": story.title, "subreddit": story.subreddit}
        
        # Keyword Extraction
        _jobs[job_id]["message"] = "Extracting AI keywords..."
        ai_keywords = []
        if settings.use_gemini_keywords:
            try: ai_keywords = await keyword_extractor.extract_keywords(story.title)
            except Exception as e: logger.error(f"Gemini error: {e}")

        processor = StoryProcessor(min_part_duration=60, max_part_duration=90)
        processed_story = processor.process_story(story, split_into_parts=request.split_into_parts)
        
        sanitized_title = "".join(x for x in story.title if x.isalnum() or x in " -_")[:50]
        post_output_dir = OUTPUT_DIR / "reddit_stories" / f"{sanitized_title}_{story.id[:8]}"
        post_output_dir.mkdir(parents=True, exist_ok=True)
        
        from reddit_story.image_generator_new import RedditImageGenerator
        title_card_generator = RedditImageGenerator()
        title_card_path = post_output_dir / "title_card.png"
        await title_card_generator.generate_reddit_post_image(title=story.title, subreddit=story.subreddit, score=story.score, author=story.author, theme_mode="dark", output_path=title_card_path, custom_keywords=ai_keywords)
        
        from reddit_story.tts_router import generate_title_and_story_audio
        text_chunks = [p.text for p in processed_story.parts]
        final_audio_path, story_audio_chunks, card_end_time, timing_data = await generate_title_and_story_audio(title=story.title, story_text_chunks=text_chunks, voice=request.voice_id, engine=settings.TTS_ENGINE.lower())
        
        composer = VideoComposer()
        video_parts = []
        for i, chunk in enumerate(story_audio_chunks, 1):
            part_path = post_output_dir / f"part_{i}_{uuid.uuid4().hex[:8]}.mp4"
            vp = composer.create_video_part(audio_chunk=chunk, theme=request.theme, output_path=part_path, overlay_image_path=title_card_path if i==1 else None, timing_data=timing_data if i==1 else None, custom_keywords=ai_keywords)
            video_parts.append(vp)
        
        if story.url.startswith("https://reddit.com"): reddit_client.mark_post_as_processed(story.id)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 1.0
        _jobs[job_id]["video_path"] = str(post_output_dir)
        _jobs[job_id]["metadata"]["video_parts"] = [str(p) for p in video_parts]
        
    except Exception as e:
        logger.error(f"Job failed: {e}")
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)

@app.post("/generate/reddit-story", response_model=RedditStoryResponse)
async def generate_reddit_story(request: RedditStoryRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "progress": 0.0, "message": "Queued", "metadata": {}, "created_at": asyncio.get_event_loop().time()}
    background_tasks.add_task(process_reddit_story_background, job_id, request)
    return RedditStoryResponse(success=True, message="Started", job_id=job_id)

@app.get("/reddit-story/status/{job_id}", response_model=RedditStoryStatus)
async def get_reddit_story_status(job_id: str):
    if job_id not in _jobs: raise HTTPException(status_code=404, detail="Not found")
    return RedditStoryStatus(job_id=job_id, **_jobs[job_id])

@app.get("/health")
async def health_check(): return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
