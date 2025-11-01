"""Performance Monitor Service.

Monitors and optimizes application performance:
- Track CPU and memory usage
- Monitor operation durations
- Detect performance issues
- Trigger optimizations
"""

import psutil
import time
from collections import deque
from typing import Dict, Any, List
from dataclasses import dataclass

from src.config import get_config
from src.logger import get_app_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    cpu_percent: float
    memory_mb: float
    timestamp: float


class PerformanceMonitor:
    """Service for monitoring application performance."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        self.metrics: Dict[str, deque] = {
            'cpu': deque(maxlen=100),
            'memory': deque(maxlen=100),
            'capture_time': deque(maxlen=100),
            'analysis_time': deque(maxlen=100),
        }
        
        self.thresholds = {
            'cpu_percent': 50.0,
            'memory_mb': 700.0,
            'capture_time': 1.0,
            'analysis_time': 5.0,
        }
        
        self.process = psutil.Process()
        self.logger.info("Performance monitor initialized")
    
    async def initialize(self) -> None:
        """Initialize performance monitoring."""
        self.logger.info("Performance monitor ready")
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric."""
        if name in self.metrics:
            self.metrics[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        cpu_percent = self.process.cpu_percent()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        self.record_metric('cpu', cpu_percent)
        self.record_metric('memory', memory_mb)
        
        return {
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'cpu_avg': sum(self.metrics['cpu']) / len(self.metrics['cpu']) if self.metrics['cpu'] else 0,
            'memory_avg': sum(self.metrics['memory']) / len(self.metrics['memory']) if self.metrics['memory'] else 0,
        }
    
    def check_thresholds(self) -> List[str]:
        """Check if any thresholds are exceeded."""
        warnings = []
        metrics = self.get_metrics()
        
        if metrics['cpu_percent'] > self.thresholds['cpu_percent']:
            warnings.append(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
        
        if metrics['memory_mb'] > self.thresholds['memory_mb']:
            warnings.append(f"High memory usage: {metrics['memory_mb']:.1f}MB")
        
        return warnings
