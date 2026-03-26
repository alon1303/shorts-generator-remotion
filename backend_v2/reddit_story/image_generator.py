"""
Reddit Image Generator for creating visual hooks.
Generates light-mode Reddit post overlays for video intros.
Uses html2image for HTML-to-image rendering.
"""

import logging
import tempfile
import re
from pathlib import Path
from typing import Optional, List
import base64

# Configure logging
logger = logging.getLogger(__name__)

try:
    from html2image import Html2Image
    HTML2IMAGE_AVAILABLE = True
except ImportError:
    logger.warning("html2image not available. Install with: pip install html2image")
    HTML2IMAGE_AVAILABLE = False


class RedditImageGenerator:
    """Generates Reddit post overlay images using html2image."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize Reddit image generator.
        
        Args:
            output_dir: Directory to save generated images (defaults to temp directory)
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "reddit_overlays"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if HTML2IMAGE_AVAILABLE:
            # Initialize Html2Image with Chrome/Chromium
            self.hti = Html2Image(
                browser='chrome',
                output_path=str(self.output_dir),
                size=(1080, 400),  # Width matches Shorts width, height for post
            )
            logger.info(f"RedditImageGenerator initialized with output directory: {self.output_dir}")
        else:
            self.hti = None
            logger.warning("RedditImageGenerator initialized without html2image - will use text file fallback")
    
    def _generate_reddit_post_html(
        self,
        title: str,
        subreddit: str,
        score: int,
        author: Optional[str] = None,
        flair: Optional[str] = None
    ) -> str:
        """
        Generate HTML for a light-mode Reddit post.
        
        Args:
            title: Post title
            subreddit: Subreddit name
            score: Upvote count
            author: Post author (optional)
            flair: Post flair (optional)
            
        Returns:
            HTML string for the Reddit post
        """
        # Format score with K/M suffix if large
        def format_score(num: int) -> str:
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        formatted_score = format_score(score)
        author_display = author or "Anonymous"
        
        # Reddit light mode colors
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    background: transparent;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    padding: 20px;
                }
                
                .reddit-post {
                    background: #FFFFFF;
                    border: 3px solid #FF4500;
                    border-radius: 12px;
                    width: 1000px;
                    max-width: 90vw;
                    padding: 24px;
                    box-shadow: 0 15px 50px rgba(0, 0, 0, 0.6);
                    position: relative;
                    overflow: hidden;
                }
                
                .post-header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 16px;
                }
                
                .subreddit-icon {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    margin-right: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .subreddit-name {
                    color: #1C1C1C;
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .post-meta {
                    color: #787C7E;
                    font-size: 12px;
                    margin-left: 8px;
                }
                
                .post-title {
                    color: #222222;
                    font-size: 36px;
                    font-weight: 800;
                    line-height: 1.3;
                    margin-bottom: 20px;
                    word-wrap: break-word;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
                }
                
                .post-footer {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding-top: 16px;
                    border-top: 1px solid #EDEFF1;
                }
                
                .upvote-section {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .upvote-icon {
                    width: 24px;
                    height: 24px;
                    background: #FF4500;
                    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 4.5L7.5 9.5H10V14H14V9.5H16.5L12 4.5Z'/%3E%3C/svg%3E") no-repeat center;
                    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 4.5L7.5 9.5H10V14H14V9.5H16.5L12 4.5Z'/%3E%3C/svg%3E") no-repeat center;
                }
                
                .upvote-count {
                    color: #FF4500;
                    font-weight: 700;
                    font-size: 18px;
                }
                
                .author-section {
                    color: #787C7E;
                    font-size: 14px;
                }
                
                .flair {
                    display: inline-block;
                    background: #EDEFF1;
                    color: #1C1C1C;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                    margin-left: 12px;
                }
                
                @media (max-width: 600px) {
                    .post-title {
                        font-size: 22px;
                    }
                    
                    .reddit-post {
                        padding: 20px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="reddit-post">
                <div class="post-header">
                    <img class="subreddit-icon" src="https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-57x57.png" alt="Reddit Logo">
                    <div>
                        <span class="subreddit-name">r/{subreddit}</span>
                        <span class="post-meta">• Posted by u/{author} • 5h ago</span>
                        {flair_html}
                    </div>
                </div>
                
                <h1 class="post-title">{title}</h1>
                
                <div class="post-footer">
                    <div class="upvote-section">
                        <div class="upvote-icon"></div>
                        <span class="upvote-count">{formatted_score}</span>
                    </div>
                    
                    <div class="author-section">
                        u/{author}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Add flair if provided
        flair_html = f'<span class="flair">{flair}</span>' if flair else ''
        
        # Fill template
        html = html_template.format(
            title=title,
            subreddit=subreddit,
            author=author_display,
            formatted_score=formatted_score,
            flair_html=flair_html
        )
        
        return html
    
    def generate_reddit_post_image(
        self,
        title: str,
        subreddit: str,
        score: int,
        author: Optional[str] = None,
        flair: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Generate a Reddit post overlay image.
        
        Args:
            title: Post title
            subreddit: Subreddit name
            score: Upvote count
            author: Post author (optional)
            flair: Post flair (optional)
            output_path: Optional output path for the image
            
        Returns:
            Path to generated PNG image, or None if failed
        """
        try:
            # Generate HTML
            html_content = self._generate_reddit_post_html(
                title=title,
                subreddit=subreddit,
                score=score,
                author=author,
                flair=flair
            )
            
            # Generate filename
            if output_path is None:
                import hashlib
                import time
                content_hash = hashlib.md5(f"{title}{subreddit}{score}".encode()).hexdigest()[:8]
                timestamp = int(time.time())
                filename = f"reddit_post_{content_hash}_{timestamp}.png"
                output_path = self.output_dir / filename
            
            if HTML2IMAGE_AVAILABLE and self.hti:
                # Use html2image to generate PNG
                logger.info(f"Generating Reddit post image: {title[:50]}...")
                
                # Save HTML to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    html_file = f.name
                
                try:
                    # Generate image
                    self.hti.screenshot(
                        html_file=html_file,
                        save_as=output_path.name,
                        size=(1080, 400)
                    )
                    
                    # Check if file was created
                    if output_path.exists():
                        logger.info(f"Reddit post image generated: {output_path}")
                        return output_path
                    else:
                        logger.error(f"Failed to generate image: {output_path}")
                        return None
                        
                finally:
                    # Clean up HTML file
                    import os
                    if os.path.exists(html_file):
                        os.unlink(html_file)
                        
            else:
                # html2image not available, create text file fallback
                logger.warning("html2image not available, creating text file")
                return self._generate_text_file_fallback(
                    title=title,
                    subreddit=subreddit,
                    score=score,
                    author=author,
                    output_path=output_path
                )
                
        except Exception as e:
            logger.error(f"Failed to generate Reddit post image: {e}")
            return None
    
    def _generate_text_file_fallback(
        self,
        title: str,
        subreddit: str,
        score: int,
        author: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Fallback method to generate a text file when no image generation is available.
        
        Args:
            title: Post title
            subreddit: Subreddit name
            score: Upvote count
            author: Post author (optional)
            output_path: Output path for the text file
            
        Returns:
            Path to generated text file
        """
        if output_path is None:
            output_path = self.output_dir / f"reddit_info_{hash(title) % 10000}.txt"
        
        text_content = f"""Reddit Post Info (Image generation failed)
========================================
Title: {title}
Subreddit: r/{subreddit}
Upvotes: {score}
Author: {author or 'Anonymous'}

Note: Install html2image for proper image generation: pip install html2image
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.warning(f"Created text file instead of image: {output_path}")
        return output_path
    
    def cleanup_old_images(self, max_age_hours: int = 24) -> int:
        """
        Clean up old generated images.
        
        Args:
            max_age_hours: Maximum age of images in hours
            
        Returns:
            Number of files deleted
        """
        import time
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filepath in self.output_dir.glob("*.*"):
            try:
                file_age = current_time - filepath.stat().st_mtime
                
                if file_age > max_age_seconds:
                    filepath.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old image: {filepath}")
                    
            except Exception as e:
                logger.warning(f"Failed to delete image {filepath}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old Reddit post images")
        
        return deleted_count


class TitlePopupTimingCalculator:
    """Calculates timing for title popup animation and display."""
    
    def __init__(self, title_audio_duration: float, buffer_seconds: float = 0.0):
        """
        Initialize timing calculator.
        
        Args:
            title_audio_duration: Duration of title audio in seconds
            buffer_seconds: Additional buffer after audio ends (default: 0.0s)
        """
        self.title_audio_duration = title_audio_duration
        self.buffer_seconds = buffer_seconds
        
        # Animation parameters
        self.pop_in_duration = 0.2  # seconds for scale animation
        self.display_duration = title_audio_duration  # Card disappears exactly when title audio ends
        
        # Calculate key timing points
        self.card_start_time = 0.0
        self.card_full_visible_time = self.pop_in_duration
        self.card_end_time = self.card_start_time + self.display_duration
        self.subtitle_start_time = self.card_end_time  # Subtitles start after card disappears (when story starts)
        
        logger.info(
            f"Timing calculated: "
            f"Title audio: {title_audio_duration:.2f}s, "
            f"Display: {self.display_duration:.2f}s, "
            f"Card visible: {self.card_start_time:.2f}s to {self.card_end_time:.2f}s, "
            f"Subtitles start: {self.subtitle_start_time:.2f}s"
        )
    
    def get_ffmpeg_filter_for_animation(self, image_path: Path) -> str:
        # Target width is 900px. We calculate height maintaining aspect ratio (ih/iw).
        # We scale from 1px to 900px over `pop_in_duration` seconds to create a pop-in effect.
        
        filter_str = (
            f"[1:v]scale=w='max(1, min(900, 900*(t-{self.card_start_time})/{self.pop_in_duration}))':"
            f"h='max(1, min(900*ih/iw, 900*ih/iw*(t-{self.card_start_time})/{self.pop_in_duration}))':"
            f"eval=frame[overlay_scaled];"
            f"[0:v][overlay_scaled]overlay=x=(W-w)/2:y=(H-h)/2:"
            f"enable='between(t,{self.card_start_time},{self.card_end_time})'"
        )
        return filter_str
    
    def to_dict(self) -> dict:
        """Return timing data as dictionary."""
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


# Example usage
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test html2image-based generator
    print("Testing html2image-based RedditImageGenerator...")
    html_generator = RedditImageGenerator()
    
    test_output = Path(tempfile.gettempdir()) / "test_html_image.png"
    result = html_generator.generate_reddit_post_image(
        title="Another test question for the community",
        subreddit="AskReddit",
        score=12500,
        author="TestUser123",
        flair="Serious",
        output_path=test_output
    )
    
    if result and result.exists():
        print(f"✅ HTML image generated: {result}")
        print(f"   File size: {result.stat().st_size} bytes")
        # Clean up
        result.unlink()
    else:
        print("❌ HTML image generation failed or not available")
    
    # Test timing calculator
    print("\nTesting TitlePopupTimingCalculator...")
    timing_calc = TitlePopupTimingCalculator(title_audio_duration=3.5)
    timing_data = timing_calc.to_dict()
    print(f"Timing data: {timing_data}")
    
    print("\nAll tests completed!")
