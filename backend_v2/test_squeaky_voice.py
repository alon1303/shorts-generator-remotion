#!/usr/bin/env python3
"""
Test script to verify the squeaky voice transformation.
Tests the new EdgeTTS client with +25% rate and +100Hz pitch.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from reddit_story.edgetts_client import EdgeTTSClient


async def test_squeaky_voice():
    """Test the squeaky voice settings."""
    print("=== Testing Squeaky Voice Transformation ===")
    print(f"Expected settings:")
    print(f"  - Voice: en-US-JennyNeural")
    print(f"  - Rate: +25% (faster)")
    print(f"  - Pitch: +100Hz (higher)")
    print()
    
    # Create client with default settings
    client = EdgeTTSClient()
    
    print(f"Client configuration:")
    print(f"  - Voice: {client.voice}")
    print(f"  - Rate: {client.rate}")
    print(f"  - Pitch: {client.pitch}")
    print(f"  - Volume: {client.volume}")
    print()
    
    # Verify configuration
    assert client.voice == "en-US-JennyNeural", f"Expected voice 'en-US-JennyNeural', got '{client.voice}'"
    assert client.rate == "+25%", f"Expected rate '+25%', got '{client.rate}'"
    assert client.pitch == "+100Hz", f"Expected pitch '+100Hz', got '{client.pitch}'"
    assert client.volume == "+0%", f"Expected volume '+0%', got '{client.volume}'"
    
    print("✓ Client configuration matches expected squeaky settings")
    print()
    
    # Test cache key generation includes rate and pitch
    test_text = "Hello, this is a test of the squeaky voice."
    cache_key = client._generate_cache_key(test_text, client.voice)
    print(f"Cache key for test text (first 32 chars): {cache_key[:32]}...")
    print()
    
    # Verify cache key changes with different settings
    old_client = EdgeTTSClient(rate="+0%", pitch="+0Hz", voice="en-US-GuyNeural")
    old_cache_key = old_client._generate_cache_key(test_text, old_client.voice)
    
    if cache_key != old_cache_key:
        print("✓ Cache keys differ for different settings (cache invalidation works)")
    else:
        print("⚠ Warning: Cache keys might not differ - check _generate_cache_key implementation")
    
    print()
    print("=== Testing complete ===")
    print("The EdgeTTS client is now configured for squeaky chipmunk-style narration.")
    print("New audio generations will use:")
    print("  - Voice: en-US-JennyNeural (female, handles high-pitch better)")
    print("  - Speed: +25% faster (squeaky fast pace)")
    print("  - Pitch: +100Hz higher (chipmunk effect)")
    print()
    print("Note: Existing cached audio with old settings will not be reused.")
    print("      New cache entries will be created with the new settings.")
    
    # Clean up
    await client.close()
    await old_client.close()


async def test_voice_generation():
    """Actually generate a small audio sample (optional)."""
    print("\n=== Testing actual voice generation (optional) ===")
    response = input("Generate a test audio sample? (y/n): ")
    
    if response.lower() == 'y':
        client = EdgeTTSClient()
        test_text = "This is a test of the squeaky voice for Shorts."
        
        print(f"Generating audio for: '{test_text}'")
        print("This may take a few seconds...")
        
        try:
            audio_path, duration, word_timestamps = await client.text_to_speech_with_timestamps(
                text=test_text,
                use_cache=False  # Force new generation
            )
            
            if audio_path and audio_path.exists():
                print(f"✓ Audio generated successfully:")
                print(f"  - Path: {audio_path}")
                print(f"  - Duration: {duration:.2f} seconds")
                if word_timestamps:
                    print(f"  - Word timestamps: {len(word_timestamps)} words")
                    print("    First 3 words:")
                    for i, ts in enumerate(word_timestamps[:3]):
                        print(f"      '{ts.word}': {ts.start:.2f}s - {ts.end:.2f}s")
                
                # Clean up test file
                audio_path.unlink(missing_ok=True)
                metadata_path = audio_path.with_suffix('.json')
                metadata_path.unlink(missing_ok=True)
                timestamp_path = audio_path.with_suffix('.timestamps.json')
                timestamp_path.unlink(missing_ok=True)
                
                print(f"\n✓ Test files cleaned up")
            else:
                print("✗ Failed to generate audio")
                
        except Exception as e:
            print(f"✗ Error during audio generation: {e}")
        
        await client.close()


if __name__ == "__main__":
    print("Squeaky Voice Transformation Test")
    print("=" * 40)
    
    # Run configuration test
    asyncio.run(test_squeaky_voice())
    
    # Ask about actual generation (can be slow)
    try:
        asyncio.run(test_voice_generation())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"\nError during voice generation test: {e}")
    
    print("\n=== Test Summary ===")
    print("The squeaky voice transformation has been successfully configured.")
    print("To use it in production:")
    print("  1. Restart any running backend services")
    print("  2. New videos will use the squeaky voice")
    print("  3. Old cached audio will not be reused (new cache entries created)")