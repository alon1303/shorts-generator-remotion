"""
Story Processor for splitting Reddit stories into logical parts for Shorts videos.
Handles text segmentation, duration calculation, and part optimization.
"""

import re
import logging
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .reddit_client import RedditStory
from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)

class SplitStrategy(Enum):
    """Strategy for splitting text into parts."""
    SENTENCE = "sentence"  # Split at sentence boundaries
    PARAGRAPH = "paragraph"  # Split at paragraph boundaries
    HYBRID = "hybrid"  # Use paragraphs first, then sentences if needed
    AI = "ai"  # Use Gemini Flash for intelligent splitting

@dataclass
class StoryPart:
    """Represents a single part of a split story."""
    part_number: int
    text: str
    word_count: int
    estimated_duration: float  # in seconds
    start_index: int  # Character index in original text
    end_index: int  # Character index in original text
    power_words: Optional[List[str]] = None
    part_index_label: Optional[str] = None  # e.g., "1/3"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "part_number": self.part_number,
            "text": self.text,
            "word_count": self.word_count,
            "estimated_duration": self.estimated_duration,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "power_words": self.power_words,
            "part_index_label": self.part_index_label,
        }

@dataclass
class ProcessedStory:
    """Represents a story that has been processed into parts."""
    story: RedditStory
    parts: List[StoryPart]
    total_parts: int
    total_duration: float
    strategy_used: SplitStrategy
    detected_gender: Optional[str] = None # "M" or "F"
    detected_age: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "story": {
                "id": self.story.id,
                "title": self.story.title,
                "subreddit": self.story.subreddit,
                "word_count": self.story.word_count,
                "estimated_duration": self.story.estimated_duration,
            },
            "parts": [part.to_dict() for part in self.parts],
            "total_parts": self.total_parts,
            "total_duration": self.total_duration,
            "strategy_used": self.strategy_used.value,
            "detected_gender": self.detected_gender,
            "detected_age": self.detected_age,
        }

class StoryProcessor:
    """Processes stories by splitting them into logical parts for Shorts videos."""
    
    def __init__(
        self,
        min_part_duration: Optional[int] = None,
        max_part_duration: Optional[int] = None,
    ):
        """
        Initialize story processor with configuration.
        """
        self.min_part_duration = min_part_duration or settings.MIN_PART_DURATION
        self.max_part_duration = max_part_duration or settings.MAX_PART_DURATION
        
        self._fallback_wpm = 150
        self.max_words_per_part = int((self.max_part_duration / 60) * self._fallback_wpm)
        
        # AI settings
        self.ai_min_part_duration = settings.AI_MIN_PART_DURATION
        self.ai_split_threshold = settings.STORY_AI_SPLIT_THRESHOLD
        
        # Gemini initialization
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
                self.ai_available = True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini for StoryProcessor: {e}")
                self.ai_available = False
        else:
            self.ai_available = False
            
        logger.info(
            f"StoryProcessor initialized: "
            f"{self.min_part_duration}-{self.max_part_duration}s parts. AI available: {self.ai_available}"
        )
    
    def _words_to_duration(self, word_count: int) -> float:
        """Estimate duration in seconds from word count using the fallback WPM."""
        return (word_count / self._fallback_wpm) * 60

    def _estimate_duration_from_words(self, word_count: int) -> float:
        """Estimate duration in seconds from word count using the fallback WPM."""
        return self._words_to_duration(word_count)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        sentence_endings = r'(?<=[.!?])\s+(?=[A-Z])'
        text = re.sub(r'\s+', ' ', text.strip())
        sentences = re.split(sentence_endings, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            sentences = [s.strip() for s in text.split('.') if s.strip()]
        return sentences
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n+', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]
        return paragraphs
    
    def _merge_small_segments(
        self, 
        segments: List[str], 
        start_indices: List[int],
        max_words: Optional[int] = None
    ) -> Tuple[List[str], List[int]]:
        """Merge small segments together."""
        if not segments:
            return [], []
        
        limit = max_words or self.max_words_per_part
        merged_segments = []
        merged_indices = []
        
        current_segment = segments[0]
        current_start = start_indices[0]
        current_word_count = len(current_segment.split())
        
        for i in range(1, len(segments)):
            segment = segments[i]
            segment_word_count = len(segment.split())
            if current_word_count + segment_word_count <= limit:
                current_segment += " " + segment
                current_word_count += segment_word_count
            else:
                merged_segments.append(current_segment)
                merged_indices.append(current_start)
                current_segment = segment
                current_start = start_indices[i]
                current_word_count = segment_word_count
        
        merged_segments.append(current_segment)
        merged_indices.append(current_start)
        return merged_segments, merged_indices
    
    def _split_large_segments(
        self, 
        segments: List[str], 
        start_indices: List[int]
    ) -> Tuple[List[str], List[int]]:
        """Split large segments."""
        if not segments:
            return [], []
        
        split_segments = []
        split_indices = []
        for segment, start_index in zip(segments, start_indices):
            word_count = len(segment.split())
            if word_count <= self.max_words_per_part:
                split_segments.append(segment)
                split_indices.append(start_index)
            else:
                sentences = self._split_into_sentences(segment)
                sentence_indices = []
                current_pos = 0
                for sentence in sentences:
                    sentence_indices.append(start_index + current_pos)
                    current_pos += len(sentence) + 1
                merged_sentences, merged_indices = self._merge_small_segments(sentences, sentence_indices)
                split_segments.extend(merged_sentences)
                split_indices.extend(merged_indices)
        return split_segments, split_indices
    
    def _create_story_parts(
        self, 
        segments: List[str], 
        start_indices: List[int]
    ) -> List[StoryPart]:
        """Create StoryPart objects from text segments."""
        parts = []
        for i, (segment, start_index) in enumerate(zip(segments, start_indices), 1):
            word_count = len(segment.split())
            duration = self._estimate_duration_from_words(word_count)
            part = StoryPart(
                part_number=i,
                text=segment,
                word_count=word_count,
                estimated_duration=duration,
                start_index=start_index,
                end_index=start_index + len(segment),
            )
            parts.append(part)
        return parts

    def detect_gender(self, title: str, text: str) -> Optional[str]:
        """Detects gender from title or text."""
        patterns = [
            r'\((\d+)?([MF])\)', r'\[(\d+)?([MF])\]', r'\(?([MF])(\d+)?\)?',
            r'\bI\'m a (\d+)\s?(year old)?\s?([mf])\b', r'\bI am a (\d+)\s?(year old)?\s?([mf])\b'
        ]
        combined_text = title + " " + text[:500]
        for pattern in patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                for group in match.groups():
                    if group and group.upper() in ["M", "F"]:
                        return group.upper()
        return None

    async def _process_story_ai(self, story: RedditStory) -> Optional[ProcessedStory]:
        """Process story using Gemini Flash for narrative splitting."""
        if not self.ai_available: return None

        prompt = f"""
        Analyze this Reddit story and divide it into logical parts for a multi-part video series.
        
        CRITICAL RULES:
        1. DO NOT modify, rewrite, or summarize the story text. Use the EXACT text provided.
        2. Identify logical split points based on HIGH-TENSION moments (Cliffhangers).
        3. Each part MUST be at least {self.ai_min_part_duration} seconds long. Use your best judgement to ensure each part takes at least {self.ai_min_part_duration} seconds to read aloud at a normal pace.
        4. Identify narrator's gender (M/F) and age.
        5. Extract 3-5 "Power Words" for each part.
        
        Response Format (JSON only):
        {{
            "detected_gender": "M"/"F"/null,
            "detected_age": int/null,
            "parts": [
                {{ "text": "exact text", "power_words": ["W1", "W2"] }}
            ]
        }}
        
        Story Title: {story.title}
        Story Content:
        {story.text}
        """

        try:
            response = self.model.generate_content(prompt)
            if not response or not response.text: return None
            
            json_text = response.text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_text)
            ai_parts = data.get("parts", [])
            if not ai_parts: return None
                
            parts = []
            current_pos = 0
            for i, part_data in enumerate(ai_parts, 1):
                part_text = part_data.get("text", "").strip()
                if not part_text: continue
                
                start_index = story.text.find(part_text, max(0, current_pos - 100))
                if start_index == -1: start_index = current_pos
                
                word_count = len(part_text.split())
                part = StoryPart(
                    part_number=i,
                    text=part_text,
                    word_count=word_count,
                    estimated_duration=self._words_to_duration(word_count),
                    start_index=start_index,
                    end_index=start_index + len(part_text),
                    power_words=part_data.get("power_words", [])
                )
                parts.append(part)
                current_pos = start_index + len(part_text)
            
            return ProcessedStory(
                story=story,
                parts=parts,
                total_parts=len(parts),
                total_duration=sum(p.estimated_duration for p in parts),
                strategy_used=SplitStrategy.AI,
                detected_gender=data.get("detected_gender"),
                detected_age=data.get("detected_age")
            )
        except Exception as e:
            logger.error(f"AI Story Processing failed: {e}")
            return None

    async def _extract_power_words_single(self, text: str) -> List[str]:
        """Extract power words for a single part."""
        if not self.ai_available:
            logger.warning("Gemini AI is not available (GEMINI_API_KEY may be missing). Returning empty keywords.")
            return []
            
        prompt = f"Extract 3-5 'Power Words' from this text. Return JSON array ONLY of strings. Example: ['WORD1', 'WORD2']\nText: {text[:2000]}"
        try:
            # Use the async generation method to prevent blocking the event loop
            response = await self.model.generate_content_async(prompt)
            json_text = response.text.strip()
            if "```json" in json_text: json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text: json_text = json_text.split("```")[1].split("```")[0].strip()
            data = json.loads(json_text)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"EXACT LLM ERROR in _extract_power_words_single: {e}")
            return []

    async def process_story(
        self,
        story: RedditStory,
        strategy: SplitStrategy = SplitStrategy.HYBRID,
        split_into_parts: bool = True
    ) -> ProcessedStory:
        """Main processing method with AI and Fallback."""
        logger.info(f"Processing story: '{story.title[:50]}...'")

        if self.ai_available and story.estimated_duration > self.ai_split_threshold and split_into_parts:
            ai_processed = await self._process_story_ai(story)
            if ai_processed:
                short_parts = [i for i, p in enumerate(ai_processed.parts) if p.estimated_duration < self.ai_min_part_duration]
                if short_parts:
                    segments = [p.text for p in ai_processed.parts]
                    indices = [p.start_index for p in ai_processed.parts]
                    merged_texts, merged_indices = self._merge_small_segments(segments, indices)
                    ai_processed.parts = self._create_story_parts(merged_texts, merged_indices)
                self._enrich_parts(ai_processed)
                return ai_processed

        processed = self._process_story_standard(story, strategy, split_into_parts)
        if self.ai_available:
            for part in processed.parts:
                part.power_words = await self._extract_power_words_single(part.text)
        self._enrich_parts(processed)
        return processed

    def _process_story_standard(self, story: RedditStory, strategy: SplitStrategy, split_into_parts: bool) -> ProcessedStory:
        """Legacy hybrid splitting."""
        detected_gender = self.detect_gender(story.title, story.text)
        if not split_into_parts or story.estimated_duration <= 120.0:
            p = StoryPart(1, story.text, len(story.text.split()), story.estimated_duration, 0, len(story.text))
            return ProcessedStory(story, [p], 1, story.estimated_duration, strategy, detected_gender)

        segments = self._split_into_paragraphs(story.text) if strategy != SplitStrategy.SENTENCE else self._split_into_sentences(story.text)
        start_indices = []
        curr = 0
        for s in segments:
            idx = story.text.find(s, curr)
            start_indices.append(idx if idx != -1 else curr)
            curr = (idx if idx != -1 else curr) + len(s)
        segments, start_indices = self._merge_small_segments(segments, start_indices)
        segments, start_indices = self._split_large_segments(segments, start_indices)
        parts = self._create_story_parts(segments, start_indices)
        return ProcessedStory(story, parts, len(parts), sum(p.estimated_duration for p in parts), strategy, detected_gender)

    def _enrich_parts(self, processed: ProcessedStory):
        """Add CTAs and labels."""
        total = len(processed.parts)
        for i, part in enumerate(processed.parts):
            part.part_index_label = f"{i+1}/{total}"
            if total > 1 and i < total - 1:
                cta = f"\n\nLike and subscribe for Part {i + 2}"
                if "Like and subscribe for Part" not in part.text:
                    part.text += cta
                    part.word_count = len(part.text.split())
                    part.estimated_duration = self._words_to_duration(part.word_count)
            
            if not part.estimated_duration:
                part.word_count = len(part.text.split())
                part.estimated_duration = self._words_to_duration(part.word_count)

    def validate_parts(self, processed_story: ProcessedStory) -> bool:
        return all(p.estimated_duration >= settings.AI_MIN_PART_DURATION for p in processed_story.parts)

async def process_story(story: RedditStory, strategy: SplitStrategy = SplitStrategy.HYBRID, **kwargs) -> ProcessedStory:
    return await StoryProcessor(**kwargs).process_story(story, strategy)
