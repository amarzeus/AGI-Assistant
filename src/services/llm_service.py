"""Local LLM service using Ollama for workflow analysis."""

import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import ollama

from src.config import get_config
from src.logger import get_app_logger
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class LLMService:
    """
    Local LLM service for analyzing user actions and generating workflow insights.
    
    Features:
    - Local LLM integration using Ollama
    - Action interpretation from screen captures and transcriptions
    - Workflow pattern detection
    - Automation suggestion generation
    - Structured JSON output parsing
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # LLM configuration
        self.model_name = self.config.llm.model_name
        self.context_window = self.config.llm.context_window
        self.temperature = self.config.llm.temperature
        self.max_tokens = self.config.llm.max_tokens
        
        # Service state
        self._initialized = False
        self._model_available = False
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Prompt templates
        self._setup_prompt_templates()
        
        self.logger.info("LLM service initialized")
    
    async def initialize(self) -> None:
        """Initialize LLM service and check model availability."""
        if self._initialized:
            return
        
        # Check if LLM is enabled in config
        if not self.config.llm.enabled:
            self.logger.info("LLM service disabled in configuration (lightweight mode)")
            self._initialized = True
            self._model_available = False
            return
        
        self.logger.info("Initializing LLM service...")
        
        try:
            # Check if Ollama is running
            await self._check_ollama_status()
            
            # Ensure model is available
            await self._ensure_model_available()
            
            self._initialized = True
            self.logger.info(f"LLM service initialized with model: {self.model_name}")
            
        except Exception as e:
            self.logger.warning(f"LLM service initialization failed (continuing without LLM): {e}")
            self._initialized = True
            self._model_available = False
    
    async def analyze_action(self, screenshot_path: str, transcription: str, 
                           context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze a user action from screenshot and transcription.
        
        Args:
            screenshot_path: Path to screenshot file
            transcription: Audio transcription of user action
            context: Additional context (window title, timestamp, etc.)
            
        Returns:
            Dictionary with action analysis or None if analysis fails
        """
        try:
            if not self._model_available:
                self.logger.warning("LLM model not available for action analysis")
                return None
            
            # Prepare analysis prompt
            prompt = self._create_action_analysis_prompt(
                screenshot_path, transcription, context
            )
            
            # Get LLM response
            response = await self._query_llm(prompt, "action_analysis")
            
            if response:
                # Parse structured response
                action_data = self._parse_action_response(response)
                
                if action_data:
                    self.logger.debug(f"Action analyzed: {action_data.get('action_type', 'unknown')}")
                    return action_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing action: {e}")
            return None
    
    async def detect_workflow_patterns(self, actions: List[Dict[str, Any]], 
                                     window_size: int = 50) -> List[Dict[str, Any]]:
        """
        Detect workflow patterns from a sequence of actions.
        
        Args:
            actions: List of analyzed actions
            window_size: Number of recent actions to analyze
            
        Returns:
            List of detected patterns
        """
        try:
            if not self._model_available:
                self.logger.warning("LLM model not available for pattern detection")
                return []
            
            # Limit to recent actions
            recent_actions = actions[-window_size:] if len(actions) > window_size else actions
            
            if len(recent_actions) < 3:  # Need at least 3 actions for pattern
                return []
            
            # Prepare pattern detection prompt
            prompt = self._create_pattern_detection_prompt(recent_actions)
            
            # Get LLM response
            response = await self._query_llm(prompt, "pattern_detection")
            
            if response:
                # Parse patterns
                patterns = self._parse_pattern_response(response)
                
                if patterns:
                    self.logger.info(f"Detected {len(patterns)} workflow patterns")
                    return patterns
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error detecting patterns: {e}")
            return []
    
    async def generate_automation_suggestions(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate automation suggestions from detected patterns.
        
        Args:
            patterns: List of detected workflow patterns
            
        Returns:
            List of automation suggestions
        """
        try:
            if not self._model_available or not patterns:
                return []
            
            # Prepare suggestion generation prompt
            prompt = self._create_suggestion_prompt(patterns)
            
            # Get LLM response
            response = await self._query_llm(prompt, "suggestion_generation")
            
            if response:
                # Parse suggestions
                suggestions = self._parse_suggestion_response(response)
                
                if suggestions:
                    self.logger.info(f"Generated {len(suggestions)} automation suggestions")
                    return suggestions
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {e}")
            return []
    
    async def _check_ollama_status(self) -> None:
        """Check if Ollama service is running."""
        try:
            # Try to list models to check if Ollama is running
            models = ollama.list()
            self.logger.info(f"Ollama is running with {len(models['models'])} models")
            
        except Exception as e:
            self.logger.error(f"Ollama is not running or not accessible: {e}")
            raise RuntimeError("Ollama service is not available. Please start Ollama first.")
    
    async def _ensure_model_available(self) -> None:
        """Ensure the required model is available."""
        try:
            # Check if model exists
            models = ollama.list()
            model_names = [model['name'] for model in models['models']]
            
            if self.model_name not in model_names:
                self.logger.info(f"Model {self.model_name} not found. Pulling...")
                
                # Pull the model
                ollama.pull(self.model_name)
                self.logger.info(f"Model {self.model_name} pulled successfully")
            
            # Test the model with a simple query
            test_response = ollama.generate(
                model=self.model_name,
                prompt="Hello, respond with 'OK' if you're working.",
                options={
                    'temperature': 0.1,
                    'num_predict': 10
                }
            )
            
            if test_response and 'response' in test_response:
                self._model_available = True
                self.logger.info(f"Model {self.model_name} is working correctly")
            else:
                raise RuntimeError("Model test failed")
                
        except Exception as e:
            self.logger.error(f"Failed to ensure model availability: {e}")
            raise
    
    async def _query_llm(self, prompt: str, query_type: str) -> Optional[str]:
        """
        Query the LLM with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            query_type: Type of query for logging
            
        Returns:
            LLM response text or None if query fails
        """
        try:
            self.logger.debug(f"Querying LLM for {query_type}")
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._run_ollama_query,
                prompt
            )
            
            if response and 'response' in response:
                response_text = response['response'].strip()
                self.logger.debug(f"LLM response for {query_type}: {len(response_text)} characters")
                return response_text
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error querying LLM for {query_type}: {e}")
            return None
    
    def _run_ollama_query(self, prompt: str) -> Dict[str, Any]:
        """Run Ollama query in thread pool."""
        return ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={
                'temperature': self.temperature,
                'num_predict': self.max_tokens,
                'top_k': 40,
                'top_p': 0.9
            }
        )
    
    def _setup_prompt_templates(self) -> None:
        """Set up prompt templates for different analysis types."""
        
        self.action_analysis_template = """
You are an AI assistant that analyzes user computer actions. Based on the provided information, identify what action the user performed.

Context:
- Screenshot: {screenshot_path}
- Audio transcription: "{transcription}"
- Window title: {window_title}
- Timestamp: {timestamp}

Analyze this information and respond with a JSON object containing:
{{
    "action_type": "click|type|navigate|scroll|select|copy|paste|save|open|close|other",
    "description": "Brief description of what the user did",
    "target_element": "What UI element was interacted with (if identifiable)",
    "application": "Application name",
    "confidence": 0.0-1.0,
    "automation_feasible": true/false,
    "automation_complexity": "low|medium|high"
}}

Respond only with valid JSON, no additional text.
"""
        
        self.pattern_detection_template = """
You are an AI assistant that detects workflow patterns in user actions. Analyze the sequence of actions to identify repetitive patterns.

Recent Actions:
{actions_summary}

Identify workflow patterns and respond with a JSON array of patterns:
[
    {{
        "pattern_id": "unique_identifier",
        "pattern_type": "repetitive_sequence|data_entry|navigation|file_management",
        "description": "Description of the pattern",
        "actions_involved": ["action1", "action2", "action3"],
        "frequency": "Number of times this pattern occurred",
        "confidence": 0.0-1.0,
        "automation_potential": "low|medium|high"
    }}
]

Only include patterns that occur at least 2 times. Respond only with valid JSON, no additional text.
"""
        
        self.suggestion_generation_template = """
You are an AI assistant that generates automation suggestions based on detected workflow patterns.

Detected Patterns:
{patterns_summary}

Generate automation suggestions and respond with a JSON array:
[
    {{
        "suggestion_id": "unique_identifier",
        "title": "Brief title for the automation",
        "description": "Detailed description of what could be automated",
        "pattern_ids": ["pattern1", "pattern2"],
        "automation_type": "macro|script|template|shortcut",
        "complexity": "low|medium|high",
        "time_saved_estimate": "Estimated time saved per execution",
        "implementation_steps": ["step1", "step2", "step3"],
        "confidence": 0.0-1.0
    }}
]

Focus on practical, implementable suggestions. Respond only with valid JSON, no additional text.
"""
    
    def _create_action_analysis_prompt(self, screenshot_path: str, transcription: str, 
                                     context: Dict[str, Any]) -> str:
        """Create prompt for action analysis."""
        return self.action_analysis_template.format(
            screenshot_path=screenshot_path,
            transcription=transcription or "No audio transcription available",
            window_title=context.get('window_title', 'Unknown'),
            timestamp=context.get('timestamp', datetime.now().isoformat())
        )
    
    def _create_pattern_detection_prompt(self, actions: List[Dict[str, Any]]) -> str:
        """Create prompt for pattern detection."""
        # Summarize actions for the prompt
        actions_summary = []
        for i, action in enumerate(actions[-20:], 1):  # Last 20 actions
            summary = f"{i}. {action.get('action_type', 'unknown')} - {action.get('description', 'No description')}"
            if action.get('application'):
                summary += f" (in {action['application']})"
            actions_summary.append(summary)
        
        return self.pattern_detection_template.format(
            actions_summary="\n".join(actions_summary)
        )
    
    def _create_suggestion_prompt(self, patterns: List[Dict[str, Any]]) -> str:
        """Create prompt for automation suggestions."""
        # Summarize patterns for the prompt
        patterns_summary = []
        for i, pattern in enumerate(patterns, 1):
            summary = f"{i}. {pattern.get('description', 'No description')} "
            summary += f"(Type: {pattern.get('pattern_type', 'unknown')}, "
            summary += f"Frequency: {pattern.get('frequency', 'unknown')})"
            patterns_summary.append(summary)
        
        return self.suggestion_generation_template.format(
            patterns_summary="\n".join(patterns_summary)
        )
    
    def _parse_action_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response for action analysis."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            action_data = json.loads(response)
            
            # Validate required fields
            required_fields = ['action_type', 'description', 'confidence']
            if all(field in action_data for field in required_fields):
                return action_data
            
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse action response as JSON: {e}")
            return None
    
    def _parse_pattern_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response for pattern detection."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            patterns = json.loads(response)
            
            # Validate that it's a list
            if isinstance(patterns, list):
                return patterns
            
            return []
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse pattern response as JSON: {e}")
            return []
    
    def _parse_suggestion_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response for automation suggestions."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            suggestions = json.loads(response)
            
            # Validate that it's a list
            if isinstance(suggestions, list):
                return suggestions
            
            return []
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse suggestion response as JSON: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self._initialized and self._model_available
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            'model_name': self.model_name,
            'available': self._model_available,
            'initialized': self._initialized,
            'context_window': self.context_window,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }