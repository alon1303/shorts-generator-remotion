"""
Video Composer for Reddit Stories Shorts.
Combines audio narration with background videos and adds Shorts-style subtitles.
"""

import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import uuid

from config.settings import settings
from .background_manager import BackgroundManager
from .models import AudioChunk, WordTimestamp
from .subtitle_generator import SubtitleGenerator
from .audio_utils import adjust_word_timestamps, detect_silence_at_beginning
from .image_generator_new import TitlePopupTimingCalculator
from .audio_mixer import AudioMixer
from .remotion_composer import RemotionComposer

# Configure logging
logger = logging.getLogger(__name__)

class VideoComposer:
    """Composes Shorts videos by combining audio, background, and subtitles."""
    
    def __init__(self, background_manager: Optional[BackgroundManager] = None):
        self.background_manager = background_manager or BackgroundManager()
        self.audio_mixer = AudioMixer()
        self.remotion_composer = RemotionComposer()
        logger.info(f"VideoComposer initialized with engine: {settings.VIDEO_ENGINE}")
    
    def _validate_background_fps(self, background_path: Path) -> bool:
        try:
            metadata = self.background_manager.get_video_metadata(background_path)
            background_fps = metadata.get('fps', 0)
            target_fps = settings.TARGET_FPS
            if background_fps <= 0:
                return False
            tolerance = 0.5
            fps_match = abs(background_fps - target_fps) <= tolerance
            return fps_match
        except Exception as e:
            logger.error(f"Failed to validate background FPS: {e}")
            return False
    
    def create_subtitles_for_text(
        self,
        text: str,
        audio_duration: float,
        output_path: Path,
        word_timestamps: Optional[List[WordTimestamp]] = None,
        audio_path: Optional[Path] = None,
        title_offset: float = 0.0,
        title_word_count: int = 0,
        is_first_part: bool = False,
        timing_data: Optional[Dict[str, Any]] = None,
        custom_keywords: Optional[List[str]] = None,
        timing_map: Optional[List[Dict[str, float]]] = None
    ) -> bool:
        generator = SubtitleGenerator(
            video_width=1080,
            video_height=1920,
            max_words_per_phrase=5,
            min_words_per_phrase=2,
            max_phrase_duration=3.0,
            min_gap_between_phrases=0.1
        )
        
        adjusted_word_timestamps = word_timestamps
        if audio_path and audio_path.exists() and word_timestamps:
            silence_offset = detect_silence_at_beginning(audio_path)
            if silence_offset > 0.05:
                adjusted_word_timestamps = adjust_word_timestamps(word_timestamps, -silence_offset)
        
        if adjusted_word_timestamps:
            if title_word_count > 0:
                min_start_time = 0.0
                if timing_data and 'card_end_time' in timing_data:
                    min_start_time = float(timing_data['card_end_time'])
                
                success, _ = generator.generate_ass_with_title_filter(
                    word_timestamps=adjusted_word_timestamps,
                    title_word_count=title_word_count,
                    audio_duration=audio_duration,
                    output_path=output_path,
                    min_start_time=min_start_time,
                    custom_keywords=custom_keywords,
                    timing_map=timing_map
                )
                return success
            else:
                if title_offset > 0 and adjusted_word_timestamps:
                    adjusted_word_timestamps = adjust_word_timestamps(adjusted_word_timestamps, title_offset)
                
                success = generator.generate_ass_with_pysubs2(
                    word_timestamps=adjusted_word_timestamps,
                    audio_duration=audio_duration + title_offset,
                    output_path=output_path,
                    min_start_time=0.0,
                    custom_keywords=custom_keywords,
                    timing_map=timing_map
                )
                return success
        else:
            return generator.generate_ass_from_text(
                text=text,
                audio_duration=audio_duration + title_offset,
                output_path=output_path,
                timing_map=timing_map
            )
    
    def combine_audio_with_background(
        self,
        audio_path: Path,
        background_path: Path,
        output_path: Path,
        subtitle_path: Optional[Path] = None,
        overlay_image_path: Optional[Path] = None,
        pop_sfx_path: Optional[Path] = None,
        bg_music_path: Optional[Path] = None,
        timing_data: Optional[Dict[str, Any]] = None,
        hook_duration: Optional[float] = None
    ) -> bool:
        try:
            audio_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)]
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, encoding='utf-8')
            audio_duration = float(audio_result.stdout.strip()) if audio_result.stdout else 0
            if audio_duration <= 0: return False
            
            temp_dir = Path(tempfile.mkdtemp())
            shutil.copy2(audio_path, temp_dir / audio_path.name)
            shutil.copy2(background_path, temp_dir / background_path.name)
            
            overlay_name = None
            if overlay_image_path and overlay_image_path.exists():
                shutil.copy2(overlay_image_path, temp_dir / overlay_image_path.name)
                overlay_name = overlay_image_path.name
                
            subtitle_name = None
            if subtitle_path and subtitle_path.exists():
                shutil.copy2(subtitle_path, temp_dir / subtitle_path.name)
                subtitle_name = subtitle_path.name

            cur_audio = audio_path.name
            if pop_sfx_path and pop_sfx_path.exists():
                shutil.copy2(pop_sfx_path, temp_dir / pop_sfx_path.name)
                mixed = self.audio_mixer.mix_title_with_pop_sfx(temp_dir / audio_path.name, temp_dir / pop_sfx_path.name, output_path=temp_dir / "mixed.wav")
                if mixed: cur_audio = "mixed.wav"

            cmd = ['ffmpeg', '-y', '-i', background_path.name]
            if overlay_name: cmd.extend(['-loop', '1', '-framerate', '30', '-i', overlay_name])
            cmd.extend(['-i', cur_audio])
            
            filter_complex = ""
            if overlay_name:
                if timing_data and 'card_start_time' in timing_data:
                    calc = TitlePopupTimingCalculator(timing_data['title_audio_duration'], timing_data['buffer_seconds'])
                    filter_complex = calc.get_ffmpeg_filter_for_animation(Path(overlay_name))
                else:
                    filter_complex = f'[1:v]scale=950:-1[ov];[0:v][ov]overlay=(W-w)/2:(H-h)/3:enable=\'between(t,0,4)\''
            
            if subtitle_name:
                if filter_complex: filter_complex += f',subtitles={subtitle_name}[vout]'
                else: filter_complex = f'subtitles={subtitle_name}[vout]'
            
            if filter_complex:
                cmd.extend(['-filter_complex', filter_complex, '-map', '[vout]', '-map', f'{"2" if overlay_name else "1"}:a'])
            else:
                cmd.extend(['-map', '0:v', '-map', '1:a'])
                
            cmd.extend(['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-c:a', 'aac', '-t', str(audio_duration), output_path.name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"FFmpeg combine failed: {result.stderr}")
                return False

            if (temp_dir / output_path.name).exists():
                shutil.copy2(temp_dir / output_path.name, output_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return output_path.exists()
        except Exception as e:
            logger.error(f"Combine failed: {e}")
            return False

    def create_video_part(
        self,
        audio_chunk: AudioChunk,
        theme: Optional[str] = None,
        output_path: Optional[Path] = None,
        overlay_image_path: Optional[Path] = None,
        pop_sfx_path: Optional[Path] = None,
        timing_data: Optional[Dict[str, Any]] = None,
        hook_duration: Optional[float] = None,
        bg_music_path: Optional[Path] = None,
        dynamic_switching: Optional[bool] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> Optional[Path]:
        if not audio_chunk.audio_path.exists(): return None
        if output_path is None: output_path = Path(tempfile.gettempdir()) / f"vp_{uuid.uuid4().hex}.mp4"
        
        # Remotion Engine support for parts
        if settings.VIDEO_ENGINE == "remotion":
            logger.info("Using Remotion Engine for video part composition")
            success = self.remotion_composer.render_video(
                audio_chunks=[audio_chunk],
                title=timing_data.get('title', 'Reddit Story') if timing_data else 'Reddit Story',
                author=timing_data.get('author', 'u/unknown') if timing_data else 'u/unknown',
                subreddit=timing_data.get('subreddit', 'r/reddit') if timing_data else 'r/reddit',
                title_card_duration=timing_data.get('card_end_time', 4.0) if timing_data else 4.0,
                output_path=output_path,
                background_music_path=bg_music_path
            )
            if success:
                return output_path
            else:
                logger.error("Remotion render for part failed")
                return None

        # FFmpeg path removed - Remotion only
        logger.warning("FFmpeg engine is disabled. Remotion is required.")
        return None

    def create_complete_shorts_video(
        self,
        audio_chunks: List[AudioChunk],
        theme: Optional[str] = None,
        output_path: Optional[Path] = None,
        overlay_image_path: Optional[Path] = None,
        pop_sfx_path: Optional[Path] = None,
        bg_music_path: Optional[Path] = None,
        timing_data: Optional[Dict[str, Any]] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> Path:
        if output_path is None: output_path = settings.OUTPUT_DIR / f"shorts_{uuid.uuid4().hex}.mp4"
        
        # New Remotion Engine path
        if settings.VIDEO_ENGINE == "remotion":
            logger.info("Using Remotion Engine for video composition")
            success = self.remotion_composer.render_video(
                audio_chunks=audio_chunks,
                title=timing_data.get('title', 'Reddit Story') if timing_data else 'Reddit Story',
                author=timing_data.get('author', 'u/unknown') if timing_data else 'u/unknown',
                subreddit=timing_data.get('subreddit', 'r/reddit') if timing_data else 'r/reddit',
                title_card_duration=timing_data.get('card_end_time', 4.0) if timing_data else 4.0,
                output_path=output_path,
                background_music_path=bg_music_path
            )
            if success:
                return output_path
            else:
                logger.error("Remotion render failed")
                return None

        # FFmpeg path removed - Remotion only
        logger.warning("FFmpeg engine is disabled. Remotion is required.")
        return None

def create_shorts_video(audio_chunks, theme=None, output_path=None, overlay_image_path=None, pop_sfx_path=None, bg_music_path=None, timing_data=None, custom_keywords=None):
    return VideoComposer().create_complete_shorts_video(audio_chunks, theme, output_path, overlay_image_path, pop_sfx_path, bg_music_path, timing_data, custom_keywords)
