"""Tests for WorkflowParameterizer service."""

import pytest
from datetime import datetime
from src.services.workflow_parameterizer import (
    WorkflowParameterizer,
    Parameter,
    ParameterSchema
)


@pytest.fixture
def parameterizer():
    """Create WorkflowParameterizer instance."""
    return WorkflowParameterizer()


@pytest.mark.asyncio
async def test_initialize(parameterizer):
    """Test parameterizer initialization."""
    await parameterizer.initialize()
    assert parameterizer.parameter_schemas == {}


@pytest.mark.asyncio
async def test_identify_parameters_text(parameterizer):
    """Test identifying text parameters."""
    workflow = {
        'actions': [
            {'type': 'type_text', 'text': 'test@example.com'},
            {'type': 'type_text', 'text': 'John Doe'},
        ]
    }
    
    params = await parameterizer.identify_parameters(workflow)
    assert len(params) >= 2
    assert any(p.type == 'text' for p in params)


@pytest.mark.asyncio
async def test_identify_parameters_numbers(parameterizer):
    """Test identifying numeric parameters."""
    workflow = {
        'actions': [
            {'type': 'click', 'x': 100, 'y': 200},
        ]
    }
    
    params = await parameterizer.identify_parameters(workflow)
    assert len(params) >= 2
    assert all(p.type == 'number' for p in params)


@pytest.mark.asyncio
async def test_create_parameter_schema(parameterizer):
    """Test creating parameter schema."""
    params = [
        Parameter(name='email', type='text', description='Email address'),
        Parameter(name='count', type='number', description='Count value'),
    ]
    
    schema = await parameterizer.create_parameter_schema('workflow_001', params)
    
    assert schema.workflow_id == 'workflow_001'
    assert len(schema.parameters) == 2
    assert schema.version == 1


@pytest.mark.asyncio
async def test_substitute_parameters(parameterizer):
    """Test parameter substitution."""
    workflow = {
        'actions': [
            {'type': 'type_text', 'text': 'email'},
        ]
    }
    
    values = {'email': 'test@example.com'}
    result = await parameterizer.substitute_parameters(workflow, values)
    
    assert result['actions'][0]['text'] == 'test@example.com'


@pytest.mark.asyncio
async def test_validate_parameters_success(parameterizer):
    """Test successful parameter validation."""
    schema = ParameterSchema(
        workflow_id='test',
        parameters=[
            Parameter(name='email', type='text', description='Email', required=True),
            Parameter(name='count', type='number', description='Count', required=True),
        ]
    )
    
    values = {'email': 'test@example.com', 'count': 5}
    errors = await parameterizer.validate_parameters(schema, values)
    
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_validate_parameters_missing_required(parameterizer):
    """Test validation with missing required parameter."""
    schema = ParameterSchema(
        workflow_id='test',
        parameters=[
            Parameter(name='email', type='text', description='Email', required=True),
        ]
    )
    
    values = {}
    errors = await parameterizer.validate_parameters(schema, values)
    
    assert len(errors) > 0
    assert 'missing' in errors[0].lower()


@pytest.mark.asyncio
async def test_validate_parameters_type_mismatch(parameterizer):
    """Test validation with type mismatch."""
    schema = ParameterSchema(
        workflow_id='test',
        parameters=[
            Parameter(name='count', type='number', description='Count', required=True),
        ]
    )
    
    values = {'count': 'not_a_number'}
    errors = await parameterizer.validate_parameters(schema, values)
    
    assert len(errors) > 0
