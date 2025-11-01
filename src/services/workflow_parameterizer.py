"""Workflow Parameterizer Service.

This module provides workflow parameterization capabilities:
- Identify parameterizable values in workflows
- Create parameter schemas
- Substitute parameter values
- Validate parameters
- Enable workflow reuse with different data
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from src.config import get_config
from src.logger import get_app_logger


@dataclass
class Parameter:
    """
    Represents a workflow parameter.
    
    Parameters allow workflows to be reused with different input values.
    """
    name: str
    type: str  # text, number, date, file, choice
    description: str
    default_value: Optional[Any] = None
    required: bool = True
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'default_value': self.default_value,
            'required': self.required,
            'validation_rules': self.validation_rules,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Parameter':
        """Create Parameter from dictionary."""
        return cls(
            name=data['name'],
            type=data['type'],
            description=data['description'],
            default_value=data.get('default_value'),
            required=data.get('required', True),
            validation_rules=data.get('validation_rules', {}),
        )


@dataclass
class ParameterSchema:
    """
    Schema defining parameters for a workflow.
    
    Contains all parameter definitions and metadata.
    """
    workflow_id: str
    parameters: List[Parameter] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'workflow_id': self.workflow_id,
            'parameters': [p.to_dict() for p in self.parameters],
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterSchema':
        """Create ParameterSchema from dictionary."""
        return cls(
            workflow_id=data['workflow_id'],
            parameters=[Parameter.from_dict(p) for p in data.get('parameters', [])],
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
        )


class WorkflowParameterizer:
    """
    Service for enabling workflow reuse with different input data.
    
    Features:
    - Identify parameterizable values in workflows
    - Create parameter schemas
    - Substitute parameter values in workflow data
    - Validate parameter values
    - Support multiple parameter types (text, number, date, file, choice)
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Parameter schemas: workflow_id -> ParameterSchema
        self.parameter_schemas: Dict[str, ParameterSchema] = {}
        
        # Patterns for identifying parameterizable values
        self._email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self._date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
        self._number_pattern = re.compile(r'\b\d+\.?\d*\b')
        self._file_path_pattern = re.compile(r'[A-Za-z]:\\[\w\\\.\-]+|/[\w/\.\-]+')
        
        self.logger.info("Workflow parameterizer initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the workflow parameterizer.
        
        Sets up any required resources and prepares for parameterization.
        """
        try:
            self.logger.info("Workflow parameterizer initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow parameterizer: {e}")
            raise
    
    def get_parameter_schema(self, workflow_id: str) -> Optional[ParameterSchema]:
        """
        Get parameter schema for a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            ParameterSchema if exists, None otherwise
        """
        return self.parameter_schemas.get(workflow_id)
    
    def has_parameters(self, workflow_id: str) -> bool:
        """
        Check if workflow has parameters.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if workflow has parameters, False otherwise
        """
        schema = self.parameter_schemas.get(workflow_id)
        return schema is not None and len(schema.parameters) > 0

    
    async def identify_parameters(
        self,
        workflow: Dict[str, Any]
    ) -> List[Parameter]:
        """
        Identify parameterizable values in workflow.
        
        Analyzes workflow actions to find values that could be parameterized
        for reuse with different data.
        
        Args:
            workflow: Workflow data dictionary
            
        Returns:
            List of Parameter objects with suggested types
        """
        try:
            parameters = []
            param_names_used = set()
            
            # Get actions from workflow
            actions = workflow.get('actions', workflow.get('steps', []))
            
            for i, action in enumerate(actions):
                action_type = action.get('type', action.get('action', 'unknown'))
                
                # Check for text input (type_text, browser_type, browser_fill)
                if action_type in ['type_text', 'browser_type', 'browser_fill']:
                    text_value = action.get('text', '')
                    if text_value and len(text_value) > 0:
                        # Check if it's an email
                        if self._email_pattern.match(text_value):
                            param_name = self._generate_param_name('email', param_names_used)
                            parameters.append(Parameter(
                                name=param_name,
                                type='text',
                                description=f'Email address for action {i+1}',
                                default_value=text_value,
                                required=True,
                                validation_rules={'pattern': r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'}
                            ))
                            param_names_used.add(param_name)
                        # Check if it's a date
                        elif self._date_pattern.match(text_value):
                            param_name = self._generate_param_name('date', param_names_used)
                            parameters.append(Parameter(
                                name=param_name,
                                type='date',
                                description=f'Date value for action {i+1}',
                                default_value=text_value,
                                required=True
                            ))
                            param_names_used.add(param_name)
                        # Check if it's a number
                        elif self._number_pattern.fullmatch(text_value):
                            param_name = self._generate_param_name('number', param_names_used)
                            parameters.append(Parameter(
                                name=param_name,
                                type='number',
                                description=f'Numeric value for action {i+1}',
                                default_value=float(text_value) if '.' in text_value else int(text_value),
                                required=True
                            ))
                            param_names_used.add(param_name)
                        # Generic text
                        elif len(text_value) > 2:
                            param_name = self._generate_param_name('text', param_names_used)
                            parameters.append(Parameter(
                                name=param_name,
                                type='text',
                                description=f'Text input for action {i+1}',
                                default_value=text_value,
                                required=True
                            ))
                            param_names_used.add(param_name)
                
                # Check for file paths (excel_open, file operations)
                if action_type in ['excel_open', 'file_open', 'file_save']:
                    file_path = action.get('file_path', action.get('path', ''))
                    if file_path and self._file_path_pattern.match(file_path):
                        param_name = self._generate_param_name('file_path', param_names_used)
                        parameters.append(Parameter(
                            name=param_name,
                            type='file',
                            description=f'File path for action {i+1}',
                            default_value=file_path,
                            required=True
                        ))
                        param_names_used.add(param_name)
                
                # Check for numeric values in action data
                for key, value in action.items():
                    if key in ['x', 'y', 'clicks', 'duration', 'amount', 'quantity', 'price']:
                        if isinstance(value, (int, float)) and value > 0:
                            param_name = self._generate_param_name(key, param_names_used)
                            parameters.append(Parameter(
                                name=param_name,
                                type='number',
                                description=f'{key.capitalize()} value for action {i+1}',
                                default_value=value,
                                required=False,  # Coordinates and durations are usually optional
                                validation_rules={'min': 0}
                            ))
                            param_names_used.add(param_name)
            
            self.logger.info(f"Identified {len(parameters)} parameters in workflow")
            return parameters
            
        except Exception as e:
            self.logger.error(f"Failed to identify parameters: {e}")
            return []
    
    def _generate_param_name(self, base_name: str, used_names: set) -> str:
        """
        Generate unique parameter name.
        
        Args:
            base_name: Base name for parameter
            used_names: Set of already used names
            
        Returns:
            Unique parameter name
        """
        if base_name not in used_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in used_names:
            counter += 1
        
        return f"{base_name}_{counter}"

    
    async def create_parameter_schema(
        self,
        workflow_id: str,
        parameters: List[Parameter]
    ) -> ParameterSchema:
        """
        Create parameter schema for workflow.
        
        Generates a schema from identified parameters with descriptions
        and validation rules.
        
        Args:
            workflow_id: Workflow identifier
            parameters: List of Parameter objects
            
        Returns:
            ParameterSchema object
        """
        try:
            # Create schema
            schema = ParameterSchema(
                workflow_id=workflow_id,
                parameters=parameters,
                version=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store schema
            self.parameter_schemas[workflow_id] = schema
            
            self.logger.info(
                f"Created parameter schema for workflow {workflow_id} "
                f"with {len(parameters)} parameters"
            )
            
            return schema
            
        except Exception as e:
            self.logger.error(f"Failed to create parameter schema: {e}")
            raise

    
    async def substitute_parameters(
        self,
        workflow: Dict[str, Any],
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Substitute parameter values in workflow.
        
        Replaces parameter placeholders with actual values, handling
        type conversion and nested references.
        
        Args:
            workflow: Workflow data dictionary
            values: Dictionary of parameter name -> value
            
        Returns:
            Modified workflow with substituted values
        """
        try:
            import copy
            import json
            
            # Create deep copy to avoid modifying original
            substituted_workflow = copy.deepcopy(workflow)
            
            # Convert workflow to JSON string for substitution
            workflow_str = json.dumps(substituted_workflow)
            
            # Replace each parameter placeholder
            for param_name, param_value in values.items():
                # Handle different placeholder formats
                placeholders = [
                    f"{{{{param_name}}}}",  # {{param_name}}
                    f"${{{param_name}}}",   # ${param_name}
                    f"<{param_name}>",      # <param_name>
                ]
                
                # Convert value to string for substitution
                value_str = str(param_value)
                
                for placeholder in placeholders:
                    workflow_str = workflow_str.replace(placeholder, value_str)
            
            # Parse back to dictionary
            substituted_workflow = json.loads(workflow_str)
            
            # Also do direct substitution in actions
            actions = substituted_workflow.get('actions', substituted_workflow.get('steps', []))
            
            for action in actions:
                for key, value in action.items():
                    if isinstance(value, str):
                        # Check if value matches a parameter name
                        if value in values:
                            # Substitute with actual value
                            action[key] = values[value]
                        else:
                            # Check for placeholder patterns
                            for param_name, param_value in values.items():
                                placeholders = [
                                    f"{{{{param_name}}}}",
                                    f"${{{param_name}}}",
                                    f"<{param_name}>",
                                ]
                                for placeholder in placeholders:
                                    if placeholder in value:
                                        action[key] = value.replace(placeholder, str(param_value))
            
            self.logger.info(f"Substituted {len(values)} parameters in workflow")
            return substituted_workflow
            
        except Exception as e:
            self.logger.error(f"Failed to substitute parameters: {e}")
            return workflow

    
    async def validate_parameters(
        self,
        schema: ParameterSchema,
        values: Dict[str, Any]
    ) -> List[str]:
        """
        Validate parameter values against schema.
        
        Checks that all required parameters are provided and that
        values match expected types and validation rules.
        
        Args:
            schema: ParameterSchema to validate against
            values: Dictionary of parameter name -> value
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            errors = []
            
            # Check each parameter in schema
            for param in schema.parameters:
                param_name = param.name
                
                # Check if required parameter is provided
                if param.required and param_name not in values:
                    errors.append(f"Required parameter '{param_name}' is missing")
                    continue
                
                # Skip validation if parameter not provided and not required
                if param_name not in values:
                    continue
                
                value = values[param_name]
                
                # Validate type
                if param.type == 'text':
                    if not isinstance(value, str):
                        errors.append(
                            f"Parameter '{param_name}' must be a string, got {type(value).__name__}"
                        )
                    else:
                        # Check pattern if specified
                        if 'pattern' in param.validation_rules:
                            pattern = re.compile(param.validation_rules['pattern'])
                            if not pattern.match(value):
                                errors.append(
                                    f"Parameter '{param_name}' does not match required pattern"
                                )
                        
                        # Check min/max length if specified
                        if 'min_length' in param.validation_rules:
                            if len(value) < param.validation_rules['min_length']:
                                errors.append(
                                    f"Parameter '{param_name}' must be at least "
                                    f"{param.validation_rules['min_length']} characters"
                                )
                        if 'max_length' in param.validation_rules:
                            if len(value) > param.validation_rules['max_length']:
                                errors.append(
                                    f"Parameter '{param_name}' must be at most "
                                    f"{param.validation_rules['max_length']} characters"
                                )
                
                elif param.type == 'number':
                    if not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                            values[param_name] = value  # Update with converted value
                        except (ValueError, TypeError):
                            errors.append(
                                f"Parameter '{param_name}' must be a number, got {type(value).__name__}"
                            )
                            continue
                    
                    # Check min/max if specified
                    if 'min' in param.validation_rules:
                        if value < param.validation_rules['min']:
                            errors.append(
                                f"Parameter '{param_name}' must be at least {param.validation_rules['min']}"
                            )
                    if 'max' in param.validation_rules:
                        if value > param.validation_rules['max']:
                            errors.append(
                                f"Parameter '{param_name}' must be at most {param.validation_rules['max']}"
                            )
                
                elif param.type == 'date':
                    if isinstance(value, str):
                        # Try to parse date
                        try:
                            from datetime import datetime as dt
                            dt.fromisoformat(value)
                        except ValueError:
                            errors.append(
                                f"Parameter '{param_name}' must be a valid date (ISO format)"
                            )
                    elif not isinstance(value, datetime):
                        errors.append(
                            f"Parameter '{param_name}' must be a date, got {type(value).__name__}"
                        )
                
                elif param.type == 'file':
                    if not isinstance(value, str):
                        errors.append(
                            f"Parameter '{param_name}' must be a file path string"
                        )
                    else:
                        # Check if file exists if specified
                        if param.validation_rules.get('must_exist', False):
                            if not Path(value).exists():
                                errors.append(
                                    f"File '{value}' for parameter '{param_name}' does not exist"
                                )
                
                elif param.type == 'choice':
                    # Check if value is in allowed choices
                    if 'choices' in param.validation_rules:
                        if value not in param.validation_rules['choices']:
                            errors.append(
                                f"Parameter '{param_name}' must be one of: "
                                f"{', '.join(str(c) for c in param.validation_rules['choices'])}"
                            )
            
            if errors:
                self.logger.warning(f"Parameter validation failed with {len(errors)} errors")
            else:
                self.logger.info("Parameter validation successful")
            
            return errors
            
        except Exception as e:
            self.logger.error(f"Failed to validate parameters: {e}")
            return [f"Validation error: {str(e)}"]
