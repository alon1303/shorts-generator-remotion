import asyncio
import os
import sys
import shutil
import math
import json
import logging
from pathlib import Path
from reddit_story.reddit_client import RedditClient
from reddit_story.story_processor import StoryProcessor
from reddit_story.tts_router import generate_title_and_story_audio, get_tts_client
from reddit_story.image_generator_new import RedditImageGenerator
from config.settings import settings

import subprocess

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def render_video(output_dir: Path):
    logger.info("Starting Remotion rendering process...")
    frontend_dir = Path(__file__).parent.parent / "remotion-frontend"
    handoff_dir = frontend_dir / "public" / "current_render"
    
    # 1. Clear and create handoff folder
    if handoff_dir.exists():
        shutil.rmtree(handoff_dir)
    handoff_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Copy assets
    for file_name in ["audio.mp3", "background.mp4", "composition_data.json"]:
        src_file = output_dir / file_name
        if src_file.exists():
            shutil.copy2(src_file, handoff_dir / file_name)
            
    # 3. Set up command
    out_file = frontend_dir / "out" / "final_video.mp4"
    if out_file.exists():
        out_file.unlink()
        
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    cmd = [npx_cmd, "remotion", "render", "src/index.ts", "RedditShort", "out/final_video.mp4"]
    
    logger.info(f"Executing: {' '.join(cmd)} inside {frontend_dir.resolve()}")
    
    # 4. Execute Remotion
    process = subprocess.Popen(
        cmd,
        cwd=str(frontend_dir.resolve()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8"
    )
    
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        
    process.wait()
    
    if process.returncode != 0:
        logger.error("Remotion rendering failed.")
        sys.exit(1)
        
    # 5. Move back to output dir
    final_dest = output_dir / "final_video.mp4"
    if out_file.exists():
        shutil.move(str(out_file), str(final_dest))
        logger.info(f"✅ Video successfully rendered and saved to {final_dest}")
    else:
        logger.error("Remotion finished successfully, but output file not found.")
        sys.exit(1)

async def run_cached_export_pipeline(config: dict):
    logger.info("Starting Multi-Part Cache Pipeline Execution...")
    
    title_text = config["title_text"]
    title_id = config["title_id"]
    num_parts = config["num_parts"]
    parts_map = config["parts"]
    
    voices_dir = Path("cache") / "elevenlabs" / "voices"
    
    # Optimization: Extract keywords ONCE
    processor = StoryProcessor()
    logger.info(f"Extracting keywords for title: {title_text}")
    keywords = await processor._extract_power_words_single(title_text)
    logger.info(f"Extracted keywords: {keywords}")
    
    title_mp3_path = voices_dir / f"{title_id}.mp3"
    title_json_path = voices_dir / f"{title_id}.json"
    
    if not title_mp3_path.exists() or not title_json_path.exists():
        logger.error(f"Cache ID not found in cache/elevenlabs/voices: {title_id}")
        sys.exit(1)
    
    for i in range(1, num_parts + 1):
        part_key = f"Part {i}"
        part_id = parts_map[part_key]
        
        logger.info(f"--- Processing {part_key} ---")
        output_dir = Path(f"output_assets/cached_story/part_{i}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Title Formatting
        if i == 1:
            title_card_text = title_text
        else:
            title_card_text = f"{title_text} (Part {i})"
            
        # 2. Audio & Timing Merge
        part_mp3_path = voices_dir / f"{part_id}.mp3"
        part_json_path = voices_dir / f"{part_id}.json"
        
        if not part_mp3_path.exists() or not part_json_path.exists():
            logger.error(f"Cache ID not found in cache/elevenlabs/voices: {part_id}")
            sys.exit(1)
        
        # Read JSONs
        with open(title_json_path, "r") as f:
            title_words = json.load(f)
        with open(part_json_path, "r") as f:
            part_words = json.load(f)
            
        # Merge Audio (Binary Append)
        final_audio_path = output_dir / "audio.mp3"
        with open(final_audio_path, "wb") as f_out:
            with open(title_mp3_path, "rb") as f_in1:
                f_out.write(f_in1.read())
            with open(part_mp3_path, "rb") as f_in2:
                f_out.write(f_in2.read())
                
        # Merge Timestamps
        # Determine title duration by looking at the last word's end time, plus a small buffer
        title_duration = title_words[-1]["end"] + 0.5 if title_words else 0.0
        
        merged_words = []
        for w in title_words:
            merged_words.append({
                "word": w["word"],
                "startFrame": math.floor(w["start"] * 30),
                "endFrame": math.floor(w["end"] * 30)
            })
            
        for w in part_words:
            merged_words.append({
                "word": w["word"],
                "startFrame": math.floor((w["start"] + title_duration) * 30),
                "endFrame": math.floor((w["end"] + title_duration) * 30)
            })
            
        # Total duration in frames
        total_duration_seconds = part_words[-1]["end"] + title_duration if part_words else title_duration
        total_duration_frames = math.floor(total_duration_seconds * 30)
        
        # Select Background
        background_dest = output_dir / "background.mp4"
        original_bg_dir = Path("../backend_v2/assets/backgrounds/minecraft")
        real_bgs = list(original_bg_dir.glob("*.mp4")) if original_bg_dir.exists() else []
        fallback_bg = Path("../backend_v2/production_preview.mp4")
        if real_bgs:
            shutil.copy2(real_bgs[0], background_dest)
        elif fallback_bg.exists():
            shutil.copy2(fallback_bg, background_dest)
        else:
            with open(background_dest, "w") as f:
                f.write("dummy background video content")
                
        # Create composition_data.json
        composition_data = {
            "assets": {
                "audio": "audio.mp3",
                "background": "background.mp4"
            },
            "metadata": {
                "fps": 30,
                "duration_frames": total_duration_frames
            },
            "titleCardData": {
                "titleText": title_card_text,
                "subreddit": "r/RedditStories",
                "author": "u/RedditUser",
                "upvotes": "15K",
                "keywords": keywords
            },
            "words": merged_words
        }
        
        json_path = output_dir / "composition_data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(composition_data, f, indent=2)
            
        logger.info(f"✅ Part {i} Data Export Complete! Output saved to {output_dir}")
        render_video(output_dir)

async def run_export_pipeline(url: str):
    logger.info(f"Starting export pipeline for URL: {url}")
    
    # 1. Create output directory
    output_dir = Path("output_assets/test_story")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Fetch Reddit Story
    logger.info("Fetching Reddit story...")
    client = RedditClient()
    
    if url:
        story = await client.fetch_story_from_url(url)
    else:
        logger.info("No URL provided. Fetching trending story...")
        stories = await client.fetch_trending_stories(limit=1)
        story = stories[0] if stories else None
        
    if not story:
        logger.error(f"CRITICAL: Failed to fetch Reddit story. No valid data returned.")
        sys.exit(1)
        
    # 3. Process Text
    print("Processing text...")
    processor = StoryProcessor()
    processed_story = await processor.process_story(story)
    
    # 4. Generate TTS
    print("Generating TTS...")
    # For simplicity, we just generate the title and first part
    title = processed_story.story.title
    story_chunks = [processed_story.parts[0].text] if processed_story.parts else ["This is a test story body."]
    
    title_audio_path, story_audio_chunks, story_start_time, timing_data = await generate_title_and_story_audio(
        title=title,
        story_text_chunks=story_chunks,
        voice="en-US-ChristopherNeural",
        engine="edge"
    )
    
    # 5. Generate Title Card (Skipped - now handled by Remotion)
    print("Skipping static Title Card generation (handled by Frontend)...")
    
    # 6. Select Background (Mocking this by finding any mp4 or creating a dummy file)
    print("Selecting background...")
    background_dest = output_dir / "background.mp4"
    # Try to find a real background in the original backend_v2 assets
    original_bg_dir = Path("../backend_v2/assets/backgrounds/minecraft")
    real_bgs = list(original_bg_dir.glob("*.mp4")) if original_bg_dir.exists() else []
    fallback_bg = Path("../backend_v2/production_preview.mp4")
    if real_bgs:
        shutil.copy2(real_bgs[0], background_dest)
    elif fallback_bg.exists():
        shutil.copy2(fallback_bg, background_dest)
    else:
        # Create a dummy file if no real background is found
        with open(background_dest, "w") as f:
            f.write("dummy background video content")
            
    # Copy audio files to output dir
    final_title_audio = output_dir / "title_audio.mp3"
    final_story_audio = output_dir / "story_audio.mp3"
    shutil.copy2(title_audio_path, final_title_audio)
    shutil.copy2(story_audio_chunks[0].audio_path, final_story_audio)
    
    # 7. Generate Data Contract (composition_data.json)
    print("Generating Data Contract...")
    FPS = 30
    
    # Convert timestamps to frames
    words_data = []
    
    # We need to fetch the raw title timestamps from the tts_router again or just re-generate them, 
    # but since tts_router combined them into story_audio_chunks in our previous step (wait, did it?),
    # Let's just generate TTS for the whole text to make it one simple list of words.
    
    # Actually, let's use a simpler approach to get a clean list of words.
    router = await get_tts_client(engine="edge")
    full_text = f"{title}. {story_chunks[0]}"
    audio_path, duration, word_timestamps = await router.text_to_speech_with_timestamps(text=full_text, voice="en-US-ChristopherNeural")
    
    # Copy this single audio file as audio.mp3
    final_audio = output_dir / "audio.mp3"
    shutil.copy2(audio_path, final_audio)
    
    if word_timestamps:
        for ts in word_timestamps:
            words_data.append({
                "word": ts.word,
                "startFrame": math.floor(ts.start * FPS),
                "endFrame": math.floor(ts.end * FPS)
            })
            
    composition_data = {
        "assets": {
            "audio": "audio.mp3",
            "background": "background.mp4"
        },
        "metadata": {
            "title": story.title,
            "subreddit": story.subreddit,
            "fps": FPS,
            "duration_frames": math.floor(duration * FPS)
        },
        "titleCardData": {
            "titleText": story.title,
            "subreddit": f"r/{story.subreddit}",
            "author": f"u/{story.author}",
            "upvotes": str(story.score),
        },
        "words": words_data
    }
    
    json_path = output_dir / "composition_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(composition_data, f, indent=2)
        
    print(f"\n✅ Data Export Complete! Output saved to {output_dir}")
    print("\n--- composition_data.json ---")
    print(json.dumps(composition_data, indent=2))
    
    render_video(output_dir)

def run_interactive():
    print("--- Reddit Shorts Generator ---")
    print("Select Data Source:")
    print(" [1] Process a new Reddit Post (URL or Trending)")
    print(" [2] Generate from Local Cache")
    print(" [3] Quick Test Run (Hardcoded Cache)")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        url_input = input("Enter a valid Reddit URL (or press Enter to fetch a trending story): ").strip()
        asyncio.run(run_export_pipeline(url_input if url_input else None))
    elif choice in ["2", "3"]:
        if choice == "2":
            print("\n--- Manual Cache Assembly ---")
            title_id = input("Enter the Cache ID for the Title TTS audio: ").strip()
        else:
            print("\n--- Quick Test Run ---")
            title_id = "145190f2f1cb57e7eb2882d6dcc8ff03_1774104704"
        
        voices_dir = Path("cache") / "elevenlabs" / "voices"
        title_json_path = voices_dir / f"{title_id}.json"
        
        if not title_json_path.exists():
            print(f"ERROR: Cache ID not found in cache/elevenlabs/voices: {title_id}")
            sys.exit(1)
            
        # Parse JSON to extract the title string automatically
        with open(title_json_path, "r", encoding="utf-8") as f:
            title_data = json.load(f)
            
        if isinstance(title_data, list) and len(title_data) > 0 and "word" in title_data[0]:
            title_text = " ".join([w["word"] for w in title_data])
        else:
            title_text = "Fallback Extracted Title"
            
        print(f"\n✅ Extracted Story Title from JSON: '{title_text}'\n")
        
        if choice == "2":
            try:
                num_parts = int(input("Enter the total number of parts (e.g., 1, 2, 3): ").strip())
            except ValueError:
                print("Invalid number of parts. Must be an integer. Exiting.")
                sys.exit(1)
                
            parts = {}
            for i in range(1, num_parts + 1):
                part_id = input(f"Enter Cache ID for Part {i}: ").strip()
                parts[f"Part {i}"] = part_id
        else:
            num_parts = 1
            parts = {"Part 1": "fb5d425957ddf905b37d946b8e0cb529_1774104711"}
            
        cache_config = {
            "title_text": title_text,
            "title_id": title_id,
            "num_parts": num_parts,
            "parts": parts
        }
        
        print("\n--- Collected Configuration ---")
        for k, v in cache_config.items():
            print(f"{k}: {v}")
            
        print("\nConfiguration confirmed. Executing cached pipeline...")
        asyncio.run(run_cached_export_pipeline(cache_config))
        sys.exit(0)
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    run_interactive()
