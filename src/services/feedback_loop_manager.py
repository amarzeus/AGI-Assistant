"""Feedback Loop Manager Service.

This module provides feedback loop capabilities for automation execution:
- Analyze execution results
- Adjust workflow parameters based on verification
- Track success/failure patterns
- Suggest workflow improvements
- Update confidence scores
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

from src.config import get_config
from src.logger import get_app_logger
from src.services.execution_verifier import VerificationResult


@dataclass
class Adjustment:
    """
    Represents a workflow adjustment based on feedback analysis.
    
    Adjustments can modify timing, coordinates, selectors, or add validation steps.
    """
    action_index: int
    adjustment_type: str  # timing, coordinate, selector, validation
    old_value: Any
    new_value: Any
    reason: str
    confidence: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'action_index': self.action_index,
            'adjustment_type': self.adjustment_type,
            'old_value': str(self.old_value),
            'new_value': str(self.new_value),
            'reason': self.reason,
            'confidence': self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Adjustment':
        """Create Adjustment from dictionary."""
        return cls(
            action_index=data['action_index'],
            adjustment_type=data['adjustment_type'],
            old_value=data['old_value'],
            new_value=data['new_value'],
            reason=data['reason'],
            confidence=data.get('confidence', 0.7),
        )


@dataclass
class FeedbackAnalysis:
    """
    Result of execution feedback analysis.
    
    Contains information about execution success, detected issues,
    and suggested adjustments.
    """
    execution_id: str
    workflow_id: str
    overall_success: bool
    confidence: float  # 0.0 to 1.0
    issues_detected: List[str] = field(default_factory=list)
    suggested_adjustments: List[Adjustment] = field(default_factory=list)
    should_retry: bool = False
    retry_delay: int = 0  # seconds
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'execution_id': self.execution_id,
            'workflow_id': self.workflow_id,
            'overall_success': self.overall_success,
            'confidence': self.confidence,
            'issues_detected': self.issues_detected,
            'suggested_adjustments': [adj.to_dict() for adj in self.suggested_adjustments],
            'should_retry': self.should_retry,
            'retry_delay': self.retry_delay,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackAnalysis':
        """Create FeedbackAnalysis from dictionary."""
        return cls(
            execution_id=data['execution_id'],
            workflow_id=data['workflow_id'],
            overall_success=data['overall_success'],
            confidence=data['confidence'],
            issues_detected=data.get('issues_detected', []),
            suggested_adjustments=[
                Adjustment.from_dict(adj) for adj in data.get('suggested_adjustments', [])
            ],
            should_retry=data.get('should_retry', False),
            retry_delay=data.get('retry_delay', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {}),
        )


class FeedbackLoopManager:
    """
    Service for learning from execution results and improving workflows.
    
    Features:
    - Analyze execution results and verification data
    - Identify common failure patterns
    - Adjust workflow parameters automatically
    - Track confidence scores over time
    - Suggest improvements to users
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Execution history: workflow_id -> list of execution results
        self.execution_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Workflow adjustments: workflow_id -> list of adjustments
        self.workflow_adjustments: Dict[str, List[Adjustment]] = defaultdict(list)
        
        # Workflow confidence scores: workflow_id -> confidence
        self.workflow_confidence: Dict[str, float] = {}
        
        # Failure patterns: workflow_id -> pattern counts
        self.failure_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Settings
        self._base_confidence = 0.5
        self._confidence_increase = 0.1
        self._confidence_decrease = 0.2
        self._max_confidence = 1.0
        self._min_confidence = 0.0
        self._retry_threshold = 3  # Suggest manual review after 3 failures
        
        self.logger.info("Feedback loop manager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the feedback loop manager.
        
        Sets up any required resources and prepares for analysis.
        """
        try:
            self.logger.info("Feedback loop manager initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize feedback loop manager: {e}")
            raise
    
    async def analyze_execution(
        self,
        execution: Any,  # WorkflowExecution object
        verification_results: List[VerificationResult]
    ) -> FeedbackAnalysis:
        """
        Analyze execution results and generate feedback.
        
        Examines verification results to identify issues and suggest improvements.
        
        Args:
            execution: WorkflowExecution instance
            verification_results: List of VerificationResult objects
            
        Returns:
            FeedbackAnalysis with detected issues and suggestions
        """
        try:
            workflow_id = execution.workflow_id
            execution_id = execution.id
            
            self.logger.info(f"Analyzing execution: {execution_id}")
            
            # Calculate overall success rate
            if verification_results:
                successful_verifications = sum(1 for vr in verification_results if vr.success)
                success_rate = successful_verifications / len(verification_results)
            else:
                success_rate = 1.0 if execution.state.value == 'completed' else 0.0
            
            overall_success = success_rate >= 0.8  # 80% threshold
            
            # Calculate confidence based on verification results
            if verification_results:
                avg_confidence = sum(vr.confidence for vr in verification_results) / len(verification_results)
            else:
                avg_confidence = 0.5
            
            # Detect issues
            issues_detected = []
            suggested_adjustments = []
            
            # Analyze each verification result
            for i, vr in enumerate(verification_results):
                if not vr.success:
                    # Identify failure type
                    if vr.error_message:
                        issues_detected.append(
                            f"Action {i+1} ({vr.action_type}): {vr.error_message}"
                        )
                    else:
                        issues_detected.append(
                            f"Action {i+1} ({vr.action_type}): Verification failed "
                            f"(confidence: {vr.confidence:.2f})"
                        )
                    
                    # Detect failure patterns
                    failure_type = self._classify_failure(vr)
                    self.failure_patterns[workflow_id][failure_type] += 1
                    
                    # Generate adjustment suggestions
                    adjustment = self._suggest_adjustment(i, vr, failure_type)
                    if adjustment:
                        suggested_adjustments.append(adjustment)
            
            # Check for common patterns
            common_issues = self._identify_common_patterns(workflow_id, verification_results)
            issues_detected.extend(common_issues)
            
            # Determine if retry is recommended
            failure_count = self._get_failure_count(workflow_id)
            should_retry = not overall_success and failure_count < self._retry_threshold
            retry_delay = min(5 * (failure_count + 1), 30)  # Exponential backoff, max 30s
            
            # Create analysis
            analysis = FeedbackAnalysis(
                execution_id=execution_id,
                workflow_id=workflow_id,
                overall_success=overall_success,
                confidence=avg_confidence,
                issues_detected=issues_detected,
                suggested_adjustments=suggested_adjustments,
                should_retry=should_retry,
                retry_delay=retry_delay,
                metadata={
                    'success_rate': success_rate,
                    'verification_count': len(verification_results),
                    'failure_count': failure_count,
                    'execution_state': execution.state.value,
                }
            )
            
            # Store execution result in history
            self.execution_history[workflow_id].append({
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat(),
                'success': overall_success,
                'confidence': avg_confidence,
                'issues': len(issues_detected),
            })
            
            # Limit history size
            if len(self.execution_history[workflow_id]) > 100:
                self.execution_history[workflow_id] = self.execution_history[workflow_id][-100:]
            
            self.logger.info(
                f"Analysis complete: success={overall_success}, "
                f"confidence={avg_confidence:.2f}, issues={len(issues_detected)}"
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze execution: {e}")
            # Return minimal analysis on error
            return FeedbackAnalysis(
                execution_id=getattr(execution, 'id', 'unknown'),
                workflow_id=getattr(execution, 'workflow_id', 'unknown'),
                overall_success=False,
                confidence=0.0,
                issues_detected=[f"Analysis error: {str(e)}"],
            )
    
    def _classify_failure(self, verification_result: VerificationResult) -> str:
        """
        Classify the type of failure from verification result.
        
        Args:
            verification_result: VerificationResult object
            
        Returns:
            Failure type string (timing, coordinate, selector, validation, unknown)
        """
        # Check error message for clues
        error_msg = (verification_result.error_message or "").lower()
        
        if 'timeout' in error_msg or 'time' in error_msg:
            return 'timing'
        elif 'coordinate' in error_msg or 'position' in error_msg or 'bounds' in error_msg:
            return 'coordinate'
        elif 'selector' in error_msg or 'element' in error_msg or 'not found' in error_msg:
            return 'selector'
        elif verification_result.confidence < 0.5:
            # Low confidence suggests validation issue
            return 'validation'
        else:
            return 'unknown'
    
    def _suggest_adjustment(
        self,
        action_index: int,
        verification_result: VerificationResult,
        failure_type: str
    ) -> Optional[Adjustment]:
        """
        Suggest an adjustment based on failure type.
        
        Args:
            action_index: Index of failed action
            verification_result: VerificationResult object
            failure_type: Type of failure
            
        Returns:
            Adjustment object or None
        """
        try:
            if failure_type == 'timing':
                # Suggest adding delay
                return Adjustment(
                    action_index=action_index,
                    adjustment_type='timing',
                    old_value='0.5s',
                    new_value='2.0s',
                    reason='Increase delay to allow UI to update',
                    confidence=0.8
                )
            
            elif failure_type == 'coordinate':
                # Suggest coordinate adjustment
                metadata = verification_result.metadata or {}
                click_loc = metadata.get('click_location', {})
                if click_loc:
                    return Adjustment(
                        action_index=action_index,
                        adjustment_type='coordinate',
                        old_value=f"({click_loc.get('x', 0)}, {click_loc.get('y', 0)})",
                        new_value=f"({click_loc.get('x', 0) + 5}, {click_loc.get('y', 0) + 5})",
                        reason='Adjust click position based on verification',
                        confidence=0.6
                    )
            
            elif failure_type == 'selector':
                # Suggest trying alternative selector
                return Adjustment(
                    action_index=action_index,
                    adjustment_type='selector',
                    old_value='current_selector',
                    new_value='alternative_selector',
                    reason='Try alternative element selector',
                    confidence=0.5
                )
            
            elif failure_type == 'validation':
                # Suggest adding verification step
                return Adjustment(
                    action_index=action_index,
                    adjustment_type='validation',
                    old_value='none',
                    new_value='add_wait_and_verify',
                    reason='Add explicit wait and verification step',
                    confidence=0.7
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to suggest adjustment: {e}")
            return None
    
    def _identify_common_patterns(
        self,
        workflow_id: str,
        verification_results: List[VerificationResult]
    ) -> List[str]:
        """
        Identify common failure patterns across executions.
        
        Args:
            workflow_id: Workflow identifier
            verification_results: List of verification results
            
        Returns:
            List of common pattern descriptions
        """
        patterns = []
        
        # Check failure pattern counts
        pattern_counts = self.failure_patterns.get(workflow_id, {})
        
        for pattern_type, count in pattern_counts.items():
            if count >= 3:
                patterns.append(
                    f"Recurring {pattern_type} issues detected ({count} times)"
                )
        
        # Check for consistent low confidence
        if verification_results:
            low_confidence_count = sum(
                1 for vr in verification_results if vr.confidence < 0.6
            )
            if low_confidence_count > len(verification_results) * 0.5:
                patterns.append(
                    "Multiple actions have low verification confidence"
                )
        
        return patterns
    
    def _get_failure_count(self, workflow_id: str) -> int:
        """
        Get consecutive failure count for workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Number of consecutive failures
        """
        history = self.execution_history.get(workflow_id, [])
        if not history:
            return 0
        
        # Count consecutive failures from most recent
        failure_count = 0
        for execution in reversed(history):
            if not execution.get('success', False):
                failure_count += 1
            else:
                break
        
        return failure_count
    
    async def adjust_workflow(
        self,
        workflow_id: str,
        workflow_data: Dict[str, Any],
        analysis: FeedbackAnalysis
    ) -> Dict[str, Any]:
        """
        Adjust workflow based on feedback analysis.
        
        Applies suggested adjustments to workflow data, modifying timing,
        coordinates, selectors, and adding validation steps as needed.
        
        Args:
            workflow_id: Workflow identifier
            workflow_data: Original workflow data dictionary
            analysis: FeedbackAnalysis with suggestions
            
        Returns:
            Adjusted workflow data dictionary with modifications applied
        """
        try:
            self.logger.info(f"Adjusting workflow: {workflow_id}")
            
            # Create a deep copy of workflow data to modify
            import copy
            adjusted_workflow = copy.deepcopy(workflow_data)
            
            # Get the actions/steps list (handle both 'actions' and 'steps' keys)
            actions_key = 'actions' if 'actions' in adjusted_workflow else 'steps'
            actions = adjusted_workflow.get(actions_key, [])
            
            if not actions:
                self.logger.warning(f"No actions found in workflow {workflow_id}")
                return adjusted_workflow
            
            # Track applied adjustments
            adjustments_applied = []
            
            # Apply each suggested adjustment
            for adjustment in analysis.suggested_adjustments:
                action_index = adjustment.action_index
                
                # Validate action index
                if action_index < 0 or action_index >= len(actions):
                    self.logger.warning(
                        f"Invalid action index {action_index} for workflow with "
                        f"{len(actions)} actions"
                    )
                    continue
                
                action = actions[action_index]
                
                # Apply adjustment based on type
                if adjustment.adjustment_type == 'timing':
                    action = self._apply_timing_adjustment(action, adjustment)
                    adjustments_applied.append(adjustment)
                    
                elif adjustment.adjustment_type == 'coordinate':
                    action = self._apply_coordinate_adjustment(action, adjustment)
                    adjustments_applied.append(adjustment)
                    
                elif adjustment.adjustment_type == 'selector':
                    action = self._apply_selector_adjustment(action, adjustment)
                    adjustments_applied.append(adjustment)
                    
                elif adjustment.adjustment_type == 'validation':
                    # Validation adjustments may add new steps
                    new_actions = self._apply_validation_adjustment(
                        actions, action_index, adjustment
                    )
                    if new_actions:
                        actions = new_actions
                        adjustments_applied.append(adjustment)
                else:
                    self.logger.warning(
                        f"Unknown adjustment type: {adjustment.adjustment_type}"
                    )
                    continue
                
                # Update the action in the list
                actions[action_index] = action
                
                self.logger.debug(
                    f"Applied {adjustment.adjustment_type} adjustment to action {action_index}"
                )
            
            # Update the workflow with adjusted actions
            adjusted_workflow[actions_key] = actions
            
            # Store adjustments in history
            for adjustment in adjustments_applied:
                self.workflow_adjustments[workflow_id].append(adjustment)
            
            # Limit adjustment history
            if len(self.workflow_adjustments[workflow_id]) > 50:
                self.workflow_adjustments[workflow_id] = \
                    self.workflow_adjustments[workflow_id][-50:]
            
            # Add metadata about adjustments
            if 'metadata' not in adjusted_workflow:
                adjusted_workflow['metadata'] = {}
            
            adjusted_workflow['metadata']['last_adjusted'] = datetime.now().isoformat()
            adjusted_workflow['metadata']['adjustments_count'] = len(adjustments_applied)
            adjusted_workflow['metadata']['adjustment_history'] = [
                adj.to_dict() for adj in adjustments_applied
            ]
            
            self.logger.info(
                f"Applied {len(adjustments_applied)} adjustments to workflow {workflow_id}"
            )
            
            return adjusted_workflow
            
        except Exception as e:
            self.logger.error(f"Failed to adjust workflow: {e}")
            # Return original workflow on error
            return workflow_data
    
    def _apply_timing_adjustment(
        self,
        action: Dict[str, Any],
        adjustment: Adjustment
    ) -> Dict[str, Any]:
        """
        Apply timing adjustment to action.
        
        Increases delays or adds wait times to allow UI to update.
        
        Args:
            action: Action dictionary
            adjustment: Adjustment to apply
            
        Returns:
            Modified action dictionary
        """
        try:
            # Parse new delay value (e.g., "2.0s" -> 2.0)
            new_delay_str = str(adjustment.new_value)
            new_delay = float(new_delay_str.rstrip('s'))
            
            # Add or update delay field
            if 'delay_after' not in action:
                action['delay_after'] = new_delay
            else:
                # Increase existing delay
                current_delay = float(action.get('delay_after', 0))
                action['delay_after'] = max(current_delay, new_delay)
            
            # Add adjustment note
            if 'adjustment_notes' not in action:
                action['adjustment_notes'] = []
            action['adjustment_notes'].append(
                f"Timing adjusted: delay increased to {new_delay}s - {adjustment.reason}"
            )
            
            self.logger.debug(f"Applied timing adjustment: delay={new_delay}s")
            
        except Exception as e:
            self.logger.error(f"Failed to apply timing adjustment: {e}")
        
        return action
    
    def _apply_coordinate_adjustment(
        self,
        action: Dict[str, Any],
        adjustment: Adjustment
    ) -> Dict[str, Any]:
        """
        Apply coordinate adjustment to action.
        
        Shifts click positions based on verification feedback.
        
        Args:
            action: Action dictionary
            adjustment: Adjustment to apply
            
        Returns:
            Modified action dictionary
        """
        try:
            # Parse new coordinates (e.g., "(100, 200)" -> (100, 200))
            new_coords_str = str(adjustment.new_value)
            new_coords_str = new_coords_str.strip('()')
            x_str, y_str = new_coords_str.split(',')
            new_x = int(x_str.strip())
            new_y = int(y_str.strip())
            
            # Update coordinates
            if 'coordinates' in action:
                action['coordinates']['x'] = new_x
                action['coordinates']['y'] = new_y
            elif 'target' in action and isinstance(action['target'], dict):
                if 'coordinates' in action['target']:
                    action['target']['coordinates']['x'] = new_x
                    action['target']['coordinates']['y'] = new_y
                else:
                    action['target']['coordinates'] = {'x': new_x, 'y': new_y}
            else:
                # Create coordinates field
                action['coordinates'] = {'x': new_x, 'y': new_y}
            
            # Add adjustment note
            if 'adjustment_notes' not in action:
                action['adjustment_notes'] = []
            action['adjustment_notes'].append(
                f"Coordinates adjusted: ({new_x}, {new_y}) - {adjustment.reason}"
            )
            
            self.logger.debug(f"Applied coordinate adjustment: ({new_x}, {new_y})")
            
        except Exception as e:
            self.logger.error(f"Failed to apply coordinate adjustment: {e}")
        
        return action
    
    def _apply_selector_adjustment(
        self,
        action: Dict[str, Any],
        adjustment: Adjustment
    ) -> Dict[str, Any]:
        """
        Apply selector adjustment to action.
        
        Updates element selectors for browser or application automation.
        
        Args:
            action: Action dictionary
            adjustment: Adjustment to apply
            
        Returns:
            Modified action dictionary
        """
        try:
            new_selector = str(adjustment.new_value)
            
            # Update selector in various possible locations
            if 'selector' in action:
                action['selector_backup'] = action['selector']
                action['selector'] = new_selector
            elif 'target' in action and isinstance(action['target'], dict):
                if 'selector' in action['target']:
                    action['target']['selector_backup'] = action['target']['selector']
                    action['target']['selector'] = new_selector
                else:
                    action['target']['selector'] = new_selector
            else:
                # Add selector field
                action['selector'] = new_selector
            
            # Add adjustment note
            if 'adjustment_notes' not in action:
                action['adjustment_notes'] = []
            action['adjustment_notes'].append(
                f"Selector adjusted: {new_selector} - {adjustment.reason}"
            )
            
            self.logger.debug(f"Applied selector adjustment: {new_selector}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply selector adjustment: {e}")
        
        return action
    
    def _apply_validation_adjustment(
        self,
        actions: List[Dict[str, Any]],
        action_index: int,
        adjustment: Adjustment
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Apply validation adjustment to workflow.
        
        Adds explicit wait and verification steps after the action.
        
        Args:
            actions: List of action dictionaries
            action_index: Index of action to add validation after
            adjustment: Adjustment to apply
            
        Returns:
            Modified actions list with validation step added, or None on error
        """
        try:
            # Create a wait step
            wait_step = {
                'action': 'wait',
                'duration': 1.0,  # 1 second wait
                'description': 'Wait for UI to update after previous action',
                'added_by_feedback': True,
                'adjustment_reason': adjustment.reason,
            }
            
            # Create a verification step
            verify_step = {
                'action': 'verify',
                'verify_previous_action': True,
                'description': 'Verify previous action completed successfully',
                'added_by_feedback': True,
                'adjustment_reason': adjustment.reason,
            }
            
            # Insert steps after the target action
            insert_index = action_index + 1
            actions.insert(insert_index, wait_step)
            actions.insert(insert_index + 1, verify_step)
            
            # Update step numbers if they exist
            for i, action in enumerate(actions):
                if 'step' in action:
                    action['step'] = i + 1
            
            self.logger.debug(
                f"Added validation steps after action {action_index}"
            )
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Failed to apply validation adjustment: {e}")
            return None
    
    async def update_confidence(
        self,
        workflow_id: str,
        success: bool
    ) -> float:
        """
        Update workflow confidence score based on execution result.
        
        Confidence increases with success, decreases with failure.
        
        Args:
            workflow_id: Workflow identifier
            success: Whether execution was successful
            
        Returns:
            Updated confidence score (0.0 to 1.0)
        """
        try:
            # Get current confidence or start with base
            current_confidence = self.workflow_confidence.get(
                workflow_id,
                self._base_confidence
            )
            
            # Adjust confidence
            if success:
                new_confidence = min(
                    self._max_confidence,
                    current_confidence + self._confidence_increase
                )
                self.logger.debug(
                    f"Confidence increased: {current_confidence:.2f} -> {new_confidence:.2f}"
                )
            else:
                new_confidence = max(
                    self._min_confidence,
                    current_confidence - self._confidence_decrease
                )
                self.logger.debug(
                    f"Confidence decreased: {current_confidence:.2f} -> {new_confidence:.2f}"
                )
            
            # Store updated confidence
            self.workflow_confidence[workflow_id] = new_confidence
            
            return new_confidence
            
        except Exception as e:
            self.logger.error(f"Failed to update confidence: {e}")
            return self._base_confidence
    
    async def suggest_improvements(
        self,
        workflow_id: str
    ) -> List[str]:
        """
        Generate improvement suggestions for workflow.
        
        Analyzes execution history and patterns to suggest improvements.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            List of improvement suggestion strings
        """
        try:
            suggestions = []
            
            # Get execution history
            history = self.execution_history.get(workflow_id, [])
            if not history:
                return ["No execution history available for analysis"]
            
            # Calculate success rate
            recent_history = history[-10:]  # Last 10 executions
            success_count = sum(1 for h in recent_history if h.get('success', False))
            success_rate = success_count / len(recent_history)
            
            # Suggest based on success rate
            if success_rate < 0.5:
                suggestions.append(
                    "Low success rate detected. Consider manual review of workflow steps."
                )
            
            # Check failure patterns
            pattern_counts = self.failure_patterns.get(workflow_id, {})
            
            if pattern_counts.get('timing', 0) >= 3:
                suggestions.append(
                    "Add wait steps between actions to allow UI to update"
                )
            
            if pattern_counts.get('coordinate', 0) >= 3:
                suggestions.append(
                    "Use relative positioning or element detection instead of fixed coordinates"
                )
            
            if pattern_counts.get('selector', 0) >= 3:
                suggestions.append(
                    "Update element selectors - target elements may have changed"
                )
            
            if pattern_counts.get('validation', 0) >= 3:
                suggestions.append(
                    "Add explicit verification steps after critical actions"
                )
            
            # Check for repeated failures
            failure_count = self._get_failure_count(workflow_id)
            if failure_count >= self._retry_threshold:
                suggestions.append(
                    f"Workflow has failed {failure_count} times consecutively. "
                    "Manual review recommended."
                )
            
            # Check for hardcoded values
            adjustments = self.workflow_adjustments.get(workflow_id, [])
            if len(adjustments) > 10:
                suggestions.append(
                    "Consider parameterizing workflow values for better reusability"
                )
            
            # Check confidence
            confidence = self.workflow_confidence.get(workflow_id, self._base_confidence)
            if confidence < 0.3:
                suggestions.append(
                    "Very low confidence score. Workflow may need significant revision."
                )
            
            if not suggestions:
                suggestions.append(
                    "Workflow is performing well. No improvements suggested at this time."
                )
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to suggest improvements: {e}")
            return [f"Error generating suggestions: {str(e)}"]
    
    def get_workflow_stats(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get statistics for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Dictionary with workflow statistics
        """
        history = self.execution_history.get(workflow_id, [])
        
        if not history:
            return {
                'workflow_id': workflow_id,
                'execution_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'success_rate': 0.0,
                'confidence': self._base_confidence,
                'adjustments_made': 0,
            }
        
        success_count = sum(1 for h in history if h.get('success', False))
        failure_count = len(history) - success_count
        
        return {
            'workflow_id': workflow_id,
            'execution_count': len(history),
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_count / len(history),
            'confidence': self.workflow_confidence.get(workflow_id, self._base_confidence),
            'adjustments_made': len(self.workflow_adjustments.get(workflow_id, [])),
            'consecutive_failures': self._get_failure_count(workflow_id),
        }
    
    def clear_history(self, workflow_id: Optional[str] = None) -> None:
        """
        Clear execution history and adjustments.
        
        Args:
            workflow_id: Workflow identifier, or None to clear all
        """
        if workflow_id:
            self.execution_history.pop(workflow_id, None)
            self.workflow_adjustments.pop(workflow_id, None)
            self.workflow_confidence.pop(workflow_id, None)
            self.failure_patterns.pop(workflow_id, None)
            self.logger.info(f"Cleared history for workflow: {workflow_id}")
        else:
            self.execution_history.clear()
            self.workflow_adjustments.clear()
            self.workflow_confidence.clear()
            self.failure_patterns.clear()
            self.logger.info("Cleared all workflow history")
