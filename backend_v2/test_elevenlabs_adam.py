import sys
import os
import asyncio
import shutil
from pathlib import Path

# Add backend_v2 to Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.settings import settings
from reddit_story.elevenlabs_client import ElevenLabsClient

async def main():
    text = "hey, my name is alon, i like playing futevuley and listening to house music. i also like the summer and going to the beach."
    voice_name = "adam"
    voice_id = settings.get_voice_id(voice_name)
    
    print(f"Initializing ElevenLabsClient with voice: {voice_name} (ID: {voice_id})")
    
    try:
        client = ElevenLabsClient(voice=voice_id)
        
        print(f"Generating audio for text:\n'{text}'")
        file_path, duration, timestamps = await client.text_to_speech_with_timestamps(
            text=text,
            voice=voice_id,
            use_cache=False
        )
        
        print(f"\nAudio generated successfully!")
        print(f"Original cache path: {file_path}")
        print(f"Duration: {duration:.2f} seconds")
        
        # Copy to a visible outputs folder
        output_dir = Path(settings.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "test_adam_elevenlabs.mp3"
        
        shutil.copy2(file_path, out_path)
        print(f"Saved copy to: {out_path}")
        
        await client.close()
        
    except Exception as e:
        print(f"Error generating audio: {e}")

if __name__ == "__main__":
    asyncio.run(main())
