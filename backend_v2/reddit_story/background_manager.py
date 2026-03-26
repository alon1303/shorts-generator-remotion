"""
Background Video Manager for Reddit Stories Shorts.
Manages background video selection, cropping, and duration matching.
"""

import random
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import subprocess
import json
import uuid
from collections import deque
import time

from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)


class BackgroundManager:
    """Manages background videos for Reddit Stories Shorts."""

    def __init__(self, backgrounds_dir: Optional[Path] = None):
        # Ensure we use absolute path to avoid confusion between project root and backend_v2 directories
        self.backgrounds_dir = (backgrounds_dir or settings.BACKGROUNDS_DIR).absolute()
        self.backgrounds_dir.mkdir(parents=True, exist_ok=True)
        self._video_cache: Dict[Path, Dict[str, Any]] = {}
        
        # Master playlist for dynamic background sequencing
        self._master_playlist: List[Path] = []
        self._playlist_index: int = 0
        self._playlist_initialized: bool = False
        self._recent_videos: deque = deque(maxlen=5)  # Track last 5 videos to avoid repetition
        
        logger.info(f"BackgroundManager initialized with directory: {self.backgrounds_dir}")

    def _initialize_master_playlist(self) -> None:
        """Initialize the master playlist with all available videos across all themes."""
        if self._playlist_initialized:
            return
        
        logger.info("Initializing master playlist with all background videos")
        all_videos = []
        
        for theme in self.get_available_themes():
            theme_videos = self.get_backgrounds_by_theme(theme)
            all_videos.extend(theme_videos)
        
        if not all_videos:
            logger.warning("No background videos found for master playlist")
            self._master_playlist = []
            self._playlist_initialized = True
            return
        
        # Shuffle with time-based seed for maximum variety between runs
        random.seed(time.time())
        self._master_playlist = all_videos.copy()
        random.shuffle(self._master_playlist)
        
        self._playlist_index = 0
        self._playlist_initialized = True
        logger.info(f"Master playlist initialized with {len(self._master_playlist)} videos")

    def _get_next_video_from_playlist(self) -> Optional[Path]:
        """Get next video from master playlist, cycling through all available videos."""
        if not self._playlist_initialized:
            self._initialize_master_playlist()
        
        if not self._master_playlist:
            logger.warning("Master playlist is empty")
            return None
        
        # If we've reached the end of playlist, reshuffle and start over
        if self._playlist_index >= len(self._master_playlist):
            logger.info("Reached end of playlist, reshuffling")
            random.shuffle(self._master_playlist)
            self._playlist_index = 0
            self._recent_videos.clear()  # Clear recent tracking on reshuffle
        
        # Find next video that's not in recent videos (to avoid immediate repetition)
        start_index = self._playlist_index
        attempts = 0
        
        while attempts < len(self._master_playlist):
            video = self._master_playlist[self._playlist_index]
            self._playlist_index = (self._playlist_index + 1) % len(self._master_playlist)
            attempts += 1
            
            if video not in self._recent_videos:
                self._recent_videos.append(video)
                return video
            
            # If we've checked all videos and all are in recent, use the current one
            if self._playlist_index == start_index:
                break
        
        # Fallback to current video if all are recent
        video = self._master_playlist[self._playlist_index]
        self._playlist_index = (self._playlist_index + 1) % len(self._master_playlist)
        self._recent_videos.append(video)
        return video

    def get_available_themes(self) -> List[str]:
        themes = []
        for item in self.backgrounds_dir.iterdir():
            if item.is_dir():
                themes.append(item.name)
        if not themes:
            themes = settings.BACKGROUND_THEMES
        return sorted(themes)

    def get_backgrounds_by_theme(self, theme: str) -> List[Path]:
        theme_dir = self.backgrounds_dir / theme
        if not theme_dir.exists():
            logger.warning(f"Theme directory does not exist: {theme_dir}")
            return []

        video_files = []
        for ext in settings.ALLOWED_EXTENSIONS:
            video_files.extend(list(theme_dir.glob(f"*{ext}")))
        video_files.sort()
        logger.debug(f"Found {len(video_files)} background videos for theme '{theme}'")
        return video_files

    def get_random_background(self, theme: Optional[str] = None) -> Optional[Path]:
        if theme:
            backgrounds = self.get_backgrounds_by_theme(theme)
        else:
            backgrounds = []
            for theme_name in self.get_available_themes():
                backgrounds.extend(self.get_backgrounds_by_theme(theme_name))

        if not backgrounds:
            logger.warning("No background videos found")
            return None
        return random.choice(backgrounds)

    def get_random_backgrounds(self, count: int, theme: Optional[str] = None) -> List[Path]:
        if count <= 0:
            return []

        if theme:
            backgrounds = self.get_backgrounds_by_theme(theme)
        else:
            backgrounds = []
            for theme_name in self.get_available_themes():
                backgrounds.extend(self.get_backgrounds_by_theme(theme_name))

        if not backgrounds:
            logger.warning("No background videos found")
            return []

        unique_backgrounds = list(set(backgrounds))
        if len(unique_backgrounds) >= count:
            selected = random.sample(unique_backgrounds, count)
        else:
            selected = random.choices(unique_backgrounds, k=count)

        return selected

    def get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        if video_path in self._video_cache:
            return self._video_cache[video_path]

        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            data = json.loads(result.stdout)

            metadata = {
                'path': str(video_path),
                'exists': video_path.exists(),
                'size_bytes': video_path.stat().st_size if video_path.exists() else 0,
            }

            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break

            if video_stream:
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))

                duration_str = data.get('format', {}).get('duration')
                if duration_str:
                    duration = float(duration_str)
                else:
                    duration = float(video_stream.get('duration', 0))

                fps_str = video_stream.get('avg_frame_rate', '30/1')
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    fps = num / den if den != 0 else 30.0
                else:
                    fps = float(fps_str)

                metadata.update({
                    'width': width,
                    'height': height,
                    'duration_seconds': duration,
                    'fps': fps,
                    'aspect_ratio': f"{width}:{height}",
                    'is_portrait': height > width,
                    'is_landscape': width > height,
                    'is_square': width == height,
                })

            self._video_cache[video_path] = metadata
            return metadata

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to get metadata for {video_path}: {e}")
            metadata = {
                'path': str(video_path),
                'exists': video_path.exists(),
                'size_bytes': video_path.stat().st_size if video_path.exists() else 0,
                'width': 0,
                'height': 0,
                'duration_seconds': 0,
                'fps': 30.0,
                'error': str(e),
            }
            self._video_cache[video_path] = metadata
            return metadata

    def is_video_916(self, video_path: Path) -> bool:
        metadata = self.get_video_metadata(video_path)
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)

        if width == 1080 and height == 1920:
            return True

        if width > 0 and height > 0:
            aspect_ratio = width / height
            target_ratio = 9 / 16
            tolerance = 0.05
            return abs(aspect_ratio - target_ratio) < tolerance
        return False

    def extract_video_clip(
        self,
        video_path: Path,
        start_time: float,
        duration: float,
        output_path: Path,
        target_width: int = 1080,
        target_height: int = 1920,
        force_fps: int = 30,
        force_pixel_format: str = "yuv420p"
    ) -> bool:
        """
        Extract a video clip with strict encoding standards to ensure consistency.
        
        Args:
            video_path: Source video file
            start_time: Start time in seconds
            duration: Clip duration in seconds
            output_path: Output file path
            target_width: Target width (default 1080)
            target_height: Target height (default 1920)
            force_fps: Force output FPS (default 30)
            force_pixel_format: Force pixel format (default yuv420p)
        
        Returns:
            bool: Success status
        """
        try:
            metadata = self.get_video_metadata(video_path)
            original_width = metadata.get('width', 0)
            original_height = metadata.get('height', 0)

            if original_width == 0 or original_height == 0:
                logger.error(f"Cannot extract clip: Invalid video dimensions {original_width}x{original_height}")
                return False

            target_aspect = target_width / target_height

            if original_width / original_height > target_aspect:
                crop_height = original_height
                crop_width = int(original_height * target_aspect)
            else:
                crop_width = original_width
                crop_height = int(original_width / target_aspect)

            x_offset = max(0, (original_width - crop_width) // 2)
            y_offset = max(0, (original_height - crop_height) // 2)

            # Build FFmpeg command with strict encoding parameters
            # Force SAR 1:1 to ensure all clips are consistent for concatenation
            filter_complex = (
                f'[0:v]crop={crop_width}:{crop_height}:{x_offset}:{y_offset},'
                f'scale={target_width}:{target_height},'
                f'setsar=1,'
                f'fps=fps={force_fps}[v]'
            )
            
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(start_time),
                '-i', str(video_path),
                '-t', str(duration),
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-pix_fmt', force_pixel_format,
                '-r', str(force_fps),  # Ensure output frame rate matches target
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                str(output_path)
            ]

            logger.debug(f"Extracting clip with strict encoding: FPS={force_fps}, pixel_format={force_pixel_format}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                logger.error(f"FFmpeg failed with error: {result.stderr}")
                return False

            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error(f"Output file not created or empty: {output_path}")
                return False

            # Verify the extracted clip meets our encoding standards
            output_metadata = self.get_video_metadata(output_path)
            output_fps = output_metadata.get('fps', 0)
            
            if abs(output_fps - force_fps) > 0.5:
                logger.warning(f"Extracted clip FPS {output_fps} doesn't match target {force_fps}, re-encoding...")
                return self._reencode_clip_to_standards(output_path, force_fps, force_pixel_format)

            return True

        except Exception as e:
            logger.error(f"Failed to extract video clip: {e}")
            return False

    def _reencode_clip_to_standards(
        self,
        clip_path: Path,
        target_fps: int = 30,
        target_pixel_format: str = "yuv420p"
    ) -> bool:
        """Re-encode a clip to ensure it meets strict encoding standards."""
        try:
            temp_path = clip_path.with_suffix('.temp.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-i', str(clip_path),
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-pix_fmt', target_pixel_format,
                '-r', str(target_fps),
                '-c:a', 'copy',  # Keep original audio
                '-movflags', '+faststart',
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"Re-encoding failed: {result.stderr}")
                return False
            
            # Replace original with re-encoded version
            temp_path.replace(clip_path)
            logger.info(f"Re-encoded clip to meet standards: FPS={target_fps}, pixel_format={target_pixel_format}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to re-encode clip: {e}")
            return False

    def create_background_clip(
        self,
        duration: float,
        theme: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        if duration <= 0:
            return None

        if duration > settings.MAX_BACKGROUND_DURATION:
            duration = min(duration, settings.MAX_BACKGROUND_DURATION)

        background_path = self.get_random_background(theme)
        if not background_path:
            return None

        metadata = self.get_video_metadata(background_path)
        video_duration = metadata.get('duration_seconds', 0)

        if video_duration < duration:
            duration = video_duration

        if output_path is None:
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"background_{uuid.uuid4()}.mp4"

        start_time = 0.0  # Can be randomized if needed, but for satisfying we typically want 0.0

        success = self.extract_video_clip(
            video_path=background_path,
            start_time=start_time,
            duration=duration,
            output_path=output_path,
            target_width=settings.TARGET_WIDTH,
            target_height=settings.TARGET_HEIGHT,
            force_fps=settings.TARGET_FPS,
            force_pixel_format="yuv420p"
        )

        if not success:
            return None
        return output_path

    def create_sequential_background_clip(
        self,
        duration: float,
        theme: Optional[str] = None,
        output_path: Optional[Path] = None,
        dynamic_switching: bool = False
    ) -> Optional[Path]:
        """
        Create a sequential background video clip by concatenating short clips
        to cover the target duration. Ensures clips play from the beginning.

        Args:
            duration: Total duration needed for the background video
            theme: Optional specific theme to use (if None, uses random themes when dynamic_switching=True)
            output_path: Optional output path for the final concatenated video
            dynamic_switching: If True, enables random theme switching per clip with configurable clip durations
        """
        # Validate duration
        if duration <= 0:
            logger.error(f"Invalid duration: {duration}")
            return None

        if duration > settings.MAX_BACKGROUND_DURATION:
            logger.warning(f"Duration {duration}s exceeds maximum {settings.MAX_BACKGROUND_DURATION}s, clipping")
            duration = min(duration, settings.MAX_BACKGROUND_DURATION)

        # Use dynamic switching if enabled in settings or explicitly requested
        use_dynamic = dynamic_switching or settings.BACKGROUND_DYNAMIC_SWITCHING

        if use_dynamic:
            logger.info(f"Creating dynamic background sequence: {duration:.1f}s with master playlist")
            return self._create_dynamic_background_sequence(duration, output_path)
        else:
            logger.info(f"Creating sequential background clip: {duration:.1f}s using theme '{theme or 'random'}'")
            return self._create_sequential_clip_fixed_theme(duration, theme, output_path)

    def _create_sequential_clip_fixed_theme(
        self,
        duration: float,
        theme: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Internal method: Create sequential clip with fixed theme (original behavior)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            clip_paths = []
            accumulated_duration = 0.0
            clip_index = 0

            # Loop until we have enough background video to cover the audio
            while accumulated_duration < duration:
                # 1. Pick a random clip
                bg_path = self.get_random_background(theme)

                if not bg_path:
                    logger.error("No background videos available")
                    break

                # 2. Get video metadata to know its full duration
                metadata = self.get_video_metadata(bg_path)
                source_duration = metadata.get('duration_seconds', 0)

                if source_duration <= 0:
                    continue

                # 3. Take the full clip (unless it's the last one and exceeds what we need)
                remaining = duration - accumulated_duration
                clip_duration = min(source_duration, remaining)

                # 4. ALWAYS START FROM 0.0
                start_time = 0.0

                clip_path = temp_dir / f"clip_{clip_index}_{uuid.uuid4().hex[:8]}.mp4"

                success = self.extract_video_clip(
                    video_path=bg_path,
                    start_time=start_time,
                    duration=clip_duration,
                    output_path=clip_path,
                    target_width=settings.TARGET_WIDTH,
                    target_height=settings.TARGET_HEIGHT,
                    force_fps=settings.TARGET_FPS,
                    force_pixel_format="yuv420p"
                )

                if not success or not clip_path.exists() or clip_path.stat().st_size == 0:
                    logger.error(f"Failed to extract clip {clip_index} from {bg_path.name}")
                    continue

                clip_paths.append(clip_path)
                accumulated_duration += clip_duration
                clip_index += 1

                logger.debug(f"Added clip {clip_index}: {clip_duration:.1f}s from {bg_path.name}")

            if not clip_paths:
                logger.error("No clips were successfully extracted")
                return None

            if output_path is None:
                output_path = Path(tempfile.gettempdir()) / f"sequential_background_{uuid.uuid4()}.mp4"

            return self._concatenate_clips(clip_paths, output_path, temp_dir)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _create_dynamic_background_sequence(
        self,
        duration: float,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Internal method: Create dynamic background sequence using master playlist.
        Each clip has random duration between BACKGROUND_CLIP_DURATION_MIN and BACKGROUND_CLIP_DURATION_MAX.
        Uses master playlist to ensure even distribution across all available videos.
        """
        temp_dir = Path(tempfile.mkdtemp())
        try:
            clip_paths = []
            accumulated_duration = 0.0
            clip_index = 0

            # Ensure playlist is initialized
            self._initialize_master_playlist()
            
            if not self._master_playlist:
                logger.error("Master playlist is empty, cannot create dynamic sequence")
                return None

            logger.info(f"Creating dynamic sequence using master playlist with {len(self._master_playlist)} videos")

            # Loop until we have enough background video to cover the audio
            while accumulated_duration < duration:
                # 1. Get next video from master playlist (ensures no immediate repetition)
                bg_path = self._get_next_video_from_playlist()
                
                if not bg_path:
                    logger.error("Failed to get video from playlist")
                    break

                # 2. Get video metadata
                metadata = self.get_video_metadata(bg_path)
                source_duration = metadata.get('duration_seconds', 0)

                if source_duration <= 0:
                    continue

                # 3. Determine clip duration (random within configured range)
                clip_duration_min = settings.BACKGROUND_CLIP_DURATION_MIN
                clip_duration_max = settings.BACKGROUND_CLIP_DURATION_MAX

                # Ensure min <= max
                if clip_duration_min > clip_duration_max:
                    clip_duration_min, clip_duration_max = clip_duration_max, clip_duration_min

                # Random duration within range
                target_clip_duration = random.uniform(clip_duration_min, clip_duration_max)

                # Adjust for remaining duration needed
                remaining = duration - accumulated_duration
                if remaining < target_clip_duration:
                    target_clip_duration = remaining

                # Ensure we don't exceed source duration
                actual_clip_duration = min(target_clip_duration, source_duration)
                if actual_clip_duration <= 0:
                    continue

                # 4. ALWAYS START FROM 0.0
                start_time = 0.0

                clip_path = temp_dir / f"clip_{clip_index}_{uuid.uuid4().hex[:8]}.mp4"

                success = self.extract_video_clip(
                    video_path=bg_path,
                    start_time=start_time,
                    duration=actual_clip_duration,
                    output_path=clip_path,
                    target_width=settings.TARGET_WIDTH,
                    target_height=settings.TARGET_HEIGHT,
                    force_fps=settings.TARGET_FPS,
                    force_pixel_format="yuv420p"
                )

                if not success or not clip_path.exists() or clip_path.stat().st_size == 0:
                    logger.error(f"Failed to extract clip {clip_index} from {bg_path.name}")
                    continue

                clip_paths.append(clip_path)
                accumulated_duration += actual_clip_duration
                clip_index += 1

                logger.debug(f"Added dynamic clip {clip_index}: {actual_clip_duration:.1f}s from {bg_path.name}")

            if not clip_paths:
                logger.error("No clips were successfully extracted")
                return None

            if output_path is None:
                output_path = Path(tempfile.gettempdir()) / f"dynamic_background_{uuid.uuid4()}.mp4"

            return self._concatenate_clips(clip_paths, output_path, temp_dir)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _concatenate_clips(self, clip_paths: List[Path], output_path: Path, temp_dir: Path) -> Optional[Path]:
        """
        Internal method: Concatenate clips with re-encoding to ensure consistent stream parameters.
        This fixes freezing issues caused by mismatched FPS, timebase, or pixel formats.
        """
        if not clip_paths:
            logger.error("No clips to concatenate")
            return None
        
        # Create concat file
        concat_file = temp_dir / "concat_list.txt"
        with open(concat_file, 'w', encoding='utf-8') as f:
            for clip_path in clip_paths:
                path_str = str(clip_path).replace('\\', '\\\\').replace("'", "'\\''")
                f.write(f"file '{path_str}'\n")
        
        logger.info(f"Concatenating {len(clip_paths)} clips with re-encoding for stability")
        
        # Use filter_complex concat with re-encoding to ensure consistent parameters
        try:
            # Build input arguments
            input_args = []
            filter_inputs = []
            filter_concat_video = []
            filter_concat_audio = []
            
            for i, clip_path in enumerate(clip_paths):
                input_args.extend(['-i', str(clip_path)])
                filter_inputs.append(f'[{i}:v]')
                filter_inputs.append(f'[{i}:a]')
                filter_concat_video.append(f'v{i}')
                filter_concat_audio.append(f'a{i}')
            
            # Create filter_complex for concatenation
            filter_complex = (
                f"{''.join(filter_inputs)}"
                f"concat=n={len(clip_paths)}:v=1:a=1"
                f"[v][a]"
            )
            
            cmd = [
                'ffmpeg', '-y',
                *input_args,
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-map', '[a]',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-r', str(settings.TARGET_FPS),
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                str(output_path)
            ]
            
            logger.debug(f"Concatenation command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                logger.error(f"FFmpeg concatenation failed: {result.stderr}")
                # Fallback to simple concat (less reliable but might work)
                return self._concatenate_clips_fallback(clip_paths, output_path, temp_dir)
            
            if not output_path.exists() or output_path.stat().st_size == 0:
                logger.error(f"Output file not created or empty: {output_path}")
                return None
            
            logger.info(f"Successfully created background video with re-encoding: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Concatenation with re-encoding failed: {e}")
            # Fallback to simple concat
            return self._concatenate_clips_fallback(clip_paths, output_path, temp_dir)

    def _concatenate_clips_fallback(
        self,
        clip_paths: List[Path],
        output_path: Path,
        temp_dir: Path
    ) -> Optional[Path]:
        """Fallback concatenation method using stream copy (less reliable but faster)."""
        logger.warning("Using fallback concatenation method (stream copy)")
        
        concat_file = temp_dir / "concat_list.txt"
        with open(concat_file, 'w', encoding='utf-8') as f:
            for clip_path in clip_paths:
                path_str = str(clip_path).replace('\\', '\\\\').replace("'", "'\\''")
                f.write(f"file '{path_str}'\n")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            logger.error(f"Fallback concatenation also failed: {result.stderr}")
            return None
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error(f"Output file not created or empty: {output_path}")
            return None
        
        logger.warning(f"Created background video using fallback (stream copy): {output_path}")
        return output_path

    def validate_backgrounds(self) -> Dict[str, Any]:
        results = {
            'total_backgrounds': 0,
            'valid_backgrounds': 0,
            'invalid_backgrounds': 0,
            'themes': {},
            'errors': []
        }

        for theme in self.get_available_themes():
            theme_results = {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'videos': []
            }

            backgrounds = self.get_backgrounds_by_theme(theme)
            results['total_backgrounds'] += len(backgrounds)
            theme_results['total'] = len(backgrounds)

            for bg_path in backgrounds:
                video_info = {
                    'path': str(bg_path),
                    'name': bg_path.name,
                }

                try:
                    metadata = self.get_video_metadata(bg_path)
                    if metadata.get('width', 0) > 0 and metadata.get('height', 0) > 0:
                        video_info.update({
                            'width': metadata['width'],
                            'height': metadata['height'],
                            'duration': metadata['duration_seconds'],
                            'fps': metadata['fps'],
                            'is_916': self.is_video_916(bg_path),
                            'valid': True
                        })
                        results['valid_backgrounds'] += 1
                        theme_results['valid'] += 1
                    else:
                        video_info['valid'] = False
                        video_info['error'] = 'Invalid dimensions'
                        results['invalid_backgrounds'] += 1
                        theme_results['invalid'] += 1
                        results['errors'].append(f"Invalid video: {bg_path.name}")
                except Exception as e:
                    video_info['valid'] = False
                    video_info['error'] = str(e)
                    results['invalid_backgrounds'] += 1
                    theme_results['invalid'] += 1
                    results['errors'].append(f"Error processing {bg_path.name}: {e}")

                theme_results['videos'].append(video_info)
            results['themes'][theme] = theme_results

        return results


def create_background_clip(
    duration: float,
    theme: Optional[str] = None,
    output_path: Optional[Path] = None
) -> Optional[Path]:
    manager = BackgroundManager()
    return manager.create_background_clip(duration, theme, output_path)