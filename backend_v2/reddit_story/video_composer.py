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

# Configure logging
logger = logging.getLogger(__name__)

class VideoComposer:
    """Composes Shorts videos by combining audio, background, and subtitles."""
    
    def __init__(self, background_manager: Optional[BackgroundManager] = None):
        self.background_manager = background_manager or BackgroundManager()
        self.audio_mixer = AudioMixer()
        logger.info("VideoComposer initialized")
    
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
        
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            bg = self.background_manager.create_sequential_background_clip(audio_chunk.duration_seconds, theme, tp / "bg.mp4")
            if not bg: return None
            sub_path = tp / "subs.ass"
            self.create_subtitles_for_text(
                audio_chunk.text, 
                audio_chunk.duration_seconds, 
                sub_path, 
                audio_chunk.word_timestamps, 
                audio_chunk.audio_path, 
                timing_data=timing_data, 
                custom_keywords=custom_keywords, 
                title_word_count=timing_data.get('title_word_count', 0) if timing_data else 0,
                timing_map=audio_chunk.timing_map
            )
            if not self.combine_audio_with_background(audio_chunk.audio_path, bg, output_path, sub_path, overlay_image_path, pop_sfx_path=pop_sfx_path, bg_music_path=bg_music_path, timing_data=timing_data):
                return None
        
        # Apply final video speed if needed
        final_speed = getattr(settings, 'FINAL_VIDEO_SPEED', 1.0)
        if final_speed != 1.0:
            logger.info(f"Applying final video speed: {final_speed}x to part")
            temp_speed_path = output_path.with_name(f"temp_speed_{uuid.uuid4().hex}.mp4")
            shutil.copy2(output_path, temp_speed_path)
            
            video_pts = 1.0 / final_speed
            audio_tempo = final_speed
            cmd = [
                'ffmpeg', '-y', 
                '-i', str(temp_speed_path), 
                '-filter_complex', f'[0:v]setpts={video_pts}*PTS[v];[0:a]atempo={audio_tempo}[a]', 
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-c:a', 'aac',
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"Failed to apply final video speed to part: {result.stderr}")
                shutil.copy2(temp_speed_path, output_path)
            
            if temp_speed_path.exists():
                temp_speed_path.unlink()
                
        return output_path

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
        vps = []
        for i, chunk in enumerate(audio_chunks, 1):
            vp = self.create_video_part(chunk, theme, overlay_image_path=overlay_image_path if i==1 else None, pop_sfx_path=pop_sfx_path if i==1 else None, bg_music_path=bg_music_path, timing_data=timing_data if i==1 else None, custom_keywords=custom_keywords)
            if vp: vps.append(vp)
        
        final_speed = getattr(settings, 'FINAL_VIDEO_SPEED', 1.0)
        
        # Determine intermediate path if we need to apply speed
        temp_combined_path = output_path
        if final_speed != 1.0:
            temp_combined_path = output_path.with_name(f"temp_combined_{uuid.uuid4().hex}.mp4")
            
        if len(vps) == 1: 
            shutil.copy2(vps[0], temp_combined_path)
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for p in vps: f.write(f"file '{str(p).replace('\\','/')}'\n")
                fl = Path(f.name)
            subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(fl), '-c', 'copy', str(temp_combined_path)], capture_output=True, text=True, encoding='utf-8')
            fl.unlink()
            
        # Apply final video speed
        if final_speed != 1.0:
            logger.info(f"Applying final video speed: {final_speed}x")
            video_pts = 1.0 / final_speed
            audio_tempo = final_speed
            cmd = [
                'ffmpeg', '-y', 
                '-i', str(temp_combined_path), 
                '-filter_complex', f'[0:v]setpts={video_pts}*PTS[v];[0:a]atempo={audio_tempo}[a]', 
                '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-c:a', 'aac',
                str(output_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"Failed to apply final video speed: {result.stderr}")
                # Fallback
                shutil.copy2(temp_combined_path, output_path)
            
            # Cleanup temp combined
            if temp_combined_path.exists():
                temp_combined_path.unlink()
                
        return output_path

def create_shorts_video(audio_chunks, theme=None, output_path=None, overlay_image_path=None, pop_sfx_path=None, bg_music_path=None, timing_data=None, custom_keywords=None):
    return VideoComposer().create_complete_shorts_video(audio_chunks, theme, output_path, overlay_image_path, pop_sfx_path, bg_music_path, timing_data, custom_keywords)
