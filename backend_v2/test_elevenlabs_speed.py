import asyncio
import os
import sys

# Ensure backend_v2 is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "backend_v2":
    sys.path.append(current_dir)
else:
    sys.path.append(os.path.join(current_dir, "backend_v2"))

from config.settings import settings
from reddit_story.elevenlabs_client import ElevenLabsClient

async def test_speed():
    text = "hey how are you today? i want to go to the jungle and play with the monkeys. my name is alon, i like to play futevuley."
    
    # Force elevenlabs engine
    settings.TTS_ENGINE = "elevenlabs"
    
    # Test Normal Speed (1.0)
    print("\n--- Testing Normal Speed (1.0) ---")
    settings.ELEVENLABS_SPEED = 1.0
    client_normal = ElevenLabsClient()
    
    # We pass use_cache=False to ensure we actually generate new audio and don't reuse cached ones for the same text
    # But to prevent duplicate generation for the exact same setting, we will append something to the text or we can just run it.
    try:
        path_normal, duration_normal, _ = await client_normal.text_to_speech_with_timestamps(text + " (normal speed)", use_cache=False)
        print(f"Normal Speed Audio: {path_normal}")
        print(f"Normal Speed Duration: {duration_normal}s")
    except Exception as e:
        print(f"Error normal speed: {e}")

    # Test Fast Speed (1.2)
    print("\n--- Testing Fast Speed (1.2) ---")
    settings.ELEVENLABS_SPEED = 1.2
    client_fast = ElevenLabsClient()
    try:
        path_fast, duration_fast, _ = await client_fast.text_to_speech_with_timestamps(text + " (fast speed)", use_cache=False)
        print(f"Fast Speed Audio: {path_fast}")
        print(f"Fast Speed Duration: {duration_fast}s")
    except Exception as e:
        print(f"Error fast speed: {e}")
        
    print("\nTests complete.")

if __name__ == "__main__":
    asyncio.run(test_speed())
