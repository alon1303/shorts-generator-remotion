#!/usr/bin/env python3
"""
Create a simple "pop" sound effect for video hooks.
Generates a short (0.5s) sine-wave chirp sound.
"""

import wave
import math
import struct
from pathlib import Path

def generate_pop_sound(
    output_path: Path,
    duration: float = 0.1,  # seconds
    sample_rate: int = 44100,  # Hz
    frequency_start: int = 1000,  # Hz
    frequency_end: int = 1000,  # Hz
    volume: float = 0.5  # 0.0 to 1.0
) -> bool:
    """
    Generate a simple pop/chirp sound effect.
    
    Args:
        output_path: Path to save the WAV file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency_start: Starting frequency in Hz
        frequency_end: Ending frequency in Hz
        volume: Volume (0.0 to 1.0)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate number of samples
        num_samples = int(duration * sample_rate)
        
        # Generate samples
        samples = []
        
        for i in range(num_samples):
            # Calculate current time
            t = i / sample_rate
            
            # Calculate current frequency (linear sweep from start to end)
            freq = frequency_start + (frequency_end - frequency_start) * (t / duration)
            
            # Calculate envelope (attack and decay)
            if t < 0.05:  # 50ms attack
                envelope = t / 0.05
            elif t > duration - 0.1:  # 100ms decay
                envelope = (duration - t) / 0.1
            else:  # sustain
                envelope = 1.0
            
            # Generate sine wave sample
            sample = math.sin(2 * math.pi * freq * t)
            
            # Apply envelope and volume
            sample *= envelope * volume
            
            # Convert to 16-bit PCM
            sample_int = int(sample * 32767)
            samples.append(sample_int)
        
        # Create WAV file
        with wave.open(str(output_path), 'w') as wav_file:
            # Set parameters
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(sample_rate)
            
            # Write samples
            for sample in samples:
                # Pack as little-endian signed short
                data = struct.pack('<h', sample)
                wav_file.writeframes(data)
        
        print(f"✅ Pop sound effect generated: {output_path}")
        print(f"   Duration: {duration}s, Sample rate: {sample_rate}Hz")
        print(f"   Frequency sweep: {frequency_start}Hz → {frequency_end}Hz")
        print(f"   File size: {output_path.stat().st_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate pop sound effect: {e}")
        return False

def generate_alternative_pop_sound(
    output_path: Path,
    duration: float = 0.3,  # shorter pop
    sample_rate: int = 44100
) -> bool:
    """
    Generate an alternative pop sound (more percussive).
    
    Args:
        output_path: Path to save the WAV file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        num_samples = int(duration * sample_rate)
        samples = []
        
        for i in range(num_samples):
            t = i / sample_rate
            
            # Exponential decay envelope
            decay_time = 0.15
            if t < decay_time:
                envelope = math.exp(-t * 20)  # Fast decay
            else:
                envelope = 0.0
            
            # Simple sine wave at 600Hz
            freq = 600
            sample = math.sin(2 * math.pi * freq * t)
            
            # Apply envelope
            sample *= envelope * 0.4  # Lower volume
            
            # Convert to 16-bit PCM
            sample_int = int(sample * 32767)
            samples.append(sample_int)
        
        # Create WAV file
        with wave.open(str(output_path), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            
            for sample in samples:
                data = struct.pack('<h', sample)
                wav_file.writeframes(data)
        
        print(f"✅ Alternative pop sound generated: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate alternative pop sound: {e}")
        return False

def main():
    """Main function to generate pop sound effects."""
    print("Pop Sound Effect Generator")
    print("="*60)
    
    # Create assets/sfx directory
    assets_dir = Path(__file__).parent / "assets" / "sfx"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate main pop sound
    pop_path = assets_dir / "pop.wav"
    print(f"\nGenerating main pop sound effect...")
    success1 = generate_pop_sound(
        output_path=pop_path,
        duration=0.5,
        frequency_start=800,
        frequency_end=200,
        volume=0.3
    )
    
    # Generate alternative pop sound
    alt_pop_path = assets_dir / "pop_alt.wav"
    print(f"\nGenerating alternative pop sound effect...")
    success2 = generate_alternative_pop_sound(
        output_path=alt_pop_path,
        duration=0.3
    )
    
    # Generate click sound (very short)
    click_path = assets_dir / "click.wav"
    print(f"\nGenerating click sound effect...")
    success3 = generate_pop_sound(
        output_path=click_path,
        duration=0.1,
        frequency_start=1000,
        frequency_end=100,
        volume=0.2
    )
    
    print("\n" + "="*60)
    if success1 or success2 or success3:
        print("✅ Sound effects generated successfully!")
        print(f"\nGenerated files in: {assets_dir}")
        
        # List generated files
        for file in assets_dir.glob("*.wav"):
            if file.exists():
                print(f"  - {file.name} ({file.stat().st_size} bytes)")
        
        print("\nUsage in video_composer.py:")
        print("  pop_sfx_path = Path('assets/sfx/pop.wav')")
        print("  if not pop_sfx_path.exists():")
        print("      # Generate it on first run")
        print("      from create_pop_sfx import generate_pop_sound")
        print("      generate_pop_sound(pop_sfx_path)")
    else:
        print("❌ Failed to generate sound effects")
        print("   Check permissions and disk space")

if __name__ == "__main__":
    main()