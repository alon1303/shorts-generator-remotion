import os
import hashlib
import json
import time
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import uuid

from elevenlabs.client import ElevenLabs
from config.settings import settings
from .models import WordTimestamp, AudioChunk

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    """Async client for ElevenLabs Text-to-Speech with modern SDK support."""
    
    def __init__(
        self,
        voice: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        model: str = "eleven_multilingual_v2"
    ):
        self.api_key = settings.ELEVENLABS_API_KEY
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set in settings/env")
            
        self.client = ElevenLabs(api_key=self.api_key)
        
        # Ensure we don't use an Edge TTS voice ID (contains 'Neural' or 'en-') 
        # when initialized, as ElevenLabs will return a 400 error.
        self.voice = voice or settings.get_voice_id("adam", engine="elevenlabs")
        self.model = model
        self.cache_dir = cache_dir or settings.CACHE_DIR / "elevenlabs"
        self.voices_dir = self.cache_dir / "voices"
        
        # ElevenLabs voice settings
        self.stability = settings.ELEVENLABS_STABILITY
        self.similarity_boost = settings.ELEVENLABS_SIMILARITY_BOOST
        self.style = settings.ELEVENLABS_STYLE
        self.use_speaker_boost = settings.ELEVENLABS_USE_SPEAKER_BOOST
        self.speed = getattr(settings, "ELEVENLABS_SPEED", 1.0)
        
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ElevenLabs client initialized: voice={self.voice}, model={self.model}")

    def _generate_cache_key(self, text: str, voice: str) -> str:
        params_str = f"{text}_{voice}_{self.model}"
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()

    async def _estimate_duration(self, audio_path: Path) -> float:
        """Get accurate duration using ffprobe."""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'json', str(audio_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return float(json.loads(result.stdout)['format']['duration'])
        except Exception:
            pass
        return 0.0

    async def text_to_speech_with_timestamps(
        self,
        text: str,
        voice: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> Tuple[Optional[Path], float, Optional[List[WordTimestamp]]]:
        """
        Convert text to speech. 
        Note: Free ElevenLabs API doesn't easily provide word-level timestamps in a single call 
        like Edge-TTS. This version focuses on fixing the 'generate' error first.
        """
        # Validate voice ID - prevent Edge TTS strings from reaching ElevenLabs API
        voice_id = voice
        if voice_id and ("neural" in voice_id.lower() or "en-" in voice_id.lower()):
            logger.warning(f"Invalid voice argument for ElevenLabs: {voice_id}. Using self.voice instead.")
            voice_id = self.voice
        
        voice_id = voice_id or self.voice
        cache_key = self._generate_cache_key(text, voice_id)
        
        if use_cache:
            pattern = f"{cache_key}_*.wav"
            cached_files = list(self.voices_dir.glob(pattern))
            if cached_files:
                cached_path = sorted(cached_files)[-1]
                duration = await self._estimate_duration(cached_path)
                
                # Try to load cached timestamps
                word_timestamps = None
                json_path = cached_path.with_suffix(".json")
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding='utf-8') as f:
                            data = json.load(f)
                            word_timestamps = [WordTimestamp.from_dict(w) for w in data]
                    except Exception as e:
                        logger.warning(f"Failed to load cached timestamps: {e}")
                
                return cached_path, duration, word_timestamps

        try:
            logger.info(f"Generating ElevenLabs TTS for {len(text)} chars")
            
            # Build voice settings dynamically
            voice_settings = {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
            }

            if self.speed != 1.0:
                voice_settings["speed"] = self.speed

            # Use convert_with_timestamps to get character-level alignment
            response = self.client.text_to_speech.convert_with_timestamps(
                text=text,
                voice_id=voice_id,
                model_id=self.model,
                output_format="mp3_44100_128",
                voice_settings=voice_settings
            )
            
            # Debug: log the attributes of response
            logger.info(f"Response type: {type(response)}")
            # In latest SDK, it might be 'audio' (base64 or bytes) or it might be a generator
            # The error said 'AudioWithTimestampsResponse' object has no attribute 'audio'
            
            # The correct attribute is 'audio_base_64' (based on debug log)
            import base64
            if hasattr(response, 'audio_base_64') and response.audio_base_64:
                audio_data = base64.b64decode(response.audio_base_64)
            elif hasattr(response, 'audio') and response.audio:
                if isinstance(response.audio, bytes):
                    audio_data = response.audio
                else:
                    audio_data = b"".join(list(response.audio))
            else:
                raise AttributeError("Could not find audio data in ElevenLabs response")

            # response.alignment contains characters, character_start_times_seconds, character_end_times_seconds
            alignment = response.alignment
            
            word_timestamps = self._aggregate_characters_to_words(alignment)
            
            timestamp = int(time.time())
            file_path = self.voices_dir / f"{cache_key}_{timestamp}.wav"
            json_path = self.voices_dir / f"{cache_key}_{timestamp}.json"
            
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            # Cache word timestamps
            with open(json_path, "w", encoding='utf-8') as f:
                json.dump([w.to_dict() for w in word_timestamps], f, indent=2)

            duration = await self._estimate_duration(file_path)
            return file_path, duration, word_timestamps
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {str(e)}")
            raise

    def _aggregate_characters_to_words(self, alignment: Any) -> List[WordTimestamp]:
        """
        Aggregates character-level alignment data into word-level timestamps.
        
        Args:
            alignment: The alignment object from ElevenLabs containing:
                      - characters: List[str]
                      - character_start_times_seconds: List[float]
                      - character_end_times_seconds: List[float]
        """
        if not alignment or not alignment.characters:
            return []
            
        words = []
        current_word_chars = []
        current_word_start = None
        
        chars = alignment.characters
        starts = alignment.character_start_times_seconds
        ends = alignment.character_end_times_seconds
        
        for char, start, end in zip(chars, starts, ends):
            # Check if this character is whitespace
            if char.isspace():
                if current_word_chars:
                    # Finalize current word
                    word_text = "".join(current_word_chars)
                    words.append(WordTimestamp(
                        word=word_text,
                        start=current_word_start,
                        end=current_word_end,
                        confidence=1.0 # ElevenLabs doesn't provide confidence per character
                    ))
                    current_word_chars = []
                    current_word_start = None
                continue
            
            # If it's a non-space character
            if not current_word_chars:
                current_word_start = start
            
            current_word_chars.append(char)
            current_word_end = end
            
        # Add the last word if it exists
        if current_word_chars:
            word_text = "".join(current_word_chars)
            words.append(WordTimestamp(
                word=word_text,
                start=current_word_start,
                end=current_word_end,
                confidence=1.0
            ))
            
        return words

    async def generate_audio_chunks(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        **kwargs
    ) -> List[AudioChunk]:
        chunks = []
        for text in text_chunks:
            path, duration, word_timestamps = await self.text_to_speech_with_timestamps(text, voice, **kwargs)
            chunks.append(AudioChunk(
                chunk_id=str(uuid.uuid4())[:8],
                text=text,
                audio_path=path,
                duration_seconds=duration,
                word_timestamps=word_timestamps,
                voice_id=voice or self.voice,
                file_size_bytes=path.stat().st_size if path else 0
            ))
        return chunks

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        response = self.client.voices.get_all()
        return [{"voice_id": v.voice_id, "name": v.name} for v in response.voices]
    
    async def close(self):
        pass