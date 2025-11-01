"""Tests for FeedbackLoopManager service."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.services.feedback_loop_manager import (
    FeedbackLoopManager,
    FeedbackAnalysis,
    Adjustment
)
from src.services.execution_verifier import VerificationResult


@pytest.fixture
def feedback_manager():
    """Create feedback loop manager for testing."""
    return FeedbackLoopManager()


@pytest.fixture
def mock_execution():
    """Create mock workflow execution."""
    execution = Mock()
    execution.id = "exec_test_001"
    execution.workflow_id = "workflow_001"
    execution.state = Mock()
    execution.state.value = "completed"
    execution.verification_results = []
    return execution


@pytest.fixture
def successful_verification():
    """Create successful verification result."""
    return VerificationResult(
        action_id="action_001",
        action_type="click",
        success=True,
        confidence=0.9,
        verification_method="region_comparison"
    )


@pytest.fixture
def failed_verification():
    """Create failed verification result."""
    return VerificationResult(
        action_id="action_002",
        action_type="type",
        success=False,
        confidence=0.3,
        error_message="Verification failed: text not found",
        verification_method="image_comparison"
    )


@pytest.mark.asyncio
async def test_initialize(feedback_manager):
    """Test feedback loop manager initialization."""
    await feedback_manager.initialize()
    # Should complete without errors


@pytest.mark.asyncio
async def test_analyze_execution_all_successful(
    feedback_manager,
    mock_execution,
    successful_verification
):
    """Test analyzing execution with all successful verifications."""
    verification_results = [successful_verification] * 5
    
    analysis = await feedback_manager.analyze_execution(
        mock_execution,
        verification_results
    )
    
    assert analysis.execution_id == mock_execution.id
    assert analysis.workflow_id == mock_execution.workflow_id
    assert analysis.overall_success == True
    assert analysis.confidence > 0.8
    assert len(analysis.issues_detected) == 0
    assert len(analysis.suggested_adjustments) == 0


@pytest.mark.asyncio
async def test_analyze_execution_with_failures(
    feedback_manager,
    mock_execution,
    successful_verification,
    failed_verification
):
    """Test analyzing execution with some failures."""
    verification_results = [
        successful_verification,
        failed_verification,
        successful_verification
    ]
    
    analysis = await feedback_manager.analyze_execution(
        mock_execution,
        verification_results
    )
    
    assert analysis.execution_id == mock_execution.id
    assert analysis.workflow_id == mock_execution.workflow_id
    assert analysis.overall_success == False  # 66% success rate < 80% threshold
    assert len(analysis.issues_detected) > 0
    assert len(analysis.suggested_adjustments) > 0


@pytest.mark.asyncio
async def test_analyze_execution_no_verifications(
    feedback_manager,
    mock_execution
):
    """Test analyzing execution with no verification results."""
    verification_results = []
    
    analysis = await feedback_manager.analyze_execution(
        mock_execution,
        verification_results
    )
    
    assert analysis.execution_id == mock_execution.id
    assert analysis.workflow_id == mock_execution.workflow_id
    assert analysis.overall_success == True  # Defaults to execution state
    assert analysis.confidence == 0.5  # Default confidence


@pytest.mark.asyncio
async def test_update_confidence_success(feedback_manager):
    """Test updating confidence after successful execution."""
    workflow_id = "workflow_001"
    
    # Initial confidence should be base (0.5)
    confidence = await feedback_manager.update_confidence(workflow_id, True)
    assert confidence == 0.6  # 0.5 + 0.1
    
    # Another success
    confidence = await feedback_manager.update_confidence(workflow_id, True)
    assert confidence == 0.7  # 0.6 + 0.1


@pytest.mark.asyncio
async def test_update_confidence_failure(feedback_manager):
    """Test updating confidence after failed execution."""
    workflow_id = "workflow_001"
    
    # Initial confidence should be base (0.5)
    confidence = await feedback_manager.update_confidence(workflow_id, False)
    assert abs(confidence - 0.3) < 0.01  # 0.5 - 0.2 (allow floating point tolerance)
    
    # Another failure
    confidence = await feedback_manager.update_confidence(workflow_id, False)
    assert abs(confidence - 0.1) < 0.01  # 0.3 - 0.2 (allow floating point tolerance)


@pytest.mark.asyncio
async def test_update_confidence_bounds(feedback_manager):
    """Test confidence stays within bounds (0.0 to 1.0)."""
    workflow_id = "workflow_001"
    
    # Test upper bound
    for _ in range(10):
        confidence = await feedback_manager.update_confidence(workflow_id, True)
    assert confidence <= 1.0
    
    # Test lower bound
    workflow_id_2 = "workflow_002"
    for _ in range(10):
        confidence = await feedback_manager.update_confidence(workflow_id_2, False)
    assert confidence >= 0.0


@pytest.mark.asyncio
async def test_adjust_workflow(feedback_manager, mock_execution):
    """Test adjusting workflow based on analysis."""
    workflow_id = "workflow_001"
    
    # Create sample workflow data
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            },
            {
                'action': 'type',
                'text': 'Hello',
                'description': 'Type text'
            }
        ]
    }
    
    # Create analysis with adjustments
    analysis = FeedbackAnalysis(
        execution_id=mock_execution.id,
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='2.0s',
                reason='Increase delay'
            ),
            Adjustment(
                action_index=1,
                adjustment_type='coordinate',
                old_value='(100, 100)',
                new_value='(105, 105)',
                reason='Adjust position'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify workflow was adjusted
    assert result['id'] == workflow_id
    assert 'metadata' in result
    assert result['metadata']['adjustments_count'] == 2
    
    # Verify timing adjustment was applied to action 0
    assert 'delay_after' in result['actions'][0]
    assert result['actions'][0]['delay_after'] == 2.0
    
    # Verify coordinate adjustment was applied to action 1
    assert 'coordinates' in result['actions'][1]
    assert result['actions'][1]['coordinates']['x'] == 105
    assert result['actions'][1]['coordinates']['y'] == 105
    
    # Verify adjustments were stored
    assert len(feedback_manager.workflow_adjustments[workflow_id]) == 2


@pytest.mark.asyncio
async def test_suggest_improvements_no_history(feedback_manager):
    """Test suggesting improvements with no execution history."""
    workflow_id = "workflow_001"
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert "No execution history" in suggestions[0]


@pytest.mark.asyncio
async def test_suggest_improvements_low_success_rate(
    feedback_manager,
    mock_execution,
    failed_verification
):
    """Test suggesting improvements with low success rate."""
    workflow_id = "workflow_001"
    
    # Add multiple failed executions to history
    for i in range(5):
        mock_execution.id = f"exec_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [failed_verification]
        )
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert any("Low success rate" in s for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_improvements_timing_issues(
    feedback_manager,
    mock_execution
):
    """Test suggesting improvements for timing issues."""
    workflow_id = "workflow_001"
    
    # Create verification with timing failure
    timing_failure = VerificationResult(
        action_id="action_001",
        action_type="click",
        success=False,
        confidence=0.3,
        error_message="timeout detected",
        verification_method="region_comparison"
    )
    
    # Add multiple executions with timing failures
    for i in range(4):
        mock_execution.id = f"exec_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [timing_failure]
        )
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert any("wait" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_improvements_coordinate_issues(
    feedback_manager,
    mock_execution
):
    """Test suggesting improvements for coordinate issues."""
    workflow_id = "workflow_001"
    
    # Create verification with coordinate failure
    coord_failure = VerificationResult(
        action_id="action_001",
        action_type="click",
        success=False,
        confidence=0.3,
        error_message="coordinate out of bounds",
        verification_method="region_comparison"
    )
    
    # Add multiple executions with coordinate failures
    for i in range(4):
        mock_execution.id = f"exec_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [coord_failure]
        )
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert any("position" in s.lower() or "coordinate" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_improvements_repeated_failures(
    feedback_manager,
    mock_execution,
    failed_verification
):
    """Test suggesting manual review after repeated failures."""
    workflow_id = "workflow_001"
    
    # Add multiple consecutive failures
    for i in range(5):
        mock_execution.id = f"exec_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [failed_verification]
        )
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert any("manual review" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_suggest_improvements_parameterization(
    feedback_manager,
    mock_execution,
    successful_verification
):
    """Test suggesting parameterization after many adjustments."""
    workflow_id = "workflow_001"
    
    # Create sample workflow data
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            }
        ]
    }
    
    # Add execution history first (needed for suggestions)
    for i in range(5):
        mock_execution.id = f"exec_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [successful_verification]
        )
    
    # Add many adjustments
    for i in range(15):
        analysis = FeedbackAnalysis(
            execution_id=f"exec_{i}",
            workflow_id=workflow_id,
            overall_success=True,
            confidence=0.8,
            suggested_adjustments=[
                Adjustment(
                    action_index=0,
                    adjustment_type='timing',
                    old_value='0.5s',
                    new_value='1.0s',
                    reason='Adjust timing'
                )
            ]
        )
        await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    suggestions = await feedback_manager.suggest_improvements(workflow_id)
    
    assert len(suggestions) > 0
    assert any("parameter" in s.lower() for s in suggestions)


@pytest.mark.asyncio
async def test_get_workflow_stats_no_history(feedback_manager):
    """Test getting stats for workflow with no history."""
    workflow_id = "workflow_001"
    
    stats = feedback_manager.get_workflow_stats(workflow_id)
    
    assert stats['workflow_id'] == workflow_id
    assert stats['execution_count'] == 0
    assert stats['success_count'] == 0
    assert stats['failure_count'] == 0
    assert stats['success_rate'] == 0.0
    assert stats['confidence'] == 0.5  # Base confidence


@pytest.mark.asyncio
async def test_get_workflow_stats_with_history(
    feedback_manager,
    mock_execution,
    successful_verification,
    failed_verification
):
    """Test getting stats for workflow with execution history."""
    workflow_id = "workflow_001"
    
    # Add successful execution
    mock_execution.id = "exec_001"
    await feedback_manager.analyze_execution(
        mock_execution,
        [successful_verification] * 3
    )
    await feedback_manager.update_confidence(workflow_id, True)
    
    # Add failed execution
    mock_execution.id = "exec_002"
    await feedback_manager.analyze_execution(
        mock_execution,
        [failed_verification] * 3
    )
    await feedback_manager.update_confidence(workflow_id, False)
    
    stats = feedback_manager.get_workflow_stats(workflow_id)
    
    assert stats['workflow_id'] == workflow_id
    assert stats['execution_count'] == 2
    assert stats['success_count'] == 1
    assert stats['failure_count'] == 1
    assert stats['success_rate'] == 0.5
    assert stats['confidence'] > 0.0


@pytest.mark.asyncio
async def test_clear_history_specific_workflow(
    feedback_manager,
    mock_execution,
    successful_verification
):
    """Test clearing history for specific workflow."""
    workflow_id_1 = "workflow_001"
    workflow_id_2 = "workflow_002"
    
    # Add history for both workflows
    mock_execution.workflow_id = workflow_id_1
    await feedback_manager.analyze_execution(
        mock_execution,
        [successful_verification]
    )
    
    mock_execution.workflow_id = workflow_id_2
    await feedback_manager.analyze_execution(
        mock_execution,
        [successful_verification]
    )
    
    # Clear only workflow_001
    feedback_manager.clear_history(workflow_id_1)
    
    # Verify workflow_001 cleared
    assert workflow_id_1 not in feedback_manager.execution_history
    
    # Verify workflow_002 still has history
    assert workflow_id_2 in feedback_manager.execution_history


@pytest.mark.asyncio
async def test_clear_history_all_workflows(
    feedback_manager,
    mock_execution,
    successful_verification
):
    """Test clearing history for all workflows."""
    # Add history for multiple workflows
    for i in range(3):
        mock_execution.workflow_id = f"workflow_{i}"
        await feedback_manager.analyze_execution(
            mock_execution,
            [successful_verification]
        )
    
    # Clear all history
    feedback_manager.clear_history()
    
    # Verify all cleared
    assert len(feedback_manager.execution_history) == 0
    assert len(feedback_manager.workflow_adjustments) == 0
    assert len(feedback_manager.workflow_confidence) == 0


@pytest.mark.asyncio
async def test_failure_pattern_tracking(
    feedback_manager,
    mock_execution
):
    """Test tracking of failure patterns."""
    workflow_id = "workflow_001"
    
    # Create different types of failures
    timing_failure = VerificationResult(
        action_id="action_001",
        action_type="click",
        success=False,
        confidence=0.3,
        error_message="timeout",
        verification_method="region_comparison"
    )
    
    coord_failure = VerificationResult(
        action_id="action_002",
        action_type="click",
        success=False,
        confidence=0.3,
        error_message="coordinate issue",
        verification_method="region_comparison"
    )
    
    # Add executions with different failure types
    mock_execution.id = "exec_001"
    await feedback_manager.analyze_execution(
        mock_execution,
        [timing_failure]
    )
    
    mock_execution.id = "exec_002"
    await feedback_manager.analyze_execution(
        mock_execution,
        [timing_failure]
    )
    
    mock_execution.id = "exec_003"
    await feedback_manager.analyze_execution(
        mock_execution,
        [coord_failure]
    )
    
    # Verify patterns were tracked
    patterns = feedback_manager.failure_patterns[workflow_id]
    assert patterns['timing'] == 2
    assert patterns['coordinate'] == 1


@pytest.mark.asyncio
async def test_adjustment_data_classes():
    """Test Adjustment data class serialization."""
    adjustment = Adjustment(
        action_index=0,
        adjustment_type='timing',
        old_value='0.5s',
        new_value='2.0s',
        reason='Test adjustment',
        confidence=0.8
    )
    
    # Test to_dict
    adj_dict = adjustment.to_dict()
    assert adj_dict['action_index'] == 0
    assert adj_dict['adjustment_type'] == 'timing'
    assert adj_dict['confidence'] == 0.8
    
    # Test from_dict
    restored = Adjustment.from_dict(adj_dict)
    assert restored.action_index == adjustment.action_index
    assert restored.adjustment_type == adjustment.adjustment_type
    assert restored.confidence == adjustment.confidence


@pytest.mark.asyncio
async def test_feedback_analysis_data_classes():
    """Test FeedbackAnalysis data class serialization."""
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id="workflow_001",
        overall_success=True,
        confidence=0.9,
        issues_detected=["Issue 1", "Issue 2"],
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='2.0s',
                reason='Test'
            )
        ],
        should_retry=False,
        retry_delay=0
    )
    
    # Test to_dict
    analysis_dict = analysis.to_dict()
    assert analysis_dict['execution_id'] == "exec_001"
    assert analysis_dict['overall_success'] == True
    assert len(analysis_dict['issues_detected']) == 2
    assert len(analysis_dict['suggested_adjustments']) == 1
    
    # Test from_dict
    restored = FeedbackAnalysis.from_dict(analysis_dict)
    assert restored.execution_id == analysis.execution_id
    assert restored.overall_success == analysis.overall_success
    assert len(restored.issues_detected) == len(analysis.issues_detected)



@pytest.mark.asyncio
async def test_adjust_workflow_timing_adjustment(feedback_manager):
    """Test timing adjustment modifies delay_after field."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='2.5s',
                reason='Increase delay for UI update'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify timing adjustment
    assert 'delay_after' in result['actions'][0]
    assert result['actions'][0]['delay_after'] == 2.5
    assert 'adjustment_notes' in result['actions'][0]
    assert any('Timing adjusted' in note for note in result['actions'][0]['adjustment_notes'])


@pytest.mark.asyncio
async def test_adjust_workflow_coordinate_adjustment(feedback_manager):
    """Test coordinate adjustment modifies click positions."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 200},
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='coordinate',
                old_value='(100, 200)',
                new_value='(110, 210)',
                reason='Adjust click position'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify coordinate adjustment
    assert result['actions'][0]['coordinates']['x'] == 110
    assert result['actions'][0]['coordinates']['y'] == 210
    assert 'adjustment_notes' in result['actions'][0]
    assert any('Coordinates adjusted' in note for note in result['actions'][0]['adjustment_notes'])


@pytest.mark.asyncio
async def test_adjust_workflow_selector_adjustment(feedback_manager):
    """Test selector adjustment modifies element selectors."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'selector': '#old-button',
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='selector',
                old_value='#old-button',
                new_value='#new-button',
                reason='Update element selector'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify selector adjustment
    assert result['actions'][0]['selector'] == '#new-button'
    assert result['actions'][0]['selector_backup'] == '#old-button'
    assert 'adjustment_notes' in result['actions'][0]
    assert any('Selector adjusted' in note for note in result['actions'][0]['adjustment_notes'])


@pytest.mark.asyncio
async def test_adjust_workflow_validation_adjustment(feedback_manager):
    """Test validation adjustment adds wait and verify steps."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            },
            {
                'action': 'type',
                'text': 'Hello',
                'description': 'Type text'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='validation',
                old_value='none',
                new_value='add_wait_and_verify',
                reason='Add verification step'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify validation steps were added
    assert len(result['actions']) == 4  # Original 2 + wait + verify
    assert result['actions'][1]['action'] == 'wait'
    assert result['actions'][2]['action'] == 'verify'
    assert result['actions'][1]['added_by_feedback'] == True
    assert result['actions'][2]['added_by_feedback'] == True


@pytest.mark.asyncio
async def test_adjust_workflow_multiple_adjustments(feedback_manager):
    """Test applying multiple different adjustment types."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            },
            {
                'action': 'type',
                'text': 'Hello',
                'description': 'Type text'
            },
            {
                'action': 'click',
                'selector': '#submit',
                'description': 'Submit form'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='1.5s',
                reason='Increase delay'
            ),
            Adjustment(
                action_index=1,
                adjustment_type='coordinate',
                old_value='(100, 100)',
                new_value='(105, 105)',
                reason='Adjust position'
            ),
            Adjustment(
                action_index=2,
                adjustment_type='selector',
                old_value='#submit',
                new_value='button[type="submit"]',
                reason='Update selector'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify all adjustments were applied
    assert result['actions'][0]['delay_after'] == 1.5
    assert result['actions'][1]['coordinates']['x'] == 105
    assert result['actions'][2]['selector'] == 'button[type="submit"]'
    assert result['metadata']['adjustments_count'] == 3


@pytest.mark.asyncio
async def test_adjust_workflow_invalid_action_index(feedback_manager):
    """Test handling of invalid action index."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=10,  # Invalid index
                adjustment_type='timing',
                old_value='0.5s',
                new_value='2.0s',
                reason='Increase delay'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Should return workflow unchanged (no crash)
    assert len(result['actions']) == 1
    assert 'delay_after' not in result['actions'][0]


@pytest.mark.asyncio
async def test_adjust_workflow_with_steps_key(feedback_manager):
    """Test adjustment works with 'steps' key instead of 'actions'."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'steps': [  # Using 'steps' instead of 'actions'
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='2.0s',
                reason='Increase delay'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify adjustment was applied to 'steps'
    assert 'steps' in result
    assert result['steps'][0]['delay_after'] == 2.0


@pytest.mark.asyncio
async def test_adjust_workflow_stores_adjustment_history(feedback_manager):
    """Test that adjustments are stored in history."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'coordinates': {'x': 100, 'y': 100},
                'description': 'Click button'
            }
        ]
    }
    
    # Apply first adjustment
    analysis1 = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='0.5s',
                new_value='1.0s',
                reason='First adjustment'
            )
        ]
    )
    
    await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis1)
    
    # Apply second adjustment
    analysis2 = FeedbackAnalysis(
        execution_id="exec_002",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='timing',
                old_value='1.0s',
                new_value='2.0s',
                reason='Second adjustment'
            )
        ]
    )
    
    await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis2)
    
    # Verify both adjustments are in history
    assert len(feedback_manager.workflow_adjustments[workflow_id]) == 2
    assert feedback_manager.workflow_adjustments[workflow_id][0].reason == 'First adjustment'
    assert feedback_manager.workflow_adjustments[workflow_id][1].reason == 'Second adjustment'


@pytest.mark.asyncio
async def test_adjust_workflow_coordinate_in_target(feedback_manager):
    """Test coordinate adjustment when coordinates are in target field."""
    workflow_id = "workflow_001"
    
    workflow_data = {
        'id': workflow_id,
        'name': 'Test Workflow',
        'actions': [
            {
                'action': 'click',
                'target': {
                    'element': 'button',
                    'coordinates': {'x': 100, 'y': 200}
                },
                'description': 'Click button'
            }
        ]
    }
    
    analysis = FeedbackAnalysis(
        execution_id="exec_001",
        workflow_id=workflow_id,
        overall_success=False,
        confidence=0.5,
        suggested_adjustments=[
            Adjustment(
                action_index=0,
                adjustment_type='coordinate',
                old_value='(100, 200)',
                new_value='(110, 210)',
                reason='Adjust click position'
            )
        ]
    )
    
    result = await feedback_manager.adjust_workflow(workflow_id, workflow_data, analysis)
    
    # Verify coordinate adjustment in target field
    assert result['actions'][0]['target']['coordinates']['x'] == 110
    assert result['actions'][0]['target']['coordinates']['y'] == 210
