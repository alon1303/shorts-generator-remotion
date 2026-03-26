"""
Configuration management for the ShortsGenerator application.
Handles environment variables, default values, and validation.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    Uses pydantic for validation and type conversion.
    
    IMPORTANT: Secrets (API Keys) should stay in .env.
    All other configurations should be defined here.
    """
    
    # --- SECRETS (Must stay in .env) ---
    ELEVENLABS_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None

    # --- APPLICATION ---
    APP_NAME: str = "ShortsGenerator Backend v2"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # --- SERVER ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # --- DIRECTORIES ---
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    DATA_DIR: Path = BASE_DIR / "data"
    CACHE_DIR: Path = BASE_DIR / "cache"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    BACKGROUNDS_DIR: Path = ASSETS_DIR / "backgrounds"
    DEFAULT_BGM_PATH: Path = ASSETS_DIR / "audio" / "lofi_bg.mp3"
    
    # --- REDDIT ---
    REDDIT_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    DEFAULT_SUBREDDIT: str = "AskReddit"
    DEFAULT_TIME_FILTER: str = "day"  # hour, day, week, month, year, all
    MIN_STORY_SCORE: int = 100
    MIN_STORY_LENGTH: int = 200  # characters
    MAX_STORY_LENGTH: int = 5000  # characters
    EXCLUDE_NSFW: bool = True
    
    # --- TTS & VOICES ---
    TTS_ENGINE: str = "edge" # "edge" or "elevenlabs"
    
    # Edge TTS Voices
    EDGE_TTS_VOICE_FEMALE: str = "en-US-JennyNeural"
    EDGE_TTS_VOICE_MALE: str = "en-US-ChristopherNeural"
    EDGE_TTS_VOICE_ARIA: str = "en-US-AriaNeural"
    
    # ElevenLabs Voice IDs
    ELEVEN_VOICE_RACHEL: str = "21m00Tcm4TlvDq8ikWAM"
    ELEVEN_VOICE_ADAM: str = "pNInz6obpgDQGcFmaJgB"
    ELEVEN_VOICE_ELLI: str = "MF3mGyEYCl7XYWbV9V6O"
    ELEVEN_VOICE_JOSH: str = "TxGEqnHWrfWFTfGW9XjX"

    DEFAULT_VOICE_ID: str = "en-US-ChristopherNeural"
    
    # Voice Aliases for easy switching
    VOICE_ALIASES: Dict[str, str] = {
        "female": "en-US-JennyNeural",
        "male": "en-US-ChristopherNeural", 
        "aria": "en-US-AriaNeural",
        "christopher": "en-US-ChristopherNeural",
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "adam": "pNInz6obpgDQGcFmaJgB",
        "elli": "MF3mGyEYCl7XYWbV9V6O",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "default": "en-US-ChristopherNeural"
    }
    
    # --- BACKGROUND VIDEO ---
    DEFAULT_BACKGROUND_THEME: str = "minecraft"
    BACKGROUND_THEMES: List[str] = ["abstract", "food", "gta", "lofi", "minecraft", "nature", "oddly satisfying", "subway surfer"]
    MIN_BACKGROUND_DURATION: int = 60
    MAX_BACKGROUND_DURATION: int = 300
    
    # Dynamic background clip settings
    BACKGROUND_CLIP_DURATION_MIN: float = 5.0
    BACKGROUND_CLIP_DURATION_MAX: float = 10.0
    BACKGROUND_DYNAMIC_SWITCHING: bool = True
    BGM_VOLUME_DELTA: float = -10.0
    
    # --- AUDIO PROCESSING (JUMP CUTS) ---
    REMOVE_SILENCES: bool = True
    REMOVE_SILENCES_EDGE: bool = True  # Edge TTS often has unnatural pauses
    REMOVE_SILENCES_ELEVENLABS: bool = False  # ElevenLabs has natural pacing
    SILENCE_THRESHOLD_DB: float = -40.0
    MIN_SILENCE_DURATION_MS: int = 400
    KEEP_SILENCE_MS: int = 100
    
    # --- VIDEO OUTPUT ---
    VIDEO_ENGINE: str = "remotion"  # options: "ffmpeg", "remotion"
    TARGET_WIDTH: int = 1080
    TARGET_HEIGHT: int = 1920
    TARGET_FPS: int = 30
    VIDEO_CRF: int = 23
    VIDEO_PRESET: str = "veryfast"
    AUDIO_BITRATE: str = "128k"
    FINAL_VIDEO_SPEED: float = 1.0
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".avi", ".mkv", ".mov", ".webm"]
    MAX_FILE_SIZE_MB: int = 100
    
    # --- STORY SEGMENTATION & AI ---
    MIN_PART_DURATION: int = 30
    MAX_PART_DURATION: int = 60
    STORY_AI_SPLIT_THRESHOLD: float = 180.0
    AI_MIN_PART_DURATION: int = 50 # This will be our enforced minimum part duration for AI splits
    
    # ElevenLabs Voice Settings
    ELEVENLABS_STABILITY: float = 0.5
    ELEVENLABS_SIMILARITY_BOOST: float = 0.75
    ELEVENLABS_STYLE: float = 0.0
    ELEVENLABS_USE_SPEAKER_BOOST: bool = True
    
    # Note: ElevenLabs API officially supports speed between 0.7 and 1.2
    ELEVENLABS_SPEED: float = 1.2
    
    GEMINI_MODEL: str = "gemini-flash-latest"
    
    # --- CACHING ---
    ENABLE_CACHE: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @validator("TTS_ENGINE")
    def validate_tts_engine(cls, v):
        if v.lower() not in ["edge", "elevenlabs"]:
            raise ValueError(f"Invalid TTS engine: {v}. Must be 'edge' or 'elevenlabs'")
        return v.lower()

    @validator("ASSETS_DIR", "BACKGROUNDS_DIR", pre=True)
    def resolve_relative_to_base_dir(cls, v: Any, values: Dict[str, Any]) -> Any:
        if isinstance(v, str): v = Path(v)
        if isinstance(v, Path) and not v.is_absolute():
            if "BASE_DIR" in values and values["BASE_DIR"]:
                v = values["BASE_DIR"] / v
            else: v = v.absolute()
        return v
    
    @validator("UPLOAD_DIR", "OUTPUT_DIR", "DATA_DIR", "CACHE_DIR", "ASSETS_DIR", "BACKGROUNDS_DIR", pre=True)
    def validate_and_create_dirs(cls, v: Path) -> Path:
        if isinstance(v, str): v = Path(v)
        if not v.is_absolute(): v = v.absolute()
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @property
    def is_elevenlabs_configured(self) -> bool: return bool(self.ELEVENLABS_API_KEY)
    
    @property
    def use_gemini_keywords(self) -> bool:
        return bool(self.GEMINI_API_KEY)
    
    def get_voice_id(self, voice_name: Optional[str] = None, engine: Optional[str] = None) -> str:
        """
        Resolves a voice ID based on name or alias.
        All voice logic is now centralized here based on Settings.
        """
        voice_name = voice_name or "default"
        voice_lower = voice_name.lower()
        
        # 1. Check Aliases first
        if voice_lower in self.VOICE_ALIASES:
            return self.VOICE_ALIASES[voice_lower]
        
        # 2. Check if it's already a full ID (Edge or ElevenLabs)
        if "neural" in voice_lower or "en-" in voice_lower: # Edge
            return voice_name
        
        if len(voice_name) == 20 and voice_name.isalnum(): # ElevenLabs ID
            return voice_name
            
        # 3. Fallback
        return self.DEFAULT_VOICE_ID

settings = Settings()
