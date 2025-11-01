"""Logging configuration with rotating file handlers."""

import logging
import logging.handlers
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import psutil
import os


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


class PerformanceLogger:
    """Logger with performance metrics tracking."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.process = psutil.Process(os.getpid())
    
    def log_with_metrics(self, level: int, message: str, **kwargs) -> None:
        """Log message with performance metrics."""
        metrics = {
            'cpu_percent': self.process.cpu_percent(),
            'memory_mb': self.process.memory_info().rss / 1024 / 1024,
            'threads': self.process.num_threads(),
        }
        
        extra_data = kwargs.get('extra_data', {})
        extra_data.update(metrics)
        
        self.logger.log(level, message, extra={'extra_data': extra_data})
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with metrics."""
        self.log_with_metrics(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with metrics."""
        self.log_with_metrics(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with metrics."""
        self.log_with_metrics(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with metrics."""
        self.log_with_metrics(logging.ERROR, message, **kwargs)


def setup_logger(
    name: str,
    log_dir: Path,
    level: str = 'INFO',
    use_json: bool = True,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up logger with rotating file handler.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level
        use_json: Use JSON formatting
        max_bytes: Maximum log file size
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    log_file = log_dir / f'{name}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    
    # Set formatters
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str, with_metrics: bool = False) -> logging.Logger | PerformanceLogger:
    """
    Get logger instance.
    
    Args:
        name: Logger name
        with_metrics: Return PerformanceLogger with metrics tracking
    
    Returns:
        Logger instance
    """
    from src.config import get_config
    
    config = get_config()
    paths = config.get_data_paths()
    
    logger = setup_logger(
        name=name,
        log_dir=paths['logs'],
        level=config.log_level,
        use_json=True
    )
    
    if with_metrics:
        return PerformanceLogger(logger)
    
    return logger


# Component-specific loggers
def get_screen_capture_logger() -> PerformanceLogger:
    """Get screen capture service logger."""
    return get_logger('screen_capture', with_metrics=True)


def get_audio_logger() -> PerformanceLogger:
    """Get audio transcription service logger."""
    return get_logger('audio_transcription', with_metrics=True)


def get_workflow_logger() -> PerformanceLogger:
    """Get workflow analyzer logger."""
    return get_logger('workflow_analyzer', with_metrics=True)


def get_storage_logger() -> PerformanceLogger:
    """Get storage manager logger."""
    return get_logger('storage_manager', with_metrics=True)


def get_ui_logger() -> logging.Logger:
    """Get UI logger."""
    return get_logger('ui', with_metrics=False)


def get_app_logger() -> logging.Logger:
    """Get main application logger."""
    return get_logger('app', with_metrics=False)
