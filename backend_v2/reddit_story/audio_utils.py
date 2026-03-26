"""
Audio utility functions for detecting silence and calculating offsets.
"""
import subprocess
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import re

try:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

from config.settings import settings

logger = logging.getLogger(__name__)

def get_audio_duration(audio_path: Path) -> float:
    """
    Get accurate audio duration using ffprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds
    """
    try:
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
            logger.debug(f"Audio duration from ffprobe: {duration:.3f}s")
            return duration
        else:
            logger.warning(f"ffprobe failed for {audio_path}: {result.stderr}")
            return 0.0
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0

def detect_silence_at_beginning(audio_path: Path, silence_threshold_db: float = -30.0, 
                               min_silence_duration: float = 0.1) -> float:
    """
    Detect silence at the beginning of audio file using ffmpeg.
    
    Args:
        audio_path: Path to audio file
        silence_threshold_db: Silence threshold in dB (default: -30dB)
        min_silence_duration: Minimum silence duration to detect (default: 0.1s)
        
    Returns:
        Duration of silence at beginning in seconds, or 0.0 if no significant silence
    """
    try:
        # Use ffmpeg to detect silence
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-af', f'silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        output = result.stderr
        
        # Parse silence detection output
        lines = output.split('\n')
        for line in lines:
            if 'silence_start:' in line:
                # Extract time
                parts = line.split('silence_start:')
                if len(parts) > 1:
                    time_str = parts[1].strip().split()[0]
                    try:
                        silence_start = float(time_str)
                        # Check if this is at the very beginning (within 50ms)
                        if silence_start < 0.05:
                            # Look for silence_end to get duration
                            for next_line in lines:
                                if 'silence_end:' in next_line and f'silence_start: {time_str}' in line:
                                    end_parts = next_line.split('silence_end:')
                                    if len(end_parts) > 1:
                                        end_time_str = end_parts[1].strip().split()[0]
                                        silence_end = float(end_time_str)
                                        silence_duration = silence_end - silence_start
                                        logger.debug(f"Detected {silence_duration:.3f}s silence at beginning of {audio_path}")
                                        return silence_duration
                        break
                    except ValueError:
                        pass
        
        logger.debug(f"No significant silence detected at beginning of {audio_path}")
        return 0.0
    except Exception as e:
        logger.warning(f"Error detecting silence: {e}")
        return 0.0

def analyze_audio_for_offset(audio_path: Path) -> Tuple[float, float]:
    """
    Analyze audio file for timing offset issues.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Tuple of (actual_duration, silence_offset)
    """
    actual_duration = get_audio_duration(audio_path)
    silence_offset = detect_silence_at_beginning(audio_path)
    
    if silence_offset > 0.1:  # More than 100ms of silence
        logger.warning(f"Audio {audio_path.name} has {silence_offset:.3f}s silence at beginning")
    
    return actual_duration, silence_offset

def adjust_word_timestamps(word_timestamps: List['WordTimestamp'], 
                          offset_seconds: float) -> List['WordTimestamp']:
    """
    Adjust word timestamps by applying an offset.
    
    Args:
        word_timestamps: List of WordTimestamp objects
        offset_seconds: Offset to apply (positive = delay, negative = advance)
        
    Returns:
        Adjusted list of WordTimestamp objects
    """
    if not word_timestamps or abs(offset_seconds) < 0.001:  # Less than 1ms
        return word_timestamps
    
    adjusted = []
    for ts in word_timestamps:
        adjusted.append(type(ts)(
            word=ts.word,
            start=max(0.0, ts.start + offset_seconds),
            end=max(0.0, ts.end + offset_seconds),
            confidence=ts.confidence
        ))
    
    logger.debug(f"Adjusted {len(word_timestamps)} word timestamps by {offset_seconds:.3f}s")
    return adjusted

def get_audio_start_time(audio_path: Path) -> float:
    """
    Get the actual start time of audio content (after any initial silence).
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Start time in seconds (0.0 if no significant silence)
    """
    return detect_silence_at_beginning(audio_path)

def remove_silences(
    audio_path: Path,
    output_path: Optional[Path] = None,
    threshold_db: Optional[float] = None,
    min_silence_ms: Optional[int] = None,
    keep_silence_ms: Optional[int] = None
) -> Tuple[Path, List[Dict[str, float]]]:
    """
    Remove silences from audio and return the new path and a timing map.
    
    Returns:
        Tuple of (new_audio_path, timing_map)
        timing_map is a list of dicts: {"original_start": float, "new_start": float, "duration": float}
    """
    if not PYDUB_AVAILABLE:
        logger.error("pydub not available, skipping silence removal")
        return audio_path, []

    threshold_db = threshold_db or settings.SILENCE_THRESHOLD_DB
    min_silence_ms = min_silence_ms or settings.MIN_SILENCE_DURATION_MS
    keep_silence_ms = keep_silence_ms or settings.KEEP_SILENCE_MS

    try:
        audio = AudioSegment.from_file(audio_path)
        
        # detect_nonsilent returns list of [start, end] in ms
        nonsilent_chunks = detect_nonsilent(
            audio, 
            min_silence_len=min_silence_ms, 
            silence_thresh=threshold_db
        )

        if not nonsilent_chunks:
            return audio_path, []

        new_audio = AudioSegment.empty()
        timing_map = []
        current_new_time_ms = 0

        for start_ms, end_ms in nonsilent_chunks:
            # Add some buffer silence before and after
            chunk_start = max(0, start_ms - keep_silence_ms)
            chunk_end = min(len(audio), end_ms + keep_silence_ms)
            
            chunk = audio[chunk_start:chunk_end]
            new_audio += chunk
            
            timing_map.append({
                "original_start": chunk_start / 1000.0,
                "original_end": chunk_end / 1000.0,
                "new_start": current_new_time_ms / 1000.0,
                "duration": (chunk_end - chunk_start) / 1000.0
            })
            
            current_new_time_ms += (chunk_end - chunk_start)

        if output_path is None:
            temp_dir = Path(tempfile.gettempdir()) / "shorts_audio_cleanup"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = temp_dir / f"cleaned_{int(time.time())}_{audio_path.stem}.wav"

        try:
            new_audio.export(str(output_path), format="wav")
            orig_dur = len(audio)/1000.0
            new_dur = len(new_audio)/1000.0
            saved = orig_dur - new_dur
            logger.info(f"✂️ SILENCE REMOVAL: {audio_path.name}")
            logger.info(f"   - Original duration: {orig_dur:.2f}s")
            logger.info(f"   - New duration: {new_dur:.2f}s")
            logger.info(f"   - Time saved: {saved:.2f}s ({ (saved/orig_dur)*100:.1f}%)")
        except Exception as e:
            logger.error(f"Failed to export cleaned audio: {e}")
            return audio_path, []
            
        return output_path, timing_map

    except Exception as e:
        logger.error(f"Error removing silences: {e}")
        return audio_path, []

def map_timestamp_to_new_time(original_time: float, timing_map: List[Dict[str, float]]) -> float:
    """
    Map an original timestamp to the new timestamp after silence removal.
    Improved to handle gaps robustly and ensure monotonic mapping.
    
    Args:
        original_time: Time in original audio (seconds)
        timing_map: List of dicts with keys: original_start, original_end, new_start, duration
    
    Returns:
        Mapped time in cleaned audio (seconds)
    """
    if not timing_map:
        return original_time
    
    # Binary search for the appropriate chunk
    lo, hi = 0, len(timing_map) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        entry = timing_map[mid]
        
        if original_time < entry["original_start"]:
            hi = mid - 1
        elif original_time > entry["original_end"]:
            lo = mid + 1
        else:
            # Within this kept chunk
            offset = original_time - entry["original_start"]
            return entry["new_start"] + offset
    
    # original_time is not inside any kept chunk; it's in a gap
    # Determine whether it's before the first chunk or between chunks
    if original_time < timing_map[0]["original_start"]:
        # Before first chunk: map to start of first chunk
        return timing_map[0]["new_start"]
    
    # After last chunk: map to end of last chunk
    if original_time > timing_map[-1]["original_end"]:
        return timing_map[-1]["new_start"] + timing_map[-1]["duration"]
    
    # Between two chunks: find the gap it falls into
    for i in range(len(timing_map) - 1):
        if timing_map[i]["original_end"] < original_time < timing_map[i + 1]["original_start"]:
            # In the gap between chunk i and i+1
            # Map to the end of chunk i (or start of chunk i+1?)
            # Choose the nearest edge to avoid large jumps.
            gap_start = timing_map[i]["original_end"]
            gap_end = timing_map[i + 1]["original_start"]
            # Determine which edge is closer
            dist_to_start = original_time - gap_start
            dist_to_end = gap_end - original_time
            if dist_to_start <= dist_to_end:
                # Closer to start of gap (end of previous chunk)
                return timing_map[i]["new_start"] + timing_map[i]["duration"]
            else:
                # Closer to end of gap (start of next chunk)
                return timing_map[i + 1]["new_start"]
    
    # Should not reach here
    return original_time

# Test function
def test_audio_analysis():
    """Test the audio analysis functions."""
    import tempfile
    from dataclasses import dataclass
    
    @dataclass
    class TestWordTimestamp:
        word: str
        start: float
        end: float
        confidence: float
    
    print("Testing audio utility functions...")
    
    # Test timestamp adjustment
    test_timestamps = [
        TestWordTimestamp("Hello", 0.5, 0.8, 0.95),
        TestWordTimestamp("world", 0.9, 1.2, 0.92),
        TestWordTimestamp("test", 1.3, 1.6, 0.94),
    ]
    
    print(f"Original timestamps:")
    for ts in test_timestamps:
        print(f"  '{ts.word}': {ts.start:.3f}s - {ts.end:.3f}s")
    
    adjusted = adjust_word_timestamps(test_timestamps, 0.25)
    print(f"\nAdjusted by +0.25s:")
    for ts in adjusted:
        print(f"  '{ts.word}': {ts.start:.3f}s - {ts.end:.3f}s")
    
    print("\nAudio utility functions ready.")

if __name__ == "__main__":
    test_audio_analysis()