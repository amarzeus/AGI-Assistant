"""Tests for data models."""

import pytest
from datetime import datetime
from src.models.session import Session, SessionStatus
from src.models.action import Action, ActionType
from src.models.pattern import Pattern, PatternOccurrence
from src.models.workflow import WorkflowSuggestion, WorkflowAnalysis
from src.models.transcription import Transcription
from src.models.capture import CaptureStatus
from src.models.storage import StorageStats


class TestSession:
    """Test Session model."""
    
    def test_session_creation(self):
        """Test creating a session."""
        session = Session(
            id='test-session-1',
            start_time=datetime.now(),
            end_time=datetime.now(),
            capture_count=10,
            transcription_count=5,
            detected_actions=8,
            storage_size=1024000,
            status=SessionStatus.ACTIVE
        )
        
        assert session.id == 'test-session-1'
        assert session.is_active
        assert session.capture_count == 10
    
    def test_session_serialization(self):
        """Test session to/from dict."""
        session = Session(
            id='test-session-2',
            start_time=datetime(2025, 1, 1, 12, 0, 0),
            end_time=datetime(2025, 1, 1, 13, 0, 0),
        )
        
        data = session.to_dict()
        restored = Session.from_dict(data)
        
        assert restored.id == session.id
        assert restored.start_time == session.start_time


class TestAction:
    """Test Action model."""
    
    def test_action_creation(self):
        """Test creating an action."""
        action = Action(
            id='action-1',
            session_id='session-1',
            type=ActionType.CLICK,
            timestamp=datetime.now(),
            application='Chrome',
            window_title='Google',
            target_element='Search button',
            confidence=0.95
        )
        
        assert action.type == ActionType.CLICK
        assert action.is_high_confidence
        assert not action.involves_input
    
    def test_action_json_export(self):
        """Test action JSON export for Round 2."""
        action = Action(
            id='action-2',
            session_id='session-1',
            type=ActionType.TYPE,
            timestamp=datetime.now(),
            application='Notepad',
            window_title='Untitled',
            target_element='Text area',
            input_data='Hello World',
            confidence=0.88
        )
        
        export = action.to_json_export()
        
        assert export['action_type'] == 'type'
        assert export['input_data'] == 'Hello World'
        assert 'confidence_score' in export


class TestPattern:
    """Test Pattern model."""
    
    def test_pattern_creation(self):
        """Test creating a pattern."""
        actions = [
            Action(
                id=f'action-{i}',
                session_id='session-1',
                type=ActionType.CLICK,
                timestamp=datetime.now(),
                application='Excel',
                window_title='Sheet1',
                target_element=f'Cell A{i}'
            )
            for i in range(3)
        ]
        
        pattern = Pattern(
            id='pattern-1',
            name='Excel data entry',
            actions=actions,
            occurrences=[],
            frequency=5,
            average_duration=30.0,
            automation_feasibility=0.85,
            created_at=datetime.now(),
            last_detected=datetime.now()
        )
        
        assert pattern.action_count == 3
        assert pattern.is_automatable
        assert pattern.total_time_saved > 0


class TestWorkflowSuggestion:
    """Test WorkflowSuggestion model."""
    
    def test_suggestion_creation(self):
        """Test creating a workflow suggestion."""
        suggestion = WorkflowSuggestion(
            id='suggestion-1',
            pattern_id='pattern-1',
            title='Automate Excel Entry',
            description='Opening Excel and entering data',
            steps=['Open Excel', 'Enter data', 'Save'],
            estimated_time_saved=120,
            complexity='low',
            confidence=0.9,
            created_at=datetime.now()
        )
        
        assert suggestion.is_high_confidence
        assert suggestion.is_simple
        
        display = suggestion.format_for_display()
        assert 'Detected repetitive action' in display
        assert 'Can be automated' in display


class TestTranscription:
    """Test Transcription model."""
    
    def test_transcription_creation(self):
        """Test creating a transcription."""
        transcription = Transcription(
            id='trans-1',
            text='Open Excel and create new spreadsheet',
            timestamp=datetime.now(),
            confidence=0.92,
            duration=3.5
        )
        
        assert transcription.is_high_confidence
        assert transcription.word_count == 6


class TestStorageStats:
    """Test StorageStats model."""
    
    def test_storage_stats(self):
        """Test storage statistics."""
        stats = StorageStats(
            total_used_gb=8.5,
            video_size_gb=5.0,
            screenshot_size_gb=3.0,
            database_size_gb=0.5,
            oldest_data_date=datetime.now(),
            session_count=10
        )
        
        assert stats.usage_percentage == 85.0
        assert stats.is_near_limit
        assert not stats.needs_cleanup
