"""Tests for automation executor service."""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from src.services.automation_executor import (
    AutomationExecutor,
    WorkflowExecution,
    ExecutionState
)
from src.database.storage_manager import StorageManager


@pytest.fixture
async def storage_manager():
    """Create storage manager for testing."""
    manager = StorageManager()
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def executor(storage_manager):
    """Create automation executor for testing."""
    executor = AutomationExecutor()
    await executor.initialize(storage_manager)
    await executor.start()
    yield executor
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_initialization(storage_manager):
    """Test executor initialization."""
    executor = AutomationExecutor()
    await executor.initialize(storage_manager)
    
    assert executor.storage_manager is not None
    assert executor.desktop_platform is not None
    assert not executor._running
    
    await executor.start()
    assert executor._running
    
    await executor.stop()
    assert not executor._running


@pytest.mark.asyncio
async def test_workflow_validation():
    """Test workflow validation."""
    executor = AutomationExecutor()
    
    # Valid workflow
    valid_workflow = {
        'id': 'test_workflow',
        'name': 'Test Workflow',
        'actions': [
            {'type': 'wait', 'duration': 0.1}
        ]
    }
    assert executor._validate_workflow(valid_workflow)
    
    # Invalid workflow - missing id
    invalid_workflow = {
        'name': 'Test Workflow',
        'actions': []
    }
    assert not executor._validate_workflow(invalid_workflow)
    
    # Invalid workflow - empty actions
    invalid_workflow2 = {
        'id': 'test',
        'name': 'Test',
        'actions': []
    }
    assert not executor._validate_workflow(invalid_workflow2)


@pytest.mark.asyncio
async def test_queue_execution(executor):
    """Test queueing workflow execution."""
    workflow_data = {
        'id': 'test_workflow',
        'name': 'Test Workflow',
        'description': 'Test workflow description',
        'actions': [
            {'type': 'wait', 'duration': 0.1}
        ]
    }
    
    execution_id = await executor.queue_execution(workflow_data)
    
    assert execution_id is not None
    assert len(executor.execution_queue) == 1
    
    # Check execution status
    status = executor.get_execution_status(execution_id)
    assert status is not None
    assert status['workflow_id'] == 'test_workflow'
    assert status['state'] == ExecutionState.PENDING.value


@pytest.mark.asyncio
async def test_simple_execution(executor):
    """Test simple workflow execution."""
    workflow_data = {
        'id': 'test_simple',
        'name': 'Simple Test',
        'description': 'Simple test workflow',
        'actions': [
            {'type': 'wait', 'duration': 0.1},
            {'type': 'wait', 'duration': 0.1}
        ]
    }
    
    execution_id = await executor.queue_execution(workflow_data)
    
    # Wait for execution to complete
    await asyncio.sleep(2)
    
    # Check stats
    stats = executor.get_stats()
    assert stats['executions_completed'] >= 1


@pytest.mark.asyncio
async def test_action_dispatch():
    """Test action dispatching."""
    executor = AutomationExecutor()
    
    # Test wait action
    result = await executor._dispatch_action('wait', {'duration': 0.1})
    assert result is True
    
    # Test unknown action
    result = await executor._dispatch_action('unknown_action', {})
    assert result is False


@pytest.mark.asyncio
async def test_execution_cancellation(executor):
    """Test execution cancellation."""
    workflow_data = {
        'id': 'test_cancel',
        'name': 'Cancel Test',
        'description': 'Test cancellation',
        'actions': [
            {'type': 'wait', 'duration': 5.0}  # Long wait
        ]
    }
    
    execution_id = await executor.queue_execution(workflow_data)
    
    # Wait a bit for execution to start
    await asyncio.sleep(0.5)
    
    # Cancel execution
    result = await executor.cancel_execution(execution_id)
    assert result is True


@pytest.mark.asyncio
async def test_workflow_execution_state():
    """Test workflow execution state management."""
    execution = WorkflowExecution(
        workflow_id='test_workflow',
        workflow_data={
            'id': 'test',
            'name': 'Test',
            'actions': [
                {'type': 'wait', 'duration': 0.1}
            ]
        }
    )
    
    # Initial state
    assert execution.state == ExecutionState.PENDING
    assert execution.progress == 0.0
    assert execution.current_step == 0
    
    # Convert to dict
    data = execution.to_dict()
    assert data['state'] == 'pending'
    assert data['workflow_id'] == 'test_workflow'


@pytest.mark.asyncio
async def test_multiple_executions(executor):
    """Test multiple workflow executions."""
    workflows = []
    for i in range(3):
        workflow_data = {
            'id': f'test_workflow_{i}',
            'name': f'Test Workflow {i}',
            'description': f'Test workflow {i}',
            'actions': [
                {'type': 'wait', 'duration': 0.1}
            ]
        }
        execution_id = await executor.queue_execution(workflow_data)
        workflows.append(execution_id)
    
    assert len(executor.execution_queue) == 3
    
    # Wait for all to complete
    await asyncio.sleep(3)
    
    # Check stats
    stats = executor.get_stats()
    assert stats['executions_completed'] >= 3


@pytest.mark.asyncio
async def test_executor_stats(executor):
    """Test executor statistics."""
    stats = executor.get_stats()
    
    assert 'running' in stats
    assert 'queue_size' in stats
    assert 'executions_completed' in stats
    assert 'executions_failed' in stats
    
    assert stats['running'] is True
    assert stats['queue_size'] == 0
    assert stats['executions_completed'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
