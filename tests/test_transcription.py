#!/usr/bin/env python3
"""
Test script to verify audio transcription functionality with Whisper.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.services.audio_transcription import AudioTranscriptionService
from src.config import get_config


async def test_transcription():
    """Test audio transcription with Whisper."""
    print("Testing audio transcription with Whisper...")
    
    # Initialize service
    service = AudioTranscriptionService()
    
    try:
        # Check if audio is enabled
        if not service.is_enabled():
            print("Audio capture is disabled in config")
            return
        
        # Start service
        print("Starting audio transcription service...")
        print("This will download the Whisper model if not already present...")
        await service.start()
        
        # Let it run for 15 seconds
        print("Capturing and transcribing audio for 15 seconds...")
        print("Try speaking clearly into your microphone...")
        await asyncio.sleep(15)
        
        # Get stats
        stats = service.get_stats()
        print(f"\nAudio transcription stats:")
        print(f"  - Chunks captured: {stats['chunks_captured']}")
        print(f"  - Chunks with speech: {stats['chunks_with_speech']}")
        print(f"  - Total duration: {stats['total_duration']:.1f}s")
        print(f"  - Queue size: {stats['queue_size']}")
        
        # Get recent transcriptions
        if service.storage_manager:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=1)
            transcriptions = await service.get_transcriptions_for_timerange(start_time, end_time)
            
            if transcriptions:
                print(f"\nRecent transcriptions ({len(transcriptions)}):")
                for i, trans in enumerate(transcriptions, 1):
                    print(f"  {i}. [{trans.timestamp.strftime('%H:%M:%S')}] "
                          f"'{trans.text}' (confidence: {trans.confidence:.2f})")
            else:
                print("\nNo transcriptions found in database")
        
        # Stop service
        print("\nStopping service...")
        await service.stop()
        
        if stats['chunks_captured'] > 0:
            print("✓ Audio capture successful!")
            if stats['chunks_with_speech'] > 0:
                print(f"✓ Voice activity detected in {stats['chunks_with_speech']} chunks")
                if transcriptions:
                    print(f"✓ Transcription successful! Generated {len(transcriptions)} transcriptions")
                else:
                    print("ℹ Voice detected but no transcriptions generated (try speaking louder/clearer)")
            else:
                print("ℹ No voice activity detected (try speaking louder)")
        else:
            print("✗ No audio chunks captured")
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_transcription())