
import logging
import json
import re
from typing import List, Optional
import google.generativeai as genai
from config.settings import settings

logger = logging.getLogger(__name__)

class GeminiKeywordExtractor:
    """Uses Google Gemini Flash to extract the most impactful words from a story title."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._initialized = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self._initialized = True
                logger.info(f"GeminiKeywordExtractor initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("GEMINI_API_KEY not found in settings. AI keyword extraction will be disabled.")

    async def extract_keywords(self, title: str) -> List[str]:
        """
        Extract 2-5 most impactful words from the title using Gemini.
        Returns a list of uppercase words.
        """
        if not self._initialized or not title:
            return []

        prompt = f"""
        Analyze this Reddit story title and identify the 2 to 5 most dramatic, viral, or impactful words.
        Focus on words that create curiosity, shock, or emotional resonance (verbs, nouns, adjectives).
        
        Rules:
        1. Return ONLY a comma-separated list of the words.
        2. Do not include common filler words (the, a, is, etc.).
        3. Convert all words to UPPERCASE.
        4. If a word is a compound word or has a hyphen, keep it as one token if it's impactful.
        
        Title: "{title}"
        
        Output example: CHEATING, BETRAYED, DISGUSTING, MOM
        """

        try:
            # We use a wrap in a thread or just run if it's sync-compatible
            # generate_content is generally synchronous in the current SDK but we treat it carefully
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return []
                
            text = response.text.strip()
            # Clean up potential markdown or extra text
            text = re.sub(r'[^A-Z0-9,\s\-]', '', text.upper())
            keywords = [k.strip() for k in text.split(',') if k.strip()]
            
            logger.info(f"Gemini extracted keywords for '{title[:30]}...': {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return []

# Singleton instance
keyword_extractor = GeminiKeywordExtractor()
