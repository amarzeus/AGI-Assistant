"""Configuration management using pydantic."""

from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, Field
import os


class ScreenCaptureConfig(BaseModel):
    """Screen capture configuration."""
    screenshot_interval: int = Field(default=3, ge=2, le=5, description="Screenshot interval in seconds")
    video_segment_duration: int = Field(default=45, ge=30, le=60, description="Video segment duration in seconds")
    resolution_width: int = Field(default=1280, description="Capture width")
    resolution_height: int = Field(default=720, description="Capture height")
    video_quality: Literal['low', 'medium', 'high'] = Field(default='medium', description="Video quality")
    video_format: str = Field(default='mp4', description="Video file format")
    screenshot_format: str = Field(default='png', description="Screenshot file format")
    video_fps: float = Field(default=5.0, ge=1.0, le=10.0, description="Video frames per second")
    video_codec: str = Field(default='mp4v', description="Video codec (mp4v, h264, etc.)")
    enable_compression: bool = Field(default=True, description="Enable video compression")


class AudioConfig(BaseModel):
    """Audio transcription configuration."""
    enabled: bool = Field(default=True, description="Enable audio capture")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    buffer_duration: int = Field(default=5, description="Audio buffer duration in seconds")
    vad_threshold: int = Field(default=-30, description="Voice Activity Detection threshold in dB")
    model_name: str = Field(default='base.en', description="Whisper model name")
    language: str = Field(default='en', description="Transcription language")


class StorageConfig(BaseModel):
    """Storage management configuration."""
    max_storage_gb: int = Field(default=10, ge=5, le=50, description="Maximum storage in GB")
    cleanup_threshold: float = Field(default=0.9, ge=0.5, le=0.95, description="Cleanup trigger threshold")
    retention_days_structured: int = Field(default=7, description="Days to keep structured data")
    retention_days_screenshots: int = Field(default=3, description="Days to keep screenshots")
    retention_days_video: int = Field(default=1, description="Days to keep video")
    enable_compression: bool = Field(default=True, description="Enable data compression")


class LLMConfig(BaseModel):
    """Local LLM configuration."""
    enabled: bool = Field(default=True, description="Enable LLM features (Phi-3 is lightweight!)")
    model_name: str = Field(default='phi:latest', description="LLM model name (phi is lightweight)")
    context_window: int = Field(default=1024, description="Context window size (reduced for speed)")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="LLM temperature")
    max_tokens: int = Field(default=256, description="Maximum tokens for response (reduced for speed)")
    use_ollama: bool = Field(default=True, description="Use Ollama for LLM")


class PrivacyConfig(BaseModel):
    """Privacy and security configuration."""
    excluded_apps: List[str] = Field(default_factory=list, description="Applications to exclude from capture")
    pause_shortcut: str = Field(default='ctrl+shift+p', description="Keyboard shortcut to pause")
    show_privacy_indicator: bool = Field(default=True, description="Show privacy indicator")
    secure_deletion: bool = Field(default=True, description="Securely delete files")


class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = Field(default='AGI Assistant', description="Application name")
    data_dir: Path = Field(default_factory=lambda: Path.home() / 'agi-assistant-data', description="Data directory")
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(default='INFO', description="Logging level")
    
    # Component configs
    screen_capture: ScreenCaptureConfig = Field(default_factory=ScreenCaptureConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    
    class Config:
        """Pydantic config."""
        use_enum_values = True
    
    def get_data_paths(self) -> dict:
        """Get all data directory paths."""
        base = self.data_dir
        return {
            'base': base,
            'db': base / 'db',
            'sessions': base / 'sessions',
            'models': base / 'models',
            'logs': base / 'logs',
            'exports': base / 'exports',
        }
    
    def ensure_directories(self) -> None:
        """Create all required directories."""
        paths = self.get_data_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from JSON file."""
        import json
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        return cls()
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        import json
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)


# Global config instance
_config: AppConfig = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        config_path = Path.home() / '.agi-assistant' / 'config.json'
        _config = AppConfig.load_from_file(config_path)
        _config.ensure_directories()
    return _config


def set_config(config: AppConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config
    config_path = Path.home() / '.agi-assistant' / 'config.json'
    config.save_to_file(config_path)
