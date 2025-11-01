"""Automation executor service for executing workflows."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

from src.config import get_config
from src.logger import get_app_logger
from src.models.action import Action
from src.database.storage_manager import StorageManager
from src.services.event_system import get_event_bus, EventType, Event
from src.services.platforms.desktop_automation import DesktopAutomationPlatform
from src.services.safety_manager import SafetyManager
from src.services.execution_verifier import ExecutionVerifier, VerificationResult
from src.services.feedback_loop_manager import FeedbackLoopManager, FeedbackAnalysis


class ExecutionState(Enum):
    """Execution state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowExecution:
    """Represents a workflow execution instance."""
    
    def __init__(self, workflow_id: str, workflow_data: Dict[str, Any]):
        self.id = f"exec_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.workflow_id = workflow_id
        self.workflow_data = workflow_data
        self.state = ExecutionState.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.current_step = 0
        self.total_steps = len(workflow_data.get('actions', []))
        self.progress = 0.0
        self.error_message: Optional[str] = None
        self.execution_log: List[Dict[str, Any]] = []
        self.verification_results: List[VerificationResult] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'state': self.state.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress': self.progress,
            'error_message': self.error_message,
            'execution_log': self.execution_log,
            'verification_results': [vr.to_dict() for vr in self.verification_results]
        }


class AutomationExecutor:
    """
    Automation executor service for executing workflows.
    
    Features:
    - Load workflows from JSON exports
    - Execute workflows step-by-step
    - Track execution state and progress
    - Handle errors and retries
    - Log execution details
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Execution queue
        self.execution_queue: List[WorkflowExecution] = []
        self.current_execution: Optional[WorkflowExecution] = None
        
        # Storage
        self.storage_manager: Optional[StorageManager] = None
        
        # Safety manager
        self.safety_manager = SafetyManager()
        
        # Execution verifier
        self.execution_verifier = ExecutionVerifier()
        
        # Feedback loop manager
        self.feedback_loop_manager = FeedbackLoopManager()
        
        # Automation platforms
        self.desktop_platform = DesktopAutomationPlatform()
        self.browser_platform = None  # Lazy loaded
        self.application_platform = None  # Lazy loaded
        
        # Event system
        self.event_bus = get_event_bus()
        
        # State
        self._running = False
        self._executor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._executions_completed = 0
        self._executions_failed = 0
        
        self.logger.info("Automation executor initialized")
    
    async def initialize(self, storage_manager: StorageManager) -> None:
        """Initialize automation executor."""
        self.logger.info("Initializing automation executor...")
        self.storage_manager = storage_manager
        
        # Initialize execution verifier
        await self.execution_verifier.initialize()
        
        # Initialize feedback loop manager
        await self.feedback_loop_manager.initialize()
        
        self.logger.info("Automation executor initialized successfully")
    
    async def start(self) -> None:
        """Start the automation executor."""
        if self._running:
            self.logger.warning("Automation executor already running")
            return
        
        self.logger.info("Starting automation executor")
        self._running = True
        
        # Start executor loop
        self._executor_task = asyncio.create_task(self._executor_loop())
        
        self.logger.info("Automation executor started")
    
    async def stop(self) -> None:
        """Stop the automation executor."""
        if not self._running:
            return
        
        self.logger.info("Stopping automation executor")
        self._running = False
        
        # Cancel current execution
        if self.current_execution:
            await self.cancel_execution(self.current_execution.id)
        
        # Close browser if open
        if self.browser_platform:
            await self.browser_platform.close()
            self.browser_platform = None
        
        # Close application platform if open
        if self.application_platform:
            await self.application_platform.close_excel()
            self.application_platform = None
        
        # Stop executor task
        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Automation executor stopped")
    
    async def _ensure_browser(self) -> None:
        """Ensure browser platform is initialized."""
        if self.browser_platform is None:
            from src.services.platforms.browser_automation import BrowserAutomationPlatform
            self.browser_platform = BrowserAutomationPlatform()
            
            if not self.browser_platform.enabled:
                raise RuntimeError("Browser automation not available (Playwright not installed)")
            
            await self.browser_platform.initialize(headless=False)
            self.logger.info("Browser platform initialized")
    
    async def _ensure_application(self) -> None:
        """Ensure application platform is initialized."""
        if self.application_platform is None:
            from src.services.platforms.application_automation import ApplicationAutomationPlatform
            self.application_platform = ApplicationAutomationPlatform()
            
            if not self.application_platform.enabled:
                raise RuntimeError("Application automation not available (pywin32 not installed)")
            
            self.logger.info("Application platform initialized")
    
    async def load_workflow_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load workflow from JSON file.
        
        Args:
            file_path: Path to workflow JSON file
            
        Returns:
            Workflow data dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Validate workflow structure
            if not self._validate_workflow(workflow_data):
                raise ValueError("Invalid workflow structure")
            
            self.logger.info(f"Loaded workflow from {file_path}")
            return workflow_data
            
        except Exception as e:
            self.logger.error(f"Failed to load workflow from {file_path}: {e}")
            raise
    
    def _validate_workflow(self, workflow_data: Dict[str, Any]) -> bool:
        """Validate workflow structure."""
        required_fields = ['id', 'name', 'actions']
        
        for field in required_fields:
            if field not in workflow_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        if not isinstance(workflow_data['actions'], list):
            self.logger.error("Actions must be a list")
            return False
        
        if len(workflow_data['actions']) == 0:
            self.logger.error("Workflow must have at least one action")
            return False
        
        return True
    
    async def queue_execution(self, workflow_data: Dict[str, Any]) -> str:
        """
        Queue a workflow for execution.
        
        Args:
            workflow_data: Workflow data dictionary
            
        Returns:
            Execution ID
        """
        try:
            # Create execution instance
            execution = WorkflowExecution(
                workflow_id=workflow_data['id'],
                workflow_data=workflow_data
            )
            
            # Add to queue
            self.execution_queue.append(execution)
            
            self.logger.info(f"Queued execution: {execution.id}")
            
            # Emit event
            event = Event(
                type=EventType.WORKFLOW_EXECUTION_QUEUED,
                timestamp=datetime.now(),
                source="automation_executor",
                data={'execution_id': execution.id}
            )
            await self.event_bus.publish(event)
            
            return execution.id
            
        except Exception as e:
            self.logger.error(f"Failed to queue execution: {e}")
            raise
    
    async def _executor_loop(self) -> None:
        """Main executor loop."""
        self.logger.info("Executor loop started")
        
        try:
            while self._running:
                try:
                    # Check if there's work to do
                    if not self.current_execution and self.execution_queue:
                        # Get next execution from queue
                        self.current_execution = self.execution_queue.pop(0)
                        
                        # Execute workflow
                        await self._execute_workflow(self.current_execution)
                        
                        # Clear current execution
                        self.current_execution = None
                    
                    # Wait before checking again
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error in executor loop: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            self.logger.error(f"Fatal error in executor loop: {e}")
        
        self.logger.info("Executor loop finished")
    
    async def _execute_workflow(self, execution: WorkflowExecution) -> None:
        """
        Execute a workflow.
        
        Args:
            execution: WorkflowExecution instance
        """
        try:
            self.logger.info(f"Starting execution: {execution.id}")
            
            # Update state
            execution.state = ExecutionState.RUNNING
            execution.start_time = datetime.now()
            
            # Emit start event
            await self._emit_execution_event(execution, EventType.WORKFLOW_EXECUTION_STARTED)
            
            # Get actions
            actions = execution.workflow_data.get('actions', [])
            
            # Execute each action
            for i, action_data in enumerate(actions):
                if not self._running or execution.state == ExecutionState.CANCELLED:
                    break
                
                # Update progress
                execution.current_step = i + 1
                execution.progress = (i + 1) / execution.total_steps
                
                # Execute action
                await self._execute_action(execution, action_data)
                
                # Emit progress event
                await self._emit_execution_event(execution, EventType.WORKFLOW_EXECUTION_PROGRESS)
                
                # Small delay between actions
                await asyncio.sleep(0.5)
            
            # Check if completed successfully
            if execution.state == ExecutionState.RUNNING:
                execution.state = ExecutionState.COMPLETED
                execution.end_time = datetime.now()
                self._executions_completed += 1
                
                self.logger.info(f"Execution completed: {execution.id}")
                await self._emit_execution_event(execution, EventType.WORKFLOW_EXECUTION_COMPLETED)
            
            # Analyze execution with feedback loop (regardless of success/failure)
            try:
                feedback_analysis = await self.feedback_loop_manager.analyze_execution(
                    execution,
                    execution.verification_results
                )
                
                # Update confidence score
                success = execution.state == ExecutionState.COMPLETED
                new_confidence = await self.feedback_loop_manager.update_confidence(
                    execution.workflow_id,
                    success
                )
                
                # Store confidence in database (pattern metadata)
                try:
                    from src.database.storage_manager import StorageManager
                    storage = StorageManager()
                    await storage.update_pattern_confidence(execution.workflow_id, new_confidence)
                except Exception as e:
                    self.logger.error(f"Failed to store confidence in database: {e}")
                
                # Generate improvement suggestions
                improvement_suggestions = await self.feedback_loop_manager.suggest_improvements(
                    execution.workflow_id
                )
                
                self.logger.info(
                    f"Feedback analysis complete: confidence={new_confidence:.2f}, "
                    f"issues={len(feedback_analysis.issues_detected)}, "
                    f"suggestions={len(improvement_suggestions)}"
                )
                
                # Apply adjustments if suggested
                if feedback_analysis.suggested_adjustments:
                    adjusted_workflow = await self.feedback_loop_manager.adjust_workflow(
                        execution.workflow_id,
                        execution.workflow_data,
                        feedback_analysis
                    )
                    
                    # Store adjusted workflow for potential retry
                    execution.workflow_data = adjusted_workflow
                    
                    adjustments_count = adjusted_workflow.get('metadata', {}).get('adjustments_count', 0)
                    self.logger.info(
                        f"Applied {adjustments_count} adjustments to workflow"
                    )
                
                # Emit feedback event for UI updates
                feedback_event = Event(
                    type=EventType.WORKFLOW_EXECUTION_COMPLETED,  # Reuse existing event type
                    timestamp=datetime.now(),
                    source="feedback_loop_manager",
                    data={
                        'execution_id': execution.id,
                        'workflow_id': execution.workflow_id,
                        'feedback_analysis': feedback_analysis.to_dict(),
                        'confidence': new_confidence,
                        'improvement_suggestions': improvement_suggestions,
                    }
                )
                await self.event_bus.publish(feedback_event)
                
            except Exception as e:
                self.logger.error(f"Feedback loop analysis failed: {e}")
            
        except Exception as e:
            self.logger.error(f"Execution failed: {execution.id}: {e}")
            execution.state = ExecutionState.FAILED
            execution.end_time = datetime.now()
            execution.error_message = str(e)
            self._executions_failed += 1
            
            await self._emit_execution_event(execution, EventType.WORKFLOW_EXECUTION_FAILED)
    
    async def _execute_action(self, execution: WorkflowExecution, action_data: Dict[str, Any]) -> None:
        """
        Execute a single action.
        
        Args:
            execution: WorkflowExecution instance
            action_data: Action data dictionary
        """
        action_type = action_data.get('type', 'unknown')
        start_time = datetime.now()
        
        # Add action ID if not present
        if 'id' not in action_data:
            action_data['id'] = f"action_{execution.current_step}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # Log action
        log_entry = {
            'timestamp': start_time.isoformat(),
            'step': execution.current_step,
            'action_type': action_type,
            'status': 'started'
        }
        
        before_state = ""
        after_state = ""
        
        try:
            # Check emergency stop BEFORE action
            if await self.safety_manager.check_emergency_stop():
                self.logger.warning(f"Emergency stop active - cancelling action {execution.current_step}")
                log_entry['status'] = 'cancelled'
                log_entry['error'] = 'Emergency stop triggered'
                execution.execution_log.append(log_entry)
                execution.state = ExecutionState.CANCELLED
                raise RuntimeError("Emergency stop triggered")
            
            # Check rate limit
            if await self.safety_manager.check_rate_limit():
                self.logger.warning(f"Rate limit exceeded - delaying action {execution.current_step}")
                await asyncio.sleep(1.0)  # Brief delay to respect rate limit
            
            # Validate action BEFORE execution
            if not await self.safety_manager.validate_action(action_data):
                self.logger.error(f"Action validation failed for action {execution.current_step}")
                log_entry['status'] = 'failed'
                log_entry['error'] = 'Action validation failed'
                execution.execution_log.append(log_entry)
                raise ValueError(f"Action validation failed: {action_type}")
            
            # Capture BEFORE state for verification
            before_state = await self.execution_verifier.capture_before_state(action_data)
            
            self.logger.debug(f"Executing action {execution.current_step}: {action_type}")
            
            # Execute action based on type
            success = await self._dispatch_action(action_type, action_data)
            
            # Small delay to allow UI to update
            await asyncio.sleep(0.3)
            
            # Capture AFTER state for verification
            after_state = await self.execution_verifier.capture_after_state(action_data)
            
            # Verify action completed successfully
            verification_result = await self.execution_verifier.verify_action(
                action_data,
                before_state,
                after_state
            )
            
            # Store verification result
            execution.verification_results.append(verification_result)
            
            # Check timeout AFTER action
            if await self.safety_manager.check_timeout(action_type, start_time):
                self.logger.warning(f"Action {execution.current_step} timed out")
                log_entry['status'] = 'timeout'
                log_entry['error'] = f'Action exceeded timeout'
                execution.execution_log.append(log_entry)
                raise TimeoutError(f"Action {action_type} timed out")
            
            # Mark execution as failed if verification failed
            if not verification_result.success:
                self.logger.warning(
                    f"Action verification failed: {action_type} "
                    f"(confidence: {verification_result.confidence:.2f})"
                )
                log_entry['status'] = 'verification_failed'
                log_entry['error'] = f'Verification failed: {verification_result.error_message}'
                log_entry['verification_confidence'] = verification_result.confidence
                execution.execution_log.append(log_entry)
                # Note: We don't raise an exception here to allow workflow to continue
                # The verification result is stored for feedback loop analysis
            elif success:
                log_entry['status'] = 'completed'
                log_entry['verification_confidence'] = verification_result.confidence
            else:
                log_entry['status'] = 'failed'
                log_entry['error'] = 'Action execution returned False'
            
            execution.execution_log.append(log_entry)
            
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            log_entry['status'] = 'failed'
            log_entry['error'] = str(e)
            execution.execution_log.append(log_entry)
            raise
    
    async def _dispatch_action(self, action_type: str, action_data: Dict[str, Any]) -> bool:
        """
        Dispatch action to appropriate platform.
        
        Args:
            action_type: Type of action
            action_data: Action parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Desktop automation actions
            if action_type == 'click':
                x = action_data.get('x', 0)
                y = action_data.get('y', 0)
                button = action_data.get('button', 'left')
                clicks = action_data.get('clicks', 1)
                return await self.desktop_platform.click(x, y, button, clicks)
            
            elif action_type == 'type_text':
                text = action_data.get('text', '')
                interval = action_data.get('interval')
                return await self.desktop_platform.type_text(text, interval)
            
            elif action_type == 'press_key':
                key = action_data.get('key', '')
                presses = action_data.get('presses', 1)
                return await self.desktop_platform.press_key(key, presses)
            
            elif action_type == 'hotkey':
                keys = action_data.get('keys', [])
                return await self.desktop_platform.hotkey(*keys)
            
            elif action_type == 'move_to':
                x = action_data.get('x', 0)
                y = action_data.get('y', 0)
                duration = action_data.get('duration')
                return await self.desktop_platform.move_to(x, y, duration)
            
            elif action_type == 'drag_to':
                x = action_data.get('x', 0)
                y = action_data.get('y', 0)
                duration = action_data.get('duration')
                button = action_data.get('button', 'left')
                return await self.desktop_platform.drag_to(x, y, duration, button)
            
            elif action_type == 'scroll':
                clicks = action_data.get('clicks', 0)
                x = action_data.get('x')
                y = action_data.get('y')
                return await self.desktop_platform.scroll(clicks, x, y)
            
            elif action_type == 'wait':
                duration = action_data.get('duration', 1.0)
                await asyncio.sleep(duration)
                return True
            
            # Browser automation actions
            elif action_type == 'browser_navigate':
                url = action_data.get('url', '')
                await self._ensure_browser()
                await self.browser_platform.navigate(url)
                return True
            
            elif action_type == 'browser_click':
                selector = action_data.get('selector', '')
                await self._ensure_browser()
                await self.browser_platform.click(selector)
                return True
            
            elif action_type == 'browser_type':
                selector = action_data.get('selector', '')
                text = action_data.get('text', '')
                await self._ensure_browser()
                await self.browser_platform.type_text(selector, text)
                return True
            
            elif action_type == 'browser_fill':
                selector = action_data.get('selector', '')
                text = action_data.get('text', '')
                await self._ensure_browser()
                await self.browser_platform.fill(selector, text)
                return True
            
            elif action_type == 'browser_select':
                selector = action_data.get('selector', '')
                value = action_data.get('value', '')
                await self._ensure_browser()
                await self.browser_platform.select_option(selector, value)
                return True
            
            elif action_type == 'browser_check':
                selector = action_data.get('selector', '')
                await self._ensure_browser()
                await self.browser_platform.check(selector)
                return True
            
            elif action_type == 'browser_uncheck':
                selector = action_data.get('selector', '')
                await self._ensure_browser()
                await self.browser_platform.uncheck(selector)
                return True
            
            elif action_type == 'browser_press_key':
                key = action_data.get('key', '')
                await self._ensure_browser()
                await self.browser_platform.press_key(key)
                return True
            
            elif action_type == 'browser_get_text':
                selector = action_data.get('selector', '')
                await self._ensure_browser()
                text = await self.browser_platform.get_text(selector)
                self.logger.info(f"Extracted text: {text[:100]}...")
                return True
            
            elif action_type == 'browser_screenshot':
                path = action_data.get('path')
                full_page = action_data.get('full_page', False)
                await self._ensure_browser()
                screenshot_path = await self.browser_platform.screenshot(path, full_page)
                self.logger.info(f"Browser screenshot saved: {screenshot_path}")
                return True
            
            elif action_type == 'browser_wait_for':
                selector = action_data.get('selector', '')
                timeout = action_data.get('timeout', 30000)
                await self._ensure_browser()
                await self.browser_platform.wait_for_selector(selector, timeout)
                return True
            
            elif action_type == 'browser_fill_form':
                form_data = action_data.get('form_data', {})
                await self._ensure_browser()
                await self.browser_platform.fill_form(form_data)
                return True
            
            elif action_type == 'browser_submit_form':
                form_selector = action_data.get('form_selector', 'form')
                await self._ensure_browser()
                await self.browser_platform.submit_form(form_selector)
                return True
            
            elif action_type == 'browser_extract_table':
                selector = action_data.get('selector', '')
                await self._ensure_browser()
                table_data = await self.browser_platform.extract_table(selector)
                self.logger.info(f"Extracted table with {len(table_data)} rows")
                return True
            
            # Application automation actions - Excel
            elif action_type == 'excel_open':
                file_path = action_data.get('file_path', '')
                visible = action_data.get('visible', True)
                await self._ensure_application()
                await self.application_platform.open_excel(file_path, visible)
                return True
            
            elif action_type == 'excel_create':
                visible = action_data.get('visible', True)
                await self._ensure_application()
                await self.application_platform.create_excel(visible)
                return True
            
            elif action_type == 'excel_close':
                save = action_data.get('save', False)
                await self._ensure_application()
                await self.application_platform.close_excel(save)
                return True
            
            elif action_type == 'excel_save':
                file_path = action_data.get('file_path')
                await self._ensure_application()
                await self.application_platform.save_excel(file_path)
                return True
            
            elif action_type == 'excel_read_cell':
                sheet = action_data.get('sheet', 1)
                cell = action_data.get('cell', 'A1')
                await self._ensure_application()
                value = await self.application_platform.read_cell(sheet, cell)
                self.logger.info(f"Read cell {sheet}!{cell}: {value}")
                return True
            
            elif action_type == 'excel_write_cell':
                sheet = action_data.get('sheet', 1)
                cell = action_data.get('cell', 'A1')
                value = action_data.get('value', '')
                await self._ensure_application()
                await self.application_platform.write_cell(sheet, cell, value)
                return True
            
            elif action_type == 'excel_write_range':
                sheet = action_data.get('sheet', 1)
                start_cell = action_data.get('start_cell', 'A1')
                data = action_data.get('data', [[]])
                await self._ensure_application()
                await self.application_platform.write_range(sheet, start_cell, data)
                return True
            
            elif action_type == 'excel_insert_formula':
                sheet = action_data.get('sheet', 1)
                cell = action_data.get('cell', 'A1')
                formula = action_data.get('formula', '')
                await self._ensure_application()
                await self.application_platform.insert_formula(sheet, cell, formula)
                return True
            
            # Application automation actions - File System
            elif action_type == 'file_copy':
                source = action_data.get('source', '')
                destination = action_data.get('destination', '')
                await self._ensure_application()
                await self.application_platform.copy_file(source, destination)
                return True
            
            elif action_type == 'file_move':
                source = action_data.get('source', '')
                destination = action_data.get('destination', '')
                await self._ensure_application()
                await self.application_platform.move_file(source, destination)
                return True
            
            elif action_type == 'file_rename':
                old_path = action_data.get('old_path', '')
                new_path = action_data.get('new_path', '')
                await self._ensure_application()
                await self.application_platform.rename_file(old_path, new_path)
                return True
            
            elif action_type == 'file_delete':
                file_path = action_data.get('file_path', '')
                await self._ensure_application()
                await self.application_platform.delete_file(file_path)
                return True
            
            elif action_type == 'folder_create':
                folder_path = action_data.get('folder_path', '')
                await self._ensure_application()
                await self.application_platform.create_folder(folder_path)
                return True
            
            elif action_type == 'folder_delete':
                folder_path = action_data.get('folder_path', '')
                await self._ensure_application()
                await self.application_platform.delete_folder(folder_path)
                return True
            
            # Application automation actions - Window Management
            elif action_type == 'window_find':
                title = action_data.get('title', '')
                await self._ensure_application()
                hwnd = await self.application_platform.find_window(title)
                self.logger.info(f"Found window: {hwnd}")
                return True
            
            elif action_type == 'window_focus':
                hwnd = action_data.get('hwnd', 0)
                await self._ensure_application()
                await self.application_platform.focus_window(hwnd)
                return True
            
            elif action_type == 'window_minimize':
                hwnd = action_data.get('hwnd', 0)
                await self._ensure_application()
                await self.application_platform.minimize_window(hwnd)
                return True
            
            elif action_type == 'window_maximize':
                hwnd = action_data.get('hwnd', 0)
                await self._ensure_application()
                await self.application_platform.maximize_window(hwnd)
                return True
            
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Action dispatch failed: {e}")
            return False
    
    async def _emit_execution_event(self, execution: WorkflowExecution, event_type: EventType) -> None:
        """Emit execution event."""
        event = Event(
            type=event_type,
            timestamp=datetime.now(),
            source="automation_executor",
            data=execution.to_dict()
        )
        await self.event_bus.publish(event)
    
    async def trigger_emergency_stop(self) -> None:
        """
        Trigger emergency stop for all automations.
        
        This will immediately halt all running and queued automations.
        """
        self.logger.warning("Emergency stop triggered via AutomationExecutor")
        await self.safety_manager.trigger_emergency_stop()
        
        # Cancel current execution
        if self.current_execution:
            self.current_execution.state = ExecutionState.CANCELLED
            self.current_execution.end_time = datetime.now()
            self.current_execution.error_message = "Emergency stop triggered"
            await self._emit_execution_event(self.current_execution, EventType.WORKFLOW_EXECUTION_CANCELLED)
        
        # Clear execution queue
        for execution in self.execution_queue:
            execution.state = ExecutionState.CANCELLED
        self.execution_queue.clear()
        
        self.logger.info("All automations halted due to emergency stop")
    
    async def reset_emergency_stop(self) -> None:
        """
        Reset emergency stop to allow automations to run again.
        """
        await self.safety_manager.reset_emergency_stop()
        self.logger.info("Emergency stop reset - automations can resume")
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            if self.current_execution and self.current_execution.id == execution_id:
                self.current_execution.state = ExecutionState.CANCELLED
                self.current_execution.end_time = datetime.now()
                
                self.logger.info(f"Cancelled execution: {execution_id}")
                await self._emit_execution_event(self.current_execution, EventType.WORKFLOW_EXECUTION_CANCELLED)
                
                return True
            
            # Check queue
            for execution in self.execution_queue:
                if execution.id == execution_id:
                    execution.state = ExecutionState.CANCELLED
                    self.execution_queue.remove(execution)
                    self.logger.info(f"Removed from queue: {execution_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to cancel execution: {e}")
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status."""
        if self.current_execution and self.current_execution.id == execution_id:
            return self.current_execution.to_dict()
        
        for execution in self.execution_queue:
            if execution.id == execution_id:
                return execution.to_dict()
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            'running': self._running,
            'current_execution': self.current_execution.to_dict() if self.current_execution else None,
            'queue_size': len(self.execution_queue),
            'executions_completed': self._executions_completed,
            'executions_failed': self._executions_failed
        }
