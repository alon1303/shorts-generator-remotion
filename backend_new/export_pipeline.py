import asyncio
import os
import sys
import shutil
import math
import json
import logging
import random
from pathlib import Path
from reddit_story.reddit_client import RedditClient
from reddit_story.story_processor import StoryProcessor
from reddit_story.tts_router import generate_title_and_story_audio, get_tts_client
from reddit_story.image_generator_new import RedditImageGenerator
from config.settings import settings

import subprocess

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_background_clips(total_duration_frames: int, output_dir: Path) -> list:
    """
    Builds the backgrounds array and prepares the files in output_dir.
    Renames clips sequentially to bg_0.mp4, bg_1.mp4, etc.
    """
    # Base backgrounds directory
    bg_base_dir = Path("../backend_v2/assets/backgrounds")
    if not bg_base_dir.exists():
        bg_base_dir = Path("assets/backgrounds")
    
    # Recursively find all mp4 files in all subdirectories
    available_bgs = list(bg_base_dir.rglob("*.mp4")) if bg_base_dir.exists() else []
    
    if available_bgs:
        logger.info(f"Found {len(available_bgs)} background videos in {bg_base_dir}")
    else:
        logger.warning(f"No background videos found in {bg_base_dir}")

    backgrounds_data = []
    current_frame = 0
    bg_index = 0
    
    # Create backgrounds subdirectory in output_dir
    output_bg_dir = output_dir / "backgrounds"
    output_bg_dir.mkdir(parents=True, exist_ok=True)

    # Fallback bg if no bgs available
    fallback_bg = Path("../backend_v2/production_preview.mp4")

    while current_frame < total_duration_frames:
        if not available_bgs:
            # Use real fallback if no bgs available
            dummy_name = f"bg_{bg_index}.mp4"
            if fallback_bg.exists():
                shutil.copy2(fallback_bg, output_bg_dir / dummy_name)
            else:
                # If even fallback is missing, we must fail or find something.
                # Writing a 1-second black mp4 with ffmpeg would be safer, but let's assume production_preview exists.
                logger.error("No background videos found and no production_preview.mp4 fallback!")
                # Last resort: copy ANY mp4 in the project if one exists, else this will crash remotion
            
            duration_frames = total_duration_frames - current_frame
            backgrounds_data.append({
                "startFrame": current_frame,
                "endFrame": total_duration_frames,
                "backgroundPath": f"backgrounds/{dummy_name}"
            })
            break

        selected_bg = random.choice(available_bgs)
        # 10 to 15 seconds in frames (30 FPS)
        duration_frames = random.randint(300, 450)
        
        # Don't overshoot total duration
        if current_frame + duration_frames > total_duration_frames:
            duration_frames = total_duration_frames - current_frame
            
        new_name = f"bg_{bg_index}.mp4"
        shutil.copy2(selected_bg, output_bg_dir / new_name)
        
        backgrounds_data.append({
            "startFrame": current_frame,
            "endFrame": current_frame + duration_frames,
            "backgroundPath": f"backgrounds/{new_name}"
        })
        
        current_frame += duration_frames
        bg_index += 1
        
    return backgrounds_data

def render_video(output_dir: Path):
    logger.info("Starting Remotion rendering process...")
    frontend_dir = Path(__file__).parent.parent / "remotion-frontend"
    handoff_dir = frontend_dir / "public" / "current_render"
    
    # 1. Clear and create handoff folder
    if handoff_dir.exists():
        shutil.rmtree(handoff_dir)
    handoff_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Copy core assets
    assets_to_copy = ["audio.mp3", "composition_data.json", "lofi_bg.mp3"]
    for file_name in assets_to_copy:
        src_file = output_dir / file_name
        if src_file.exists():
            shutil.copy2(src_file, handoff_dir / file_name)
        elif file_name == "lofi_bg.mp3":
            # Try to find lofi_bg in backend assets if not in output_dir
            backend_assets = Path("assets") / "audio" / "lofi_bg.mp3"
            if backend_assets.exists():
                shutil.copy2(backend_assets, handoff_dir / "lofi_bg.mp3")

    # 3. Copy backgrounds folder
    src_bg_dir = output_dir / "backgrounds"
    if src_bg_dir.exists():
        shutil.copytree(src_bg_dir, handoff_dir / "backgrounds")
            
    # 4. Set up command
    out_file = frontend_dir / "out" / "final_video.mp4"
    if out_file.exists():
        out_file.unlink()
        
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    cmd = [npx_cmd, "remotion", "render", "src/index.ts", "RedditShort", "out/final_video.mp4"]
    
    logger.info(f"Executing: {' '.join(cmd)} inside {frontend_dir.resolve()}")
    
    # 5. Execute Remotion
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
        
    # 6. Move back to output dir
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
        title_duration_frames = math.floor(title_duration * 30)
        
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
        
        # 3. Dynamic Background Selection
        backgrounds_data = get_background_clips(total_duration_frames, output_dir)
                
        # 4. Create composition_data.json
        composition_data = {
            "assets": {
                "audio": "audio.mp3",
                "bg_music": "lofi_bg.mp3"
            },
            "metadata": {
                "title": title_text,
                "subreddit": "r/RedditStories",
                "fps": 30,
                "duration_frames": total_duration_frames,
                "titleDurationFrames": title_duration_frames
            },
            "titleCardData": {
                "titleText": title_card_text,
                "subreddit": "r/RedditStories",
                "author": "u/RedditUser",
                "upvotes": "15K",
                "keywords": keywords
            },
            "backgrounds": backgrounds_data,
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
    title = processed_story.story.title
    story_chunks = [processed_story.parts[0].text] if processed_story.parts else ["This is a test story body."]
    
    # We need keywords for the title
    keywords = await processor._extract_power_words_single(title)
    
    router = await get_tts_client(engine="edge")
    
    # Title only for duration
    title_audio, title_dur, title_words = await router.text_to_speech_with_timestamps(text=title, voice="en-US-ChristopherNeural")
    title_duration_frames = math.floor((title_dur + 0.5) * 30) # 0.5s buffer
    
    full_text = f"{title}. {story_chunks[0]}"
    audio_path, duration, word_timestamps = await router.text_to_speech_with_timestamps(text=full_text, voice="en-US-ChristopherNeural")
    
    # Copy this single audio file as audio.mp3
    final_audio = output_dir / "audio.mp3"
    shutil.copy2(audio_path, final_audio)
    
    FPS = 30
    words_data = []
    if word_timestamps:
        for ts in word_timestamps:
            words_data.append({
                "word": ts.word,
                "startFrame": math.floor(ts.start * FPS),
                "endFrame": math.floor(ts.end * FPS)
            })
            
    total_duration_frames = math.floor(duration * FPS)
    
    # 5. Dynamic Background Selection
    backgrounds_data = get_background_clips(total_duration_frames, output_dir)
            
    # 6. Generate Data Contract (composition_data.json)
    print("Generating Data Contract...")
    
    composition_data = {
        "assets": {
            "audio": "audio.mp3",
            "bg_music": "lofi_bg.mp3"
        },
        "metadata": {
            "title": story.title,
            "subreddit": story.subreddit,
            "fps": FPS,
            "duration_frames": total_duration_frames,
            "titleDurationFrames": title_duration_frames
        },
        "titleCardData": {
            "titleText": story.title,
            "subreddit": f"r/{story.subreddit}",
            "author": f"u/{story.author}",
            "upvotes": str(story.score),
            "keywords": keywords
        },
        "backgrounds": backgrounds_data,
        "words": words_data
    }
    
    json_path = output_dir / "composition_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(composition_data, f, indent=2)
        
    print(f"\n✅ Data Export Complete! Output saved to {output_dir}")
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
            title_id = "3cdcb63d840e0a19ad703bab4b928fe4_1774288704"
        
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
            # Quick Test Run (Hardcoded Cache)
            title_id = "3cdcb63d840e0a19ad703bab4b928fe4_1774288704"
            num_parts = 1
            parts = {"Part 1": "8ff2c43f3f1522bbdfc617c19583ba7d_1774288715"}
            
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
