"""
Microsoft Edge Text-to-Speech (edge-tts) client for generating voiceovers for Reddit stories.
Provides free TTS with word-level timestamps using Microsoft's Edge browser TTS service.
"""

import asyncio
import logging
import json
import hashlib
import time
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import uuid
import edge_tts

from config.settings import settings
from .models import WordTimestamp, AudioChunk

# Configure logging
logger = logging.getLogger(__name__)

class EdgeTTSClient:
    """Async client for Microsoft Edge Text-to-Speech (edge-tts)."""
    
    # Default voice for English (US) - Male voice for better retention
    DEFAULT_VOICE = "en-US-GuyNeural"
    
    # Available voices for different languages/accents
    AVAILABLE_VOICES = {
        "en-US-GuyNeural": "English (US) - Male",
        "en-US-JennyNeural": "English (US) - Female",
        "en-GB-SoniaNeural": "English (UK) - Female",
        "en-AU-AnnetteNeural": "English (Australia) - Female",
        "en-CA-ClaraNeural": "English (Canada) - Female",
        "en-IN-NeerjaNeural": "English (India) - Female",
        "en-IE-ConnorNeural": "English (Ireland) - Male",
        "en-NG-AbeoNeural": "English (Nigeria) - Male",
    }
    
    def __init__(
        self,
        voice: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        rate: str = "+20%",
        volume: str = "+0%",
        pitch: str = "+10Hz",
    ):
        """
        Initialize EdgeTTS client.
        
        Args:
            voice: Voice ID (defaults to DEFAULT_VOICE)
            cache_dir: Directory to cache generated audio files
            rate: Speaking rate adjustment (+/- percentage)
            volume: Volume adjustment (+/- percentage)
            pitch: Pitch adjustment (+/- Hz)
        """
        self.voice = voice or self.DEFAULT_VOICE
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        
        # Set up cache directory
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = settings.CACHE_DIR / "edgetts"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create voices subdirectory
        self.voices_dir = self.cache_dir / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"EdgeTTS client initialized: "
            f"voice={self.voice}, cache={self.cache_dir}"
        )
    
    async def close(self):
        """EdgeTTS doesn't have persistent connections to close."""
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _generate_cache_key(self, text: str, voice: str, **kwargs) -> str:
        """
        Generate a cache key for text and voice combination.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use
            **kwargs: Additional parameters that affect output
            
        Returns:
            MD5 hash string for caching
        """
        # Create a string representation of all parameters
        params_str = f"{text}_{voice}_{self.rate}_{self.volume}_{self.pitch}_{json.dumps(kwargs, sort_keys=True)}"
        
        # Generate MD5 hash
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()
    
    def _get_cached_audio_path(self, cache_key: str) -> Optional[Path]:
        """
        Check if audio is already cached.
        
        Args:
            cache_key: Cache key for the audio
            
        Returns:
            Path to cached audio file if exists, None otherwise
        """
        # Look for files with this cache key
        pattern = f"{cache_key}_*.wav"
        cached_files = list(self.voices_dir.glob(pattern))
        
        if cached_files:
            # Return the most recent file
            return sorted(cached_files, key=lambda p: p.stat().st_mtime)[-1]
        
        return None
    
    async def _save_audio_to_cache(
        self, 
        cache_key: str, 
        audio_data: bytes,
        text: str,
        voice: str,
        word_timestamps: Optional[List[WordTimestamp]] = None
    ) -> Path:
        """
        Save audio data to cache.
        
        Args:
            cache_key: Cache key for the audio
            audio_data: Raw audio bytes
            text: Original text (for metadata)
            voice: Voice ID used
            word_timestamps: Optional word timestamps
            
        Returns:
            Path to saved audio file
        """
        # Generate filename with timestamp
        timestamp = int(time.time())
        filename = f"{cache_key}_{timestamp}.wav"
        filepath = self.voices_dir / filename
        
        # Save audio file
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        # Save metadata
        metadata = {
            "cache_key": cache_key,
            "text": text,
            "voice": voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "timestamp": timestamp,
            "file_size": len(audio_data),
        }
        
        metadata_path = filepath.with_suffix('.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Save word timestamps if available
        if word_timestamps:
            timestamp_path = filepath.with_suffix('.timestamps.json')
            timestamp_data = {
                'word_timestamps': [
                    {
                        'word': ts.word,
                        'start': ts.start,
                        'end': ts.end,
                        'confidence': ts.confidence
                    }
                    for ts in word_timestamps
                ]
            }
            
            with open(timestamp_path, 'w', encoding='utf-8') as f:
                json.dump(timestamp_data, f, indent=2)
        
        logger.debug(f"Audio cached: {filepath} ({len(audio_data)} bytes)")
        
        return filepath
    
    async def _estimate_audio_duration(self, audio_path: Path) -> float:
        """
        Get accurate audio duration using ffprobe.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Accurate duration in seconds
        """
        try:
            # Use ffprobe to get accurate duration
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                logger.debug(f"Accurate audio duration from ffprobe: {duration:.3f}s")
                return duration
            else:
                logger.warning(f"ffprobe failed for {audio_path}: {result.stderr}")
                # Fallback to file size estimation
                file_size = audio_path.stat().st_size
                estimated_duration = file_size / 16000  # Rough MP3 estimation
                logger.warning(f"Using estimated duration: {estimated_duration:.3f}s (file size: {file_size} bytes)")
                return estimated_duration
                
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            # Fallback: estimate based on text length (150 words/minute)
            words = len(text.split()) if 'text' in locals() else 0
            return words / 2.5  # 150 words/minute = 2.5 words/second
    
    def _parse_word_boundary_events(self, events: List[Dict[str, Any]]) -> List[WordTimestamp]:
        """
        Parse edge-tts WordBoundary events into WordTimestamp objects.
        
        Args:
            events: List of WordBoundary events from edge-tts
            
        Returns:
            List of WordTimestamp objects
        """
        word_timestamps = []
        
        for event in events:
            if event['type'] == 'WordBoundary':
                # Convert 100-nanosecond ticks to seconds
                offset_ticks = event['offset']
                duration_ticks = event['duration']
                
                # Convert to seconds (10,000,000 ticks per second)
                start_seconds = offset_ticks / 10000000.0
                end_seconds = (offset_ticks + duration_ticks) / 10000000.0
                
                word = event['text'].strip()
                
                # Skip empty words (can happen with punctuation)
                if not word:
                    continue
                
                # Create WordTimestamp with default confidence of 1.0
                word_ts = WordTimestamp(
                    word=word,
                    start=start_seconds,
                    end=end_seconds,
                    confidence=1.0
                )
                
                word_timestamps.append(word_ts)
                logger.debug(f"Parsed word: '{word}' at {start_seconds:.3f}s - {end_seconds:.3f}s")
        
        return word_timestamps
    
    async def text_to_speech_with_timestamps(
        self,
        text: str,
        voice: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> Tuple[Optional[Path], float, Optional[List[WordTimestamp]]]:
        """
        Convert text to speech using edge-tts with word-level timestamps.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use (defaults to self.voice)
            use_cache: Whether to use cached audio if available
            
        Returns:
            Tuple of (audio_file_path, duration_seconds, word_timestamps)
            Raises exception on error (fail-fast)
        """
        voice = voice or self.voice
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            text, 
            voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
            boundary='WordBoundary'  # Always use WordBoundary for timestamps
        )
        
        # Check cache first
        if use_cache:
            cached_path = self._get_cached_audio_path(cache_key)
            if cached_path:
                # Check if we have timestamp metadata
                timestamp_path = cached_path.with_suffix('.timestamps.json')
                if timestamp_path.exists():
                    try:
                        with open(timestamp_path, 'r', encoding='utf-8') as f:
                            timestamp_data = json.load(f)
                        
                        # Parse word timestamps
                        word_timestamps = []
                        for ts in timestamp_data.get('word_timestamps', []):
                            word_timestamps.append(WordTimestamp(
                                word=ts['word'],
                                start=ts['start'],
                                end=ts['end'],
                                confidence=ts.get('confidence', 1.0)
                            ))
                        
                        duration = await self._estimate_audio_duration(cached_path)
                        logger.debug(f"Using cached audio with timestamps: {cached_path} ({duration:.1f}s, {len(word_timestamps)} words)")
                        return cached_path, duration, word_timestamps
                    except Exception as e:
                        logger.warning(f"Failed to load cached timestamps: {e}")
                
                # If we have audio but no timestamps, we still return the audio
                duration = await self._estimate_audio_duration(cached_path)
                logger.debug(f"Using cached audio (no timestamps): {cached_path} ({duration:.1f}s)")
                return cached_path, duration, None
        
        try:
            # Create Communicate instance with WordBoundary for timestamps
            communicate = edge_tts.Communicate(
                text, 
                voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
                boundary='WordBoundary'  # CRITICAL: enables word-level timestamps
            )
            
            logger.info(f"Generating TTS with timestamps for {len(text)} characters with voice {voice}")
            
            # Collect audio data and word events
            audio_chunks = []
            word_events = []
            
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_chunks.append(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    word_events.append(chunk)
                # Ignore other event types (SentenceBoundary, Viseme)
            
            if not audio_chunks:
                raise RuntimeError("No audio data received from edge-tts")
            
            # Combine audio chunks
            audio_data = b''.join(audio_chunks)
            
            # Parse word timestamps
            word_timestamps = self._parse_word_boundary_events(word_events)
            
            if not word_timestamps:
                logger.warning(f"No word timestamps extracted from edge-tts for text: '{text[:50]}...'")
                # Don't fail - we can still return audio without timestamps
            
            # Save to cache
            audio_path = await self._save_audio_to_cache(
                cache_key, audio_data, text, voice, word_timestamps
            )
            
            # Estimate duration
            duration = await self._estimate_audio_duration(audio_path)
            
            logger.info(f"TTS with timestamps generated: {audio_path} ({duration:.1f}s, {len(word_timestamps)} words)")
            return audio_path, duration, word_timestamps
            
        except Exception as e:
            logger.error(f"EdgeTTS generation failed: {e}")
            raise  # Fail-fast: re-raise exception
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        use_cache: bool = True,
    ) -> Tuple[Optional[Path], float]:
        """
        Convert text to speech using edge-tts (without timestamps).
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use (defaults to self.voice)
            use_cache: Whether to use cached audio if available
            
        Returns:
            Tuple of (audio_file_path, duration_seconds)
            Raises exception on error (fail-fast)
        """
        # Use the with-timestamps method but ignore timestamps for backward compatibility
        audio_path, duration, _ = await self.text_to_speech_with_timestamps(
            text=text,
            voice=voice,
            use_cache=use_cache,
        )
        return audio_path, duration
    
    async def generate_audio_chunks(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        with_timestamps: bool = True,
        **kwargs,
    ) -> List[AudioChunk]:
        """
        Generate audio for multiple text chunks.
        
        Args:
            text_chunks: List of text chunks to convert
            voice: Voice ID to use
            with_timestamps: Whether to request word-level timestamps
            **kwargs: Additional arguments for text_to_speech
            
        Returns:
            List of AudioChunk objects
        """
        voice = voice or self.voice
        
        logger.info(f"Generating audio for {len(text_chunks)} chunks with voice {voice} (timestamps: {with_timestamps})")
        
        audio_chunks = []
        
        for i, text in enumerate(text_chunks, 1):
            chunk_id = str(uuid.uuid4())[:8]
            
            logger.debug(f"Processing chunk {i}/{len(text_chunks)}: {len(text)} chars")
            
            # Generate audio with or without timestamps
            if with_timestamps:
                audio_path, duration, word_timestamps = await self.text_to_speech_with_timestamps(
                    text, 
                    voice=voice,
                    **kwargs,
                )
            else:
                audio_path, duration = await self.text_to_speech(
                    text, 
                    voice=voice,
                    **kwargs,
                )
                word_timestamps = None
            
            if audio_path:
                # Get file size
                file_size = audio_path.stat().st_size
                
                # Create AudioChunk object
                chunk = AudioChunk(
                    chunk_id=chunk_id,
                    text=text,
                    audio_path=audio_path,
                    duration_seconds=duration,
                    voice_id=voice,
                    file_size_bytes=file_size,
                    word_timestamps=word_timestamps,
                )
                
                audio_chunks.append(chunk)
                if word_timestamps:
                    logger.info(f"Chunk {i} generated: {duration:.1f}s, {file_size} bytes, {len(word_timestamps)} word timestamps")
                else:
                    logger.info(f"Chunk {i} generated: {duration:.1f}s, {file_size} bytes")
            else:
                logger.error(f"Failed to generate audio for chunk {i}")
                # Create a placeholder chunk to maintain order
                chunk = AudioChunk(
                    chunk_id=chunk_id,
                    text=text,
                    audio_path=Path(""),
                    duration_seconds=0.0,
                    voice_id=voice,
                    file_size_bytes=0,
                    word_timestamps=None,
                )
                audio_chunks.append(chunk)
        
        # Log summary
        successful = sum(1 for c in audio_chunks if c.duration_seconds > 0)
        total_duration = sum(c.duration_seconds for c in audio_chunks)
        chunks_with_timestamps = sum(1 for c in audio_chunks if c.word_timestamps)
        
        logger.info(
            f"Audio generation complete: {successful}/{len(text_chunks)} successful, "
            f"total duration: {total_duration:.1f}s, "
            f"{chunks_with_timestamps} chunks with word timestamps"
        )
        
        return audio_chunks
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices from edge-tts.
        
        Returns:
            List of voice information dictionaries
        """
        voices = []
        for voice_id, description in self.AVAILABLE_VOICES.items():
            voices.append({
                "voice_id": voice_id,
                "name": description,
                "category": "neural",
                "description": f"Microsoft Edge TTS - {description}",
            })
        
        return voices
    
    def cleanup_old_cache(self, max_age_hours: int = 24) -> int:
        """
        Clean up old cache files.
        
        Args:
            max_age_hours: Maximum age of cache files in hours
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filepath in self.voices_dir.glob("*.wav"):
            try:
                file_age = current_time - filepath.stat().st_mtime
                
                if file_age > max_age_seconds:
                    # Delete audio file
                    filepath.unlink()
                    
                    # Delete metadata file if exists
                    metadata_path = filepath.with_suffix('.json')
                    if metadata_path.exists():
                        metadata_path.unlink()
                    
                    # Delete timestamp file if exists
                    timestamp_path = filepath.with_suffix('.timestamps.json')
                    if timestamp_path.exists():
                        timestamp_path.unlink()
                    
                    deleted_count += 1
                    logger.debug(f"Deleted old cache file: {filepath}")
                    
            except Exception as e:
                logger.warning(f"Failed to delete cache file {filepath}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old cache files")
        
        return deleted_count


# Utility functions for direct use
async def generate_story_audio_edge(
    text_chunks: List[str],
    voice: Optional[str] = None,
    with_timestamps: bool = True,
    **kwargs,
) -> List[AudioChunk]:
    """
    Convenience function to generate audio for story chunks using edge-tts.
    
    Args:
        text_chunks: List of text chunks to convert
        voice: Voice ID to use
        with_timestamps: Whether to request word-level timestamps
        **kwargs: Additional arguments for EdgeTTSClient
        
    Returns:
        List of AudioChunk objects
    """
    async with EdgeTTSClient(**kwargs) as client:
        return await client.generate_audio_chunks(text_chunks, voice, with_timestamps=with_timestamps)


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        # Create client
        async with EdgeTTSClient() as client:
            # Test text chunks
            test_chunks = [
                "Hello, this is a test of the Edge text-to-speech system.",
                "This is the second chunk of text for testing purposes.",
                "And this is the third and final test chunk."
            ]
            
            print(f"Generating audio for {len(test_chunks)} test chunks...")
            
            # Generate audio
            audio_chunks = await client.generate_audio_chunks(test_chunks)
            
            print(f"\nGenerated {len(audio_chunks)} audio chunks:")
            for i, chunk in enumerate(audio_chunks, 1):
                print(f"\nChunk {i}:")
                print(f"  Duration: {chunk.duration_seconds:.1f}s")
                print(f"  File size: {chunk.file_size_bytes} bytes")
                print(f"  Voice: {chunk.voice_id}")
                print(f"  Path: {chunk.audio_path}")
                if chunk.word_timestamps:
                    print(f"  Word timestamps: {len(chunk.word_timestamps)} words")
                    for j, ts in enumerate(chunk.word_timestamps[:3]):
                        print(f"    Word {j+1}: '{ts.word}' at {ts.start:.3f}s - {ts.end:.3f}s")
            
            # Test cache functionality
            print(f"\nTesting cache...")
            cached_path, duration = await client.text_to_speech(
                test_chunks[0],
                use_cache=True
            )
            
            if cached_path:
                print(f"Retrieved from cache: {cached_path} ({duration:.1f}s)")
            
            # Get available voices
            voices = await client.get_available_voices()
            print(f"\nAvailable voices: {len(voices)}")
            for voice in voices[:3]:
                print(f"  - {voice['voice_id']}: {voice['name']}")
            
            # Clean up old cache (optional)
            deleted = client.cleanup_old_cache(max_age_hours=1)
            print(f"Cleaned up {deleted} old cache files")
    
    # Run example
    asyncio.run(example())