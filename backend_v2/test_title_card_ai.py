
import asyncio
import logging
import os
from pathlib import Path
from reddit_story.reddit_client import RedditClient
from reddit_story.keyword_extractor import keyword_extractor
from reddit_story.image_generator_new import RedditImageGenerator
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_title_card_generation():
    """
    Test script to verify Title Card generation with AI-powered keyword highlighting.
    This script will:
    1. Fetch a random trending story from Reddit.
    2. Use Gemini Flash to extract high-impact keywords.
    3. Generate a title card PNG with red highlights on those keywords.
    """
    
    print("\n" + "="*50)
    print("🚀 STARTING TITLE CARD AI TEST")
    print("="*50 + "\n")

    # 1. Initialize Reddit Client and fetch a story
    async with RedditClient() as reddit:
        logger.info("Fetching trending stories from Reddit...")
        stories = await reddit.fetch_trending_stories(
            subreddit=["AmItheAsshole", "tifu", "TrueOffMyChest"],
            limit=5,
            time_filter="day",
            min_score=50,
            exclude_processed=False 
        )
        
        if not stories:
            logger.warning("No stories found on Reddit, using fallback title.")
            title = "AITA for telling my toxic MIL that she is RUINING our wedding?"
            subreddit = "AmItheAsshole"
            score = 12500
            author = "TestUser123"
        else:
            story = stories[0]
            title = story.title
            subreddit = story.subreddit
            score = story.score
            author = story.author or "Anonymous"
            logger.info(f"Selected Story: {title}")

    # 2. Extract Keywords using Gemini
    ai_keywords = []
    if settings.use_gemini_keywords:
        logger.info("Extracting keywords using Gemini Flash...")
        ai_keywords = await keyword_extractor.extract_keywords(title)
        print(f"✨ AI EXTRACTED KEYWORDS: {ai_keywords}")
    else:
        logger.warning("GEMINI_API_KEY not set. Using heuristic fallback for highlighting.")

    # 3. Generate the Image
    output_dir = Path("backend_v2/outputs/tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_title_card_ai.png"
    
    generator = RedditImageGenerator(output_dir=output_dir)
    
    logger.info("Generating Title Card image...")
    result = await generator.generate_reddit_post_image(
        title=title,
        subreddit=subreddit,
        score=score,
        author=author,
        theme_mode="dark",
        output_path=output_path,
        custom_keywords=ai_keywords
    )
    
    if result and result.exists():
        print("\n" + "="*50)
        print("✅ TEST SUCCESSFUL!")
        print(f"Title: {title}")
        print(f"Result Image: {result.absolute()}")
        print("="*50 + "\n")
    else:
        logger.error("❌ Failed to generate title card.")

    await generator.cleanup()

if __name__ == "__main__":
    # Ensure we are in the correct directory context if run from root
    import sys
    backend_path = Path(__file__).parent
    if str(backend_path) not in sys.path:
        sys.path.append(str(backend_path))
        
    asyncio.run(test_title_card_generation())
