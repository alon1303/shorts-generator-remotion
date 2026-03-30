"""
TTS Router/Factory for Edge TTS and ElevenLabs engines.
Routes requests to the appropriate TTS client.
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from config.settings import settings
from .models import WordTimestamp, AudioChunk
from .edgetts_client import EdgeTTSClient
from .elevenlabs_client import ElevenLabsClient
import tempfile
import shutil
import asyncio
import uuid

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class TTSConfig:
    """Configuration for TTS engine selection."""
    engine: str  # "edge" or "elevenlabs"
    voice_id: Optional[str] = None
    cache_dir: Optional[Path] = None
    use_cache: bool = True
    
    @classmethod
    def from_settings(cls, engine: Optional[str] = None, voice_id: Optional[str] = None, cache_dir: Optional[Path] = None):
        """Create TTSConfig from application settings."""
        return cls(
            engine=engine or settings.TTS_ENGINE.lower(),
            voice_id=voice_id or settings.get_voice_id(),
            cache_dir=cache_dir,
            use_cache=settings.ENABLE_CACHE
        )


class TTSRouter:
    """
    Router that selects the appropriate TTS client based on configuration.
    """
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig.from_settings()
        self._client = None
        logger.info(f"TTSRouter initialized with engine: {self.config.engine}")
    
    async def _get_client(self):
        """Get or create the appropriate TTS client."""
        if self._client is None:
            if self.config.engine == "edge":
                self._client = EdgeTTSClient(
                    voice=self.config.voice_id,
                    cache_dir=self.config.cache_dir
                )
            elif self.config.engine == "elevenlabs":
                # Ensure the voice ID is valid for ElevenLabs (not an Edge TTS ID)
                voice_id = self.config.voice_id
                if voice_id and ("neural" in voice_id.lower() or "en-" in voice_id.lower()):
                    logger.warning(f"Overriding Edge TTS voice '{voice_id}' with ElevenLabs default for ElevenLabs engine")
                    voice_id = settings.get_voice_id("adam", engine="elevenlabs")
                
                self._client = ElevenLabsClient(
                    voice=voice_id,
                    cache_dir=self.config.cache_dir
                )
            else:
                raise ValueError(f"Unknown TTS engine: {self.config.engine}. Use 'edge' or 'elevenlabs'")
        
        return self._client
    
    async def text_to_speech_with_timestamps(
        self,
        text: str,
        voice: Optional[str] = None,
        gender: Optional[str] = None,
        **kwargs,
    ) -> Tuple[Optional[Path], float, Optional[List[WordTimestamp]]]:
        client = await self._get_client()
        
        # Determine voice based on gender if provided and using ElevenLabs
        if self.config.engine == "elevenlabs" and gender:
            if gender.upper() == "F":
                voice = "yj30vwTGJxSHezdAGsv9"
                logger.info(f"Using ElevenLabs female voice: {voice}")
            else:
                voice = voice or self.config.voice_id
                logger.info(f"Using ElevenLabs male/default voice: {voice}")
        else:
            voice = voice or self.config.voice_id
            
        logger.info(f"TTSRouter: engine={self.config.engine}, requested_voice={voice}, gender={gender}")
        
        # Sanitize voice for ElevenLabs engine to prevent 400 errors
        if self.config.engine == "elevenlabs" and voice:
            if "neural" in voice.lower() or "en-" in voice.lower():
                logger.warning(f"TTSRouter: Sanitizing Edge voice '{voice}' for ElevenLabs engine")
                voice = None # Force client to use its own sanitized default
        
        logger.debug(f"Routing TTS request to {self.config.engine} engine")
        
        # Remove 'use_cache' from kwargs if present
        kwargs_without_use_cache = {k: v for k, v in kwargs.items() if k != 'use_cache'}
        
        return await client.text_to_speech_with_timestamps(
            text=text,
            voice=voice,
            use_cache=self.config.use_cache,
            **kwargs_without_use_cache,
        )
    
    async def text_to_speech(self, text: str, voice: Optional[str] = None, **kwargs) -> Tuple[Optional[Path], float]:
        client = await self._get_client()
        voice = voice or self.config.voice_id
        return await client.text_to_speech(text=text, voice=voice, use_cache=self.config.use_cache, **kwargs)
    
    async def generate_audio_chunks(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        gender: Optional[str] = None,
        with_timestamps: bool = True,
        **kwargs,
    ) -> List[AudioChunk]:
        client = await self._get_client()
        
        if self.config.engine == "elevenlabs" and gender:
            if gender.upper() == "F":
                voice = "yj30vwTGJxSHezdAGsv9"
            else:
                voice = voice or self.config.voice_id
        else:
            voice = voice or self.config.voice_id
            
        return await client.generate_audio_chunks(text_chunks=text_chunks, voice=voice, with_timestamps=with_timestamps, **kwargs)
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        return await client.get_available_voices()
    
    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def get_tts_client(engine: Optional[str] = None, voice: Optional[str] = None, **kwargs) -> TTSRouter:
    config = TTSConfig.from_settings(engine=engine, voice_id=voice)
    return TTSRouter(config)

async def generate_title_and_story_audio(
    title: str,
    story_text_chunks: List[str],
    voice: Optional[str] = None,
    gender: Optional[str] = None,
    engine: Optional[str] = None,
    buffer_seconds: float = 0.5,
    **kwargs,
) -> Tuple[Path, List[AudioChunk], float, Dict[str, Any]]:
    
    async with await get_tts_client(engine=engine, voice=voice) as router:
        # Generate title audio
        title_audio_path, title_duration, title_timestamps = await router.text_to_speech_with_timestamps(
            text=title, voice=voice, gender=gender, **kwargs
        )
        
        # Generate story audio chunks
        story_audio_chunks = await router.generate_audio_chunks(
            text_chunks=story_text_chunks, voice=voice, gender=gender, with_timestamps=True, **kwargs
        )
        
        if not story_audio_chunks:
            raise ValueError("No story audio chunks were generated")

        actual_buffer = max(0.5, float(buffer_seconds))
        pop_out_duration = 0.8
        
        # Card end time is exactly when the card begins its exit animation
        card_end_time = title_duration + actual_buffer
        
        # The total gap is the buffer + the time it takes the card to disappear
        total_gap = actual_buffer + pop_out_duration
        
        # The time the story subtitles and audio should actually start
        story_start_time = title_duration + total_gap
        
        first_chunk = story_audio_chunks[0]
        first_chunk.is_first_part = True
        first_chunk.title_word_count = len(title_timestamps) if title_timestamps else 0

        # Offset story word timestamps by title duration + total_gap (story_start_time)
        # Note: We just update the objects in memory. Remotion will use these directly.
        for chunk in story_audio_chunks:
            if chunk.word_timestamps:
                for ts in chunk.word_timestamps:
                    ts.start += story_start_time
                    ts.end += story_start_time

        # Timing data for video composition
        timing_data = {
            "title_audio_duration": title_duration,
            "buffer_seconds": actual_buffer,
            "title_word_count": first_chunk.title_word_count,
            "subtitle_start_time": story_start_time,
            "pop_in_duration": 0.6,
            "pop_out_duration": pop_out_duration,
            "card_start_time": 0.0,
            "card_end_time": card_end_time
        }
        
        return title_audio_path, story_audio_chunks, story_start_time, timing_data
