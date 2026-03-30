"""
Data models used across the TTS and video generation pipeline.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class WordTimestamp:
    """Represents a word with its timing information."""
    word: str
    start: float  # Start time in seconds
    end: float    # End time in seconds
    confidence: float  # Confidence score (0.0-1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "word": self.word,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WordTimestamp':
        """Create WordTimestamp from dictionary."""
        return cls(
            word=data["word"],
            start=data["start"],
            end=data["end"],
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class AudioChunk:
    """Represents a generated audio chunk with metadata."""
    chunk_id: str
    text: str
    audio_path: Path
    duration_seconds: float
    voice_id: str
    file_size_bytes: int
    word_timestamps: Optional[List[WordTimestamp]] = None
    is_first_part: bool = False
    power_words: Optional[List[str]] = None
    part_index: Optional[str] = None  # e.g., "1/3"
    title_word_count: int = 0
    timing_map: Optional[List[Dict[str, float]]] = None  # Map of silence removals
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "audio_path": str(self.audio_path),
            "duration_seconds": self.duration_seconds,
            "voice_id": self.voice_id,
            "file_size_bytes": self.file_size_bytes,
            "has_word_timestamps": self.word_timestamps is not None and len(self.word_timestamps) > 0,
            "word_count": len(self.word_timestamps) if self.word_timestamps else 0,
            "power_words": self.power_words,
            "part_index": self.part_index,
            "title_word_count": self.title_word_count,
            "has_timing_map": self.timing_map is not None and len(self.timing_map) > 0,
        }
