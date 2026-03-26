"""
Reddit Image Generator for creating visual hooks using Playwright and Jinja2.
Generates high-quality Reddit post overlays for video intros with transparent backgrounds.
Uses Jinja2 templates and Playwright for pixel-perfect rendering.
"""

import logging
import tempfile
import re
import asyncio
import math
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import base64
import hashlib
import time
import json

# Configure logging
logger = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    logger.warning("jinja2 not available. Install with: pip install jinja2")
    JINJA2_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("playwright not available. Install with: pip install playwright")
    PLAYWRIGHT_AVAILABLE = False


class RedditImageGenerator:
    """Generates Reddit post overlay images using Playwright and Jinja2 templates."""
    
    # viral/emotional words to highlight automatically (Heuristic fallback)
    POWER_KEYWORDS = {
        'AITA', 'ASSHOLE', 'MOM', 'BROTHER', 'SAVINGS', 'REFUSING', 'DEMANDED', 
        'TOOK', 'LEFT', 'MONEY', 'HOUSE', 'WIFE', 'UPDATE', 'ILLEGAL', 'CAUGHT',
        'DAUGHTER', 'SON', 'SISTER', 'HUSBAND', 'CHEATING', 'DIVORCE', 'MARRIAGE',
        'WEDDING', 'PREGNANT', 'BABY', 'IN-LAWS', 'MIL', 'FIL', 'SIL', 'BIL',
        'STOLE', 'LIAR', 'LYING', 'SECRET', 'HIDDEN', 'CRAZY', 'INSANE', 'RUINED',
        'KICKED', 'OUT', 'EMERGENCY', 'HOSPITAL', 'POLICE', 'ARRESTED', 'LAWSUIT',
        'SCAM', 'GHOSTED', 'BLOCKED', 'ABUSE', 'TOXIC', 'RED', 'FLAG', 'FLAGS',
        'SCREAMED', 'BETRAYED', 'HORRIFIC', 'TERRIBLE', 'AWFUL', 'DISGUSTING',
        'AFRAID', 'SCARED', 'THREATENED', 'VIOLENT', 'MURDER', 'CRIME', 'STOLEN',
        'WEALTHY', 'RICH', 'POOR', 'DEBT', 'FIRED', 'JOB', 'PROMOTED', 'BOSS'
    }

    # Common "weak" words that should NEVER be highlighted (even if in ALL CAPS)
    WEAK_WORDS = {
        'THE', 'AND', 'FOR', 'THAT', 'THIS', 'WITH', 'FROM', 'HAVE', 'WAS', 'ARE',
        'YOU', 'SHE', 'THEY', 'THEIR', 'WHAT', 'WHO', 'WHICH', 'WHEN', 'WHERE',
        'WILL', 'WOULD', 'COULD', 'SHOULD', 'ABOUT', 'THEN', 'THAN', 'JUST', 
        'LIKE', 'SOME', 'THEM', 'BEING', 'BEEN', 'HERE', 'THERE', 'ONCE', 'THROUGH'
    }

    def __init__(self, output_dir: Optional[Path] = None, template_dir: Optional[Path] = None):
        """
        Initialize Reddit image generator with Playwright and Jinja2.
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "reddit_overlays"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates"
        self.template_dir = template_dir
        
        self.jinja_env = None
        if JINJA2_AVAILABLE and self.template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"Jinja2 environment initialized with template directory: {self.template_dir}")
        else:
            logger.warning(f"Jinja2 not available or template directory not found: {self.template_dir}")
        
        self._browser = None
        self._playwright = None
        self._playwright_context = None
        
        logger.info(f"RedditImageGenerator initialized with output directory: {self.output_dir}")
    
    async def _ensure_playwright_initialized(self):
        """Initialize Playwright browser if not already done."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available. Install with: pip install playwright")
        
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--disable-web-security', '--no-sandbox', '--disable-dev-shm-usage', '--disable-setuid-sandbox']
            )
            self._playwright_context = await self._browser.new_context(
                viewport={'width': 1080, 'height': 1920},
                device_scale_factor=2.0,
            )
            logger.debug("Playwright browser initialized")
    
    async def _close_playwright(self):
        """Close Playwright browser if open."""
        if self._playwright_context:
            await self._playwright_context.close()
            self._playwright_context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    def _format_score(self, score: Union[int, str]) -> str:
        if isinstance(score, str): return score
        if score >= 1000000: return f"{score/1000000:.1f}M"
        elif score >= 1000: return f"{score/1000:.1f}K"
        return str(score)
    
    def _format_comments(self, comments: Union[int, str]) -> str:
        if isinstance(comments, str): return comments
        if comments >= 1000000: return f"{comments/1000000:.1f}M"
        elif comments >= 1000: return f"{comments/1000:.1f}K"
        return str(comments)
    
    def _get_time_ago(self) -> str:
        import random
        return random.choice(["5h ago", "3h ago", "8h ago", "1d ago", "2d ago", "1w ago"])
    
    def _apply_highlights(self, text: str, custom_keywords: Optional[List[str]] = None) -> str:
        """
        Apply red highlights to dramatic words.
        If custom_keywords is provided (from Gemini), they take precedence.
        """
        if not text:
            return text

        active_power_keywords = set(k.upper() for k in custom_keywords) if custom_keywords else self.POWER_KEYWORDS
        is_ai_mode = bool(custom_keywords)

        pattern = re.compile(r'(\b[\w\-\']+\b)([^\w\s]*)', re.UNICODE)
        scored_tokens = []
        parts = re.split(r'(\s+)', text)
        
        for part in parts:
            if not part.strip():
                scored_tokens.append((part, False, 0, ""))
                continue
                
            match = pattern.search(part)
            if not match:
                scored_tokens.append((part, False, 0, ""))
                continue
                
            full_word = match.group(1)
            punctuation = match.group(2)
            
            clean_word = re.sub(r"\'s$", "", full_word, flags=re.IGNORECASE).upper()
            base_clean = re.sub(r'[^\w]', '', clean_word)
            
            importance = 0
            is_power = clean_word in active_power_keywords or base_clean in active_power_keywords
            is_all_caps = full_word.isupper() and len(re.sub(r'[^a-zA-Z]', '', full_word)) >= 2
            
            is_weak = clean_word in self.WEAK_WORDS or len(full_word) <= 2
            if is_power and len(full_word) >= 3:
                is_weak = False
            
            is_candidate = (is_power or is_all_caps) and not is_weak
            if is_candidate:
                importance += 5 if is_power else 2
                importance += 1 if is_all_caps else 0
                importance += min(len(full_word) // 2, 3)
            
            scored_tokens.append((full_word, is_candidate, importance, punctuation))

        candidates = [t for t in scored_tokens if t[1]]
        if is_ai_mode:
            max_highlights = len(candidates)
        else:
            max_highlights = max(2, min(len(candidates), 4, len(scored_tokens) // 4))
        
        top_scores = sorted([t[2] for t in candidates], reverse=True)[:max_highlights]
        min_importance = top_scores[-1] if top_scores else 999
        
        result_parts = []
        highlight_count = 0
        for token_text, is_candidate, importance, punctuation in scored_tokens:
            if is_candidate and importance >= min_importance and highlight_count < max_highlights:
                result_parts.append(f'<span class="highlight">{token_text}</span>{punctuation}')
                highlight_count += 1
            else:
                result_parts.append(f'{token_text}{punctuation}')
                
        return "".join(result_parts)

    async def generate_reddit_post_image(
        self,
        title: str,
        subreddit: str,
        score: int,
        author: Optional[str] = None,
        flair: Optional[str] = None,
        comments: Optional[int] = None,
        theme_mode: str = "dark",
        body: Optional[str] = None,
        output_path: Optional[Path] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> Optional[Path]:
        try:
            if not title or not subreddit:
                logger.error("Title and subreddit are required")
                return None
            
            author_display = author or "Anonymous"
            comments_display = comments or max(score // 10, 1)
            highlighted_title = self._apply_highlights(title, custom_keywords=custom_keywords)
            
            avatar_base64 = ""
            profile_pic_path = self.template_dir / "channels_profile.jpg"
            if profile_pic_path.exists():
                try:
                    with open(profile_pic_path, "rb") as img_file:
                        avatar_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                except Exception: pass
            
            template_data = {
                "title": highlighted_title,
                "subreddit": subreddit,
                "author": author_display,
                "flair": flair,
                "score": score,
                "formatted_score": self._format_score(score),
                "comments": comments_display,
                "formatted_comments": self._format_comments(comments_display),
                "time_ago": self._get_time_ago(),
                "theme_mode": theme_mode,
                "body": body,
                "avatar_base64": avatar_base64,
            }
            
            html_content = self.jinja_env.get_template("reddit_post.html").render(**template_data)
            
            if output_path is None:
                content_hash = hashlib.md5(f"{title}{subreddit}".encode()).hexdigest()[:8]
                output_path = self.output_dir / f"reddit_post_{content_hash}_{int(time.time())}.png"
            
            await self._ensure_playwright_initialized()
            page = await self._playwright_context.new_page()
            
            try:
                await page.set_content(html_content, wait_until="networkidle")
                await page.wait_for_timeout(300)
                card_element = await page.query_selector('.post-card')
                
                if not card_element:
                    await page.screenshot(path=str(output_path), type='png', omit_background=True)
                else:
                    box = await card_element.bounding_box()
                    if box:
                        padding = 20
                        clip = {'x': box['x'] - padding, 'y': box['y'] - padding, 'width': box['width'] + (padding * 2), 'height': box['height'] + (padding * 2)}
                        await page.screenshot(path=str(output_path), type='png', omit_background=True, clip=clip)
                    else:
                        await page.screenshot(path=str(output_path), type='png', omit_background=True)
                
                return output_path if output_path.exists() else None
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"Failed to generate Reddit post image: {e}")
            return None
    
    def generate_reddit_post_image_sync(self, *args, **kwargs) -> Optional[Path]:
        try:
            return asyncio.run(self.generate_reddit_post_image(*args, **kwargs))
        except Exception as e:
            logger.error(f"Failed in synchronous wrapper: {e}")
            return None
    
    async def cleanup(self):
        await self._close_playwright()
    
    def __del__(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running(): loop.create_task(self.cleanup())
            else: loop.run_until_complete(self.cleanup())
        except: pass


class TitlePopupTimingCalculator:
    def __init__(self, title_audio_duration: float, buffer_seconds: float = 2.0):
        self.title_audio_duration = title_audio_duration
        self.buffer_seconds = buffer_seconds
        self.pop_in_duration = 1.2
        self.display_duration = title_audio_duration + buffer_seconds
        self.card_start_time = 0.0
        self.card_full_visible_time = 0.6
        self.card_end_time = self.card_start_time + self.display_duration
        self.subtitle_start_time = self.card_end_time
    
    def get_ffmpeg_filter_for_animation(self, image_path: Path) -> str:
        TARGET_W = 950
        ANIM_DURATION = 0.6  
        FADE_DURATION = 0.8
        fade_start = self.card_end_time - FADE_DURATION
        filter_str = (
            f"[1:v]scale={TARGET_W}:-1,format=rgba,"
            f"fade=t=in:st={self.card_start_time:.3f}:d={ANIM_DURATION:.1f}:alpha=1,"
            f"fade=t=out:st={fade_start:.3f}:d={FADE_DURATION:.1f}:alpha=1[animated];"
            f"[0:v][animated]overlay=x=(W-w)/2:"
            f"y='min((H-h)/3 + 100 - 100*min(max(t-{self.card_start_time:.3f},0)/{ANIM_DURATION:.3f},1), (H-h)/3)':"
            f"enable='between(t,{self.card_start_time:.2f},{self.card_end_time:.2f})'"
        )
        return filter_str
    
    def to_dict(self) -> dict:
        return {
            "title_audio_duration": self.title_audio_duration,
            "buffer_seconds": self.buffer_seconds,
            "pop_in_duration": self.pop_in_duration,
            "display_duration": self.display_duration,
            "card_start_time": self.card_start_time,
            "card_full_visible_time": self.card_full_visible_time,
            "card_end_time": self.card_end_time,
            "subtitle_start_time": self.subtitle_start_time,
        }


class LegacyRedditImageGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.generator = RedditImageGenerator(output_dir)
    def generate_reddit_post_image(self, *args, **kwargs) -> Optional[Path]:
        return self.generator.generate_reddit_post_image_sync(*args, **kwargs)
