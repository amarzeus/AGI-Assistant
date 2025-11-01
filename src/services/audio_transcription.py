"""Audio transcription service using pyaudio and faster-whisper."""

import asyncio
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Callable
import uuid
import queue

try:
    import pyaudio
    import numpy as np
    import webrtcvad
    from faster_whisper import WhisperModel
    AUDIO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Audio dependencies not available: {e}")
    AUDIO_AVAILABLE = False
    pyaudio = None
    np = None
    webrtcvad = None
    WhisperModel = None

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.models.transcription import Transcription
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class AudioTranscriptionService:
    """
    Audio transcription service that captures audio and transcribes it using Whisper.
    
    Features:
    - Real-time audio capture using pyaudio
    - Voice Activity Detection (VAD) using webrtcvad
    - Audio buffering in configurable chunks
    - Enable/disable toggle for privacy
    - Integration with event system
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        if not AUDIO_AVAILABLE:
            self.logger.warning("Audio transcription disabled - dependencies not available")
            self.enabled = False
            return
        
        # Audio configuration
        self.sample_rate = self.config.audio.sample_rate
        self.buffer_duration = self.config.audio.buffer_duration
        self.chunk_size = int(self.sample_rate * self.buffer_duration)
        self.format = pyaudio.paInt16
        self.channels = 1
        
        # Service state
        self._enabled = self.config.audio.enabled
        self._running = False
        self._capturing = False
        self._session_id = ""
        
        # Audio components
        self._audio = None
        self._stream = None
        self._vad = None
        self._whisper_model: Optional[WhisperModel] = None
        
        # Threading and queues
        self._capture_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self._processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._chunks_captured = 0
        self._chunks_with_speech = 0
        self._total_audio_duration = 0.0
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Storage manager
        self.storage_manager: Optional[StorageManager] = None
        
        self.logger.info("Audio transcription service initialized")
    
    async def start(self) -> None:
        """Start audio capture service."""
        if not AUDIO_AVAILABLE:
            self.logger.info("Audio transcription unavailable - dependencies not installed")
            return
            
        if self._running:
            self.logger.warning("Audio transcription already running")
            return
        
        if not self._enabled:
            self.logger.info("Audio transcription is disabled")
            return
        
        self.logger.info("Starting audio transcription service")
        self._running = True
        self._session_id = str(uuid.uuid4())
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            # Initialize audio components
            await self._initialize_audio()
            
            # Start capture thread
            self._start_capture_thread()
            
            # Start processing task
            self._processing_task = asyncio.create_task(self._process_audio_loop())
            
            # Publish service started event
            event = Event(
                type=EventType.AUDIO_CAPTURE_STARTED,
                timestamp=datetime.now(),
                source="audio_transcription",
                data={
                    "session_id": self._session_id,
                    "sample_rate": self.sample_rate,
                    "buffer_duration": self.buffer_duration
                }
            )
            await self.event_bus.publish(event)
            
            self.logger.info(f"Audio transcription started for session: {self._session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to start audio transcription: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop audio capture service."""
        if not self._running:
            return
        
        self.logger.info("Stopping audio transcription service")
        self._running = False
        self._capturing = False
        
        try:
            # Stop processing task
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            
            # Stop capture thread
            self._stop_capture_thread()
            
            # Clean up audio components
            await self._cleanup_audio()
            
            # Publish service stopped event
            event = Event(
                type=EventType.AUDIO_CAPTURE_STOPPED,
                timestamp=datetime.now(),
                source="audio_transcription",
                data={
                    "session_id": self._session_id,
                    "chunks_captured": self._chunks_captured,
                    "chunks_with_speech": self._chunks_with_speech,
                    "total_duration": self._total_audio_duration
                }
            )
            await self.event_bus.publish(event)
            
            self.logger.info("Audio transcription stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping audio transcription: {e}")
    
    def enable(self) -> None:
        """Enable audio capture."""
        self._enabled = True
        self.logger.info("Audio transcription enabled")
    
    def disable(self) -> None:
        """Disable audio capture."""
        self._enabled = False
        self.logger.info("Audio transcription disabled")
    
    def is_enabled(self) -> bool:
        """Check if audio capture is enabled."""
        return self._enabled
    
    def is_running(self) -> bool:
        """Check if audio capture is running."""
        return self._running and self._capturing
    
    def get_stats(self) -> dict:
        """Get audio capture statistics."""
        return {
            'enabled': self._enabled,
            'running': self._running,
            'capturing': self._capturing,
            'session_id': self._session_id,
            'chunks_captured': self._chunks_captured,
            'chunks_with_speech': self._chunks_with_speech,
            'total_duration': self._total_audio_duration,
            'sample_rate': self.sample_rate,
            'buffer_duration': self.buffer_duration,
            'queue_size': self._audio_queue.qsize()
        }
    
    async def _initialize_audio(self) -> None:
        """Initialize audio components."""
        try:
            # Initialize PyAudio
            self._audio = pyaudio.PyAudio()
            
            # Initialize Voice Activity Detection
            self._vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (0-3)
            
            # Initialize Whisper model
            await self._initialize_whisper_model()
            
            # Test audio input availability
            device_count = self._audio.get_device_count()
            input_device = None
            
            for i in range(device_count):
                device_info = self._audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_device = i
                    self.logger.info(f"Using audio input device: {device_info['name']}")
                    break
            
            if input_device is None:
                raise RuntimeError("No audio input device found")
            
            # Create audio stream
            self._stream = self._audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=1024,
                stream_callback=None  # We'll use blocking read
            )
            
            self.logger.info("Audio components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audio: {e}")
            await self._cleanup_audio()
            raise
    
    async def _cleanup_audio(self) -> None:
        """Clean up audio components."""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            
            if self._audio:
                self._audio.terminate()
                self._audio = None
            
            self._vad = None
            self._whisper_model = None
            
            self.logger.debug("Audio components cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up audio: {e}")
    
    def _start_capture_thread(self) -> None:
        """Start audio capture thread."""
        self._capturing = True
        self._capture_thread = threading.Thread(
            target=self._capture_audio_thread,
            name="AudioCapture",
            daemon=True
        )
        self._capture_thread.start()
        self.logger.info("Audio capture thread started")
    
    def _stop_capture_thread(self) -> None:
        """Stop audio capture thread."""
        self._capturing = False
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=5.0)
            if self._capture_thread.is_alive():
                self.logger.warning("Audio capture thread did not stop gracefully")
        
        self._capture_thread = None
        self.logger.info("Audio capture thread stopped")
    
    def _capture_audio_thread(self) -> None:
        """Audio capture thread function."""
        self.logger.info("Audio capture thread running")
        
        try:
            while self._capturing and self._stream:
                try:
                    # Read audio data
                    audio_data = self._stream.read(
                        self.chunk_size,
                        exception_on_overflow=False
                    )
                    
                    # Convert to numpy array
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Check for voice activity
                    has_speech = self._detect_voice_activity(audio_data)
                    
                    # Create audio chunk
                    chunk = {
                        'timestamp': datetime.now(),
                        'data': audio_array,
                        'raw_data': audio_data,
                        'has_speech': has_speech,
                        'duration': self.buffer_duration,
                        'sample_rate': self.sample_rate
                    }
                    
                    # Add to processing queue
                    try:
                        self._audio_queue.put_nowait(chunk)
                        self._chunks_captured += 1
                        self._total_audio_duration += self.buffer_duration
                        
                        if has_speech:
                            self._chunks_with_speech += 1
                        
                    except queue.Full:
                        self.logger.warning("Audio queue full, dropping chunk")
                    
                except Exception as e:
                    if self._capturing:  # Only log if we're still supposed to be capturing
                        self.logger.error(f"Error in audio capture: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Fatal error in audio capture thread: {e}")
        
        self.logger.info("Audio capture thread finished")
    
    def _detect_voice_activity(self, audio_data: bytes) -> bool:
        """Detect voice activity in audio data."""
        try:
            if not self._vad:
                return False
            
            # VAD requires specific sample rates and frame sizes
            # For 16kHz, we need 10ms, 20ms, or 30ms frames
            frame_duration_ms = 30  # 30ms frames
            frame_size = int(self.sample_rate * frame_duration_ms / 1000)
            
            # Process audio in VAD-compatible frames
            has_speech = False
            for i in range(0, len(audio_data), frame_size * 2):  # *2 for 16-bit samples
                frame = audio_data[i:i + frame_size * 2]
                
                if len(frame) == frame_size * 2:  # Ensure complete frame
                    try:
                        if self._vad.is_speech(frame, self.sample_rate):
                            has_speech = True
                            break
                    except Exception:
                        # VAD can be sensitive to audio format, continue without it
                        pass
            
            return has_speech
            
        except Exception as e:
            self.logger.debug(f"VAD error: {e}")
            return False  # Assume no speech on error
    
    async def _process_audio_loop(self) -> None:
        """Process captured audio chunks."""
        self.logger.info("Audio processing loop started")
        
        try:
            while self._running:
                try:
                    # Get audio chunk from queue (with timeout)
                    try:
                        chunk = self._audio_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    # Process chunk if it has speech
                    if chunk['has_speech']:
                        await self._process_audio_chunk(chunk)
                    
                    # Mark task as done
                    self._audio_queue.task_done()
                    
                except Exception as e:
                    self.logger.error(f"Error processing audio chunk: {e}")
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in audio processing loop: {e}")
        
        self.logger.info("Audio processing loop finished")
    
    async def _initialize_whisper_model(self) -> None:
        """Initialize Whisper model for transcription."""
        try:
            self.logger.info("Initializing Whisper model...")
            
            # Initialize Whisper model with configuration
            model_name = self.config.audio.model_name
            
            # Use CPU for now (can be changed to GPU if available)
            self._whisper_model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8"  # Use int8 for better performance on CPU
            )
            
            self.logger.info(f"Whisper model '{model_name}' initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Whisper model: {e}")
            raise
    
    async def _process_audio_chunk(self, chunk: dict) -> None:
        """Process a single audio chunk with Whisper transcription."""
        try:
            timestamp = chunk['timestamp']
            duration = chunk['duration']
            audio_data = chunk['data']
            
            # Convert audio to float32 format expected by Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Perform transcription
            transcription_result = await self._transcribe_audio(audio_float)
            
            if transcription_result:
                transcription_text = transcription_result['text']
                confidence = transcription_result['confidence']
                language = transcription_result.get('language', 'en')
                
                self.logger.debug(f"Transcribed: '{transcription_text}' (confidence: {confidence:.2f})")
                
                # Create transcription model
                transcription = Transcription(
                    text=transcription_text,
                    timestamp=timestamp,
                    confidence=confidence,
                    duration=duration,
                    language=language
                )
                
                # Save to database
                if self.storage_manager:
                    try:
                        await self.storage_manager.save_transcription(transcription)
                        self.logger.debug(f"Transcription saved to database: {transcription.id}")
                    except Exception as e:
                        self.logger.error(f"Failed to save transcription: {e}")
                
                # Publish transcription event
                event = Event(
                    type=EventType.AUDIO_TRANSCRIBED,
                    timestamp=timestamp,
                    source="audio_transcription",
                    data={
                        "session_id": self._session_id,
                        "transcription_id": transcription.id,
                        "timestamp": timestamp.isoformat(),
                        "duration": duration,
                        "has_speech": True,
                        "transcription": transcription_text,
                        "confidence": confidence,
                        "language": language,
                        "model": self.config.audio.model_name
                    }
                )
                await self.event_bus.publish(event)
            else:
                # No transcription result
                self.logger.debug(f"No transcription for {duration}s chunk at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error processing audio chunk: {e}")
    
    async def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[dict]:
        """Transcribe audio data using Whisper model."""
        try:
            if not self._whisper_model:
                self.logger.warning("Whisper model not initialized")
                return None
            
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_whisper_transcription,
                audio_data
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in transcription: {e}")
            return None
    
    def _run_whisper_transcription(self, audio_data: np.ndarray) -> Optional[dict]:
        """Run Whisper transcription in thread pool."""
        try:
            # Transcribe audio
            segments, info = self._whisper_model.transcribe(
                audio_data,
                language=self.config.audio.language,
                vad_filter=True,  # Use VAD filtering
                vad_parameters=dict(min_silence_duration_ms=500),
                word_timestamps=False  # Disable for better performance
            )
            
            # Combine all segments into single transcription
            transcription_parts = []
            total_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                if segment.text.strip():  # Only include non-empty segments
                    transcription_parts.append(segment.text.strip())
                    total_confidence += segment.avg_logprob if hasattr(segment, 'avg_logprob') else 0.0
                    segment_count += 1
            
            if not transcription_parts:
                return None
            
            # Calculate average confidence (convert from log probability)
            avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0
            # Convert log probability to confidence score (0-1)
            confidence = min(1.0, max(0.0, (avg_confidence + 1.0)))
            
            return {
                'text': ' '.join(transcription_parts),
                'confidence': confidence,
                'language': info.language if hasattr(info, 'language') else 'en',
                'segments': segment_count
            }
            
        except Exception as e:
            self.logger.error(f"Error in Whisper transcription: {e}")
            return None
    
    async def get_transcriptions_for_timerange(self, start_time: datetime, end_time: datetime) -> List[Transcription]:
        """Get transcriptions within a time range for correlation with screen captures."""
        try:
            if not self.storage_manager:
                return []
            
            return await self.storage_manager.get_transcriptions_by_time_range(start_time, end_time)
            
        except Exception as e:
            self.logger.error(f"Error retrieving transcriptions: {e}")
            return []