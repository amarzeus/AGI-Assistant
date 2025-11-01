#!/usr/bin/env python3
"""
Simple test script to verify audio capture functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.audio_transcription import AudioTranscriptionService
from src.config import get_config


async def test_audio_capture():
    """Test audio capture for a short duration."""
    print("Testing audio capture functionality...")
    
    # Initialize service
    service = AudioTranscriptionService()
    
    try:
        # Check if audio is enabled
        if not service.is_enabled():
            print("Audio capture is disabled in config")
            return
        
        # Start service
        print("Starting audio transcription service...")
        await service.start()
        
        # Let it run for 10 seconds
        print("Capturing audio for 10 seconds...")
        print("Try speaking or making some noise...")
        await asyncio.sleep(10)
        
        # Get stats
        stats = service.get_stats()
        print(f"Audio capture stats:")
        print(f"  - Chunks captured: {stats['chunks_captured']}")
        print(f"  - Chunks with speech: {stats['chunks_with_speech']}")
        print(f"  - Total duration: {stats['total_duration']:.1f}s")
        print(f"  - Queue size: {stats['queue_size']}")
        
        # Stop service
        print("Stopping service...")
        await service.stop()
        
        if stats['chunks_captured'] > 0:
            print("✓ Audio capture successful!")
            if stats['chunks_with_speech'] > 0:
                print(f"✓ Voice activity detected in {stats['chunks_with_speech']} chunks")
            else:
                print("ℹ No voice activity detected (try speaking louder)")
        else:
            print("✗ No audio chunks captured")
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_audio_capture())