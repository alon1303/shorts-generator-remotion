import json
import logging
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any

from config.settings import settings
from .models import AudioChunk, WordTimestamp

logger = logging.getLogger(__name__)

class RemotionComposer:
    """Composes videos using Remotion engine."""
    
    def __init__(self, remotion_path: Optional[Path] = None):
        # Always resolve absolute path from settings base_dir if none provided
        self.remotion_path = remotion_path or (settings.BASE_DIR.parent / "remotion_engine").resolve()
        logger.info(f"RemotionComposer initialized at {self.remotion_path}")

    def _prepare_props(self, 
                       audio_chunks: List[AudioChunk], 
                       title: str, 
                       author: str, 
                       subreddit: str,
                       title_card_duration: float,
                       public_dir: Path,
                       background_music_path: Optional[Path] = None
                       ) -> Dict[str, Any]:
        """Converts internal models to Remotion InputProps and copies assets."""
        
        chunks_data = []
        for i, chunk in enumerate(audio_chunks):
            # Copy audio file to public dir
            dest_audio = public_dir / f"audio_{i}.mp3"
            shutil.copy2(chunk.audio_path, dest_audio)
            
            chunks_data.append({
                "audioPath": dest_audio.name,
                "text": chunk.text,
                "duration": chunk.duration_seconds,
                "wordTimestamps": [
                    {"word": w.word, "start": w.start, "end": w.end} 
                    for w in chunk.word_timestamps
                ]
            })
            
        bg_music_name = None
        if background_music_path and background_music_path.exists():
            dest_bg = public_dir / "bg_music.mp3"
            shutil.copy2(background_music_path, dest_bg)
            bg_music_name = "bg_music.mp3"
            
        return {
            "audioChunks": chunks_data,
            "title": title,
            "author": author,
            "subreddit": subreddit,
            "titleCardDuration": title_card_duration,
            "backgroundMusicPath": bg_music_name,
            "fps": settings.TARGET_FPS,
            "width": settings.TARGET_WIDTH,
            "height": settings.TARGET_HEIGHT
        }

    def render_video(self, 
                     audio_chunks: List[AudioChunk], 
                     title: str, 
                     author: str, 
                     subreddit: str,
                     title_card_duration: float,
                     output_path: Path,
                     background_music_path: Optional[Path] = None
                     ) -> bool:
        """Renders video using Remotion CLI (Synchronous)."""
        
        # Ensure public dir exists
        public_dir = self.remotion_path.absolute() / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        
        props = self._prepare_props(
            audio_chunks, title, author, subreddit, title_card_duration, public_dir, background_music_path
        )
        
        # Calculate total duration for Remotion composition
        total_duration = sum(chunk.duration_seconds for chunk in audio_chunks)
        # We might need a small buffer
        total_frames = int(total_duration * settings.TARGET_FPS) + 30
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(props, f)
            props_file = Path(f.name)
            
        try:
            logger.info(f"Starting Remotion render to {output_path}")
            
            remotion_bin_path = self.remotion_path / "node_modules" / ".bin" / ("remotion.cmd" if os.name == 'nt' else "remotion")
            if not remotion_bin_path.exists():
                logger.error(f"Remotion CLI not found at {remotion_bin_path}")
                return False
                
            remotion_bin = str(remotion_bin_path.absolute())
                
            # Command: remotion render <id> <output> --props=<props>
            cmd = [
                remotion_bin, "render", 
                "ShortVideo", 
                str(output_path.absolute()),
                f"--props={str(props_file.absolute())}",
                # Overriding composition duration
                "--duration", str(total_frames)
            ]
            
            logger.info(f"Executing Remotion Command: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd, 
                cwd=str(self.remotion_path.absolute()),
                capture_output=True,
                text=True,
                shell=True if os.name == 'nt' else False # Windows requires shell=True for .cmd files
            )
            
            if process.returncode != 0:
                logger.error(f"Remotion render failed: {process.stderr}")
                return False
                
            logger.info("Remotion render completed successfully")
            return output_path.exists()
            
        except Exception as e:
            logger.exception(f"Error during Remotion render: {e}")
            return False
        finally:
            if props_file.exists():
                props_file.unlink()
