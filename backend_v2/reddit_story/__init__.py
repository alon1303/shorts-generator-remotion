"""
Reddit Stories module for ShortsGenerator.
Provides functionality to fetch, process, and convert Reddit stories into Shorts videos.
"""

from .reddit_client import RedditClient, RedditStory
from .story_processor import StoryProcessor, ProcessedStory, StoryPart, SplitStrategy
from .models import AudioChunk

__all__ = [
    "RedditClient", 
    "RedditStory",
    "StoryProcessor", 
    "ProcessedStory", 
    "StoryPart", 
    "SplitStrategy",
    "AudioChunk",
]
__version__ = "2.0.0"
