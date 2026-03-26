"""
Audio mixer module for combining multiple audio sources.
Uses pydub for precise audio manipulation and mixing.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError
    PYDUB_AVAILABLE = True
except ImportError:
    logger.warning("pydub not available. Install with: pip install pydub")
    PYDUB_AVAILABLE = False


class AudioMixer:
    """Mix multiple audio files with precise timing control."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize audio mixer.
        
        Args:
            output_dir: Directory to save mixed audio files (defaults to temp directory)
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "mixed_audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AudioMixer initialized with output directory: {self.output_dir}")
    
    def _load_audio(self, audio_path: Path) -> Optional['AudioSegment']:
        """
        Load audio file using pydub.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            AudioSegment object or None if failed
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available")
            return None
        
        if not audio_path.exists():
            logger.error(f"Audio file does not exist: {audio_path}")
            return None
        
        try:
            audio = AudioSegment.from_file(audio_path)
            logger.debug(f"Loaded audio: {audio_path} ({len(audio)}ms, {audio.frame_rate}Hz)")
            return audio
        except CouldntDecodeError as e:
            logger.error(f"Could not decode audio file {audio_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading audio {audio_path}: {e}")
            return None
    
    def mix_title_with_pop_sfx(
        self,
        main_audio_path: Path,
        pop_sfx_path: Path,
        pop_start_time: float = 0.0,  # Start time in seconds
        pop_volume_delta: float = -6.0,  # dB adjustment for pop SFX (-6 = quieter)
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Mix title audio with pop sound effect at specified time.
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available, cannot mix audio")
            return None
        
        # Load audio files
        logger.info(f"Mixing audio: {main_audio_path} + {pop_sfx_path} at {pop_start_time:.2f}s")
        
        main_audio = self._load_audio(main_audio_path)
        pop_sfx = self._load_audio(pop_sfx_path)
        
        if main_audio is None or pop_sfx is None:
            logger.error("Failed to load audio files")
            return None
        
        try:
            # Adjust pop SFX volume
            if pop_volume_delta != 0:
                pop_sfx = pop_sfx.apply_gain(pop_volume_delta)
                logger.debug(f"Adjusted pop SFX volume by {pop_volume_delta}dB")
            
            # Convert start time to milliseconds
            pop_start_ms = int(pop_start_time * 1000)
            
            # Ensure pop SFX doesn't exceed main audio duration
            if pop_start_ms + len(pop_sfx) > len(main_audio):
                logger.warning(f"Pop SFX exceeds main audio duration, trimming")
                pop_sfx = pop_sfx[:len(main_audio) - pop_start_ms]
            
            # Create a silent audio segment for the pop SFX
            pop_track = AudioSegment.silent(duration=len(main_audio))
            
            # Overlay pop SFX at specified start time
            pop_track = pop_track.overlay(pop_sfx, position=pop_start_ms)
            
            # Mix with main audio
            mixed_audio = main_audio.overlay(pop_track)
            
            # Generate output path if not provided
            if output_path is None:
                import hashlib
                import time
                content_hash = hashlib.md5(
                    f"{main_audio_path}{pop_sfx_path}{pop_start_time}".encode()
                ).hexdigest()[:8]
                timestamp = int(time.time())
                filename = f"mixed_audio_{content_hash}_{timestamp}.wav"
                output_path = self.output_dir / filename
            
            # Export mixed audio
            try:
                mixed_audio.export(str(output_path), format="wav")
            except Exception as e:
                logger.error(f"Failed to export mixed title/pop audio: {e}")
                return None
            
            # Verify file was created
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Mixed audio saved: {output_path} ({output_path.stat().st_size} bytes)")
                return output_path
            else:
                logger.error(f"Failed to save mixed audio: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error mixing audio: {e}")
            return None

    def add_background_music(
        self,
        main_audio_path: Path,
        bg_music_path: Path,
        output_path: Optional[Path] = None,
        bg_volume_delta: float = -24.0,
        start_offset_seconds: float = 17.0,
            
    ) -> Optional[Path]:
        """
        Mix main audio (narration) with looping background music.
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available, cannot mix background music")
            return None
            
        logger.info(f"Adding background music: {bg_music_path.name} starting from {start_offset_seconds}s")
        
        main_audio = self._load_audio(main_audio_path)
        bg_music = self._load_audio(bg_music_path)
        
        if main_audio is None or bg_music is None:
            logger.error("Failed to load audio files for background music")
            return None
            
        try:
            # חיתוך השקט או הפתיח מההתחלה של שיר הרקע
            if start_offset_seconds > 0:
                start_ms = int(start_offset_seconds * 1000)
                if start_ms < len(bg_music):
                    bg_music = bg_music[start_ms:]
                else:
                    logger.warning("Start offset is longer than the music itself!")

            # מנמיכים את הווליום
            bg_music = bg_music.apply_gain(bg_volume_delta)
            
            # משכפלים את המוזיקה (Loop) כדי שתספיק לכל אורך הקריינות
            loops_needed = (len(main_audio) // len(bg_music)) + 1
            bg_music_looped = bg_music * loops_needed
            
            # חותכים בדיוק לאורך של הקריינות
            bg_music_trimmed = bg_music_looped[:len(main_audio)]
            
            # מערבבים את הערוצים
            mixed_audio = main_audio.overlay(bg_music_trimmed)
            
            if output_path is None:
                import time, hashlib
                content_hash = hashlib.md5(f"{main_audio_path}{bg_music_path}".encode()).hexdigest()[:8]
                output_path = self.output_dir / f"with_bgm_{content_hash}_{int(time.time())}.wav"
                
            try:
                mixed_audio.export(str(output_path), format="wav")
                return output_path
            except Exception as e:
                logger.error(f"Failed to export audio with background music: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error mixing background music: {e}")
            return None
        
    def fade_audio(
        self,
        audio_path: Path,
        fade_in_duration: float = 0.1,  # seconds
        fade_out_duration: float = 0.1,  # seconds
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Apply fade-in and fade-out to audio."""
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available")
            return None
        
        audio = self._load_audio(audio_path)
        if audio is None:
            return None
        
        try:
            fade_in_ms = int(fade_in_duration * 1000)
            fade_out_ms = int(fade_out_duration * 1000)
            
            faded = audio.fade_in(fade_in_ms).fade_out(fade_out_ms)
            
            if output_path is None:
                import hashlib
                import time
                content_hash = hashlib.md5(
                    f"{audio_path}{fade_in_duration}{fade_out_duration}".encode()
                ).hexdigest()[:8]
                timestamp = int(time.time())
                filename = f"faded_audio_{content_hash}_{timestamp}.wav"
                output_path = self.output_dir / filename
            
            try:
                faded.export(str(output_path), format="wav")
            except Exception as e:
                logger.error(f"Failed to export faded audio: {e}")
                return None
            
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Faded audio saved: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to save faded audio: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error fading audio: {e}")
            return None
    
    def normalize_audio(
        self,
        audio_path: Path,
        target_db: float = -20.0,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Normalize audio loudness to target dB level."""
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available")
            return None
        
        audio = self._load_audio(audio_path)
        if audio is None:
            return None
        
        try:
            current_db = audio.dBFS
            gain_db = target_db - current_db
            
            normalized = audio.apply_gain(gain_db)
            
            if output_path is None:
                import hashlib
                import time
                content_hash = hashlib.md5(f"{audio_path}{target_db}".encode()).hexdigest()[:8]
                timestamp = int(time.time())
                filename = f"normalized_audio_{content_hash}_{timestamp}.wav"
                output_path = self.output_dir / filename
            
            try:
                normalized.export(str(output_path), format="wav")
            except Exception as e:
                logger.error(f"Failed to export normalized audio: {e}")
                return None
            
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Normalized audio saved: {output_path} (adjusted by {gain_db:.1f}dB)")
                return output_path
            else:
                logger.error(f"Failed to save normalized audio: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            return None
    
    def concat_audio_files(
        self,
        audio_paths: List[Path],
        crossfade_duration: float = 0.0,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Concatenate multiple audio files."""
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available")
            return None
        
        if not audio_paths:
            logger.error("No audio files to concatenate")
            return None
        
        try:
            segments = []
            for path in audio_paths:
                if not path.exists():
                    logger.warning(f"Audio file does not exist, skipping: {path}")
                    continue
                
                segment = self._load_audio(path)
                if segment is not None:
                    segments.append(segment)
                else:
                    logger.warning(f"Failed to load segment: {path}")
            
            if not segments:
                logger.error("No valid audio segments loaded")
                return None
            
            crossfade_ms = int(crossfade_duration * 1000)
            
            if crossfade_ms > 0 and len(segments) > 1:
                concatenated = segments[0]
                for i, segment in enumerate(segments[1:], 1):
                    if len(concatenated) >= crossfade_ms and len(segment) >= crossfade_ms:
                        concatenated = concatenated.append(segment, crossfade=crossfade_ms)
                    else:
                        concatenated = concatenated.append(segment)
            else:
                concatenated = segments[0]
                for segment in segments[1:]:
                    concatenated = concatenated.append(segment)
            
            if output_path is None:
                import hashlib
                import time
                path_str = "".join(str(p) for p in audio_paths)
                content_hash = hashlib.md5(path_str.encode()).hexdigest()[:8]
                timestamp = int(time.time())
                filename = f"concatenated_audio_{content_hash}_{timestamp}.wav"
                output_path = self.output_dir / filename
            
            try:
                concatenated.export(str(output_path), format="wav")
            except Exception as e:
                logger.error(f"Failed to export concatenated audio: {e}")
                return None
            
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"Concatenated audio saved: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to save concatenated audio: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error concatenating audio: {e}")
            return None
    
    async def mix_title_with_pop_sfx_async(
        self,
        main_audio_path: Path,
        pop_sfx_path: Path,
        pop_start_time: float = 0.0,
        pop_volume_delta: float = -6.0,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Async wrapper for mix_title_with_pop_sfx."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.mix_title_with_pop_sfx(
                main_audio_path, pop_sfx_path, pop_start_time, pop_volume_delta, output_path
            )
        )


def create_title_audio_with_pop(
    title_audio_path: Path,
    pop_sfx_path: Path,
    output_dir: Optional[Path] = None,
    pop_volume: float = -6.0,
) -> Optional[Path]:
    mixer = AudioMixer(output_dir=output_dir)
    return mixer.mix_title_with_pop_sfx(
        main_audio_path=title_audio_path,
        pop_sfx_path=pop_sfx_path,
        pop_start_time=0.0,
        pop_volume_delta=pop_volume,
    )