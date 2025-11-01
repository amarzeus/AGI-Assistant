"""Automation Scheduler Service.

This module provides scheduling capabilities for recurring workflow executions:
- Create and manage schedules
- Calculate next run times
- Execute workflows at scheduled times
- Handle retries and failures
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from src.config import get_config
from src.logger import get_app_logger


class ScheduleType(Enum):
    """Schedule type enumeration."""
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class RetryPolicy:
    """Retry policy for failed scheduled executions."""
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    backoff_multiplier: float = 2.0


@dataclass
class Schedule:
    """Represents a workflow execution schedule."""
    id: str
    workflow_id: str
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AutomationScheduler:
    """Service for scheduling recurring workflow executions."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        self.schedules: Dict[str, Schedule] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.logger.info("Automation scheduler initialized")
    
    async def initialize(self) -> None:
        """Initialize the scheduler and start the scheduler loop."""
        try:
            self._running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            self.logger.info("Automation scheduler started")
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self._running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Automation scheduler stopped")
    
    async def create_schedule(
        self,
        workflow_id: str,
        schedule_config: Dict[str, Any]
    ) -> str:
        """Create a new schedule."""
        import uuid
        schedule_id = str(uuid.uuid4())
        
        schedule_type = ScheduleType(schedule_config.get('type', 'one_time'))
        
        schedule = Schedule(
            id=schedule_id,
            workflow_id=workflow_id,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            enabled=True
        )
        
        schedule.next_run = await self.get_next_run_time(schedule)
        self.schedules[schedule_id] = schedule
        
        self.logger.info(f"Created schedule {schedule_id} for workflow {workflow_id}")
        return schedule_id
    
    async def get_next_run_time(self, schedule: Schedule) -> datetime:
        """Calculate next run time for schedule."""
        now = datetime.now()
        config = schedule.schedule_config
        
        if schedule.schedule_type == ScheduleType.ONE_TIME:
            run_time = datetime.fromisoformat(config['run_at'])
            return run_time if run_time > now else now
        
        elif schedule.schedule_type == ScheduleType.DAILY:
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif schedule.schedule_type == ScheduleType.WEEKLY:
            days = config.get('days', [0])  # 0=Monday
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            
            for i in range(7):
                check_date = now + timedelta(days=i)
                if check_date.weekday() in days:
                    next_run = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run > now:
                        return next_run
            return now + timedelta(days=7)
        
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            interval_minutes = config.get('interval_minutes', 60)
            if schedule.last_run:
                return schedule.last_run + timedelta(minutes=interval_minutes)
            return now + timedelta(minutes=interval_minutes)
        
        return now + timedelta(hours=1)
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now()
                
                for schedule_id, schedule in list(self.schedules.items()):
                    if not schedule.enabled:
                        continue
                    
                    if schedule.next_run and schedule.next_run <= now:
                        self.logger.info(f"Triggering schedule {schedule_id}")
                        await self._execute_scheduled_workflow(schedule)
                        
                        schedule.last_run = now
                        schedule.next_run = await self.get_next_run_time(schedule)
                        schedule.updated_at = now
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_scheduled_workflow(self, schedule: Schedule) -> None:
        """Execute a scheduled workflow."""
        self.logger.info(f"Executing scheduled workflow {schedule.workflow_id}")
        # Integration point with AutomationExecutor
