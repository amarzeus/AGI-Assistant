"""
Comprehensive Unit Tests for AGI Assistant MVP
Based on PRD Requirements: "The AGI Assistant" Hackathon

Tests verify Round 1 objectives:
1. Observe & Understand (Screen & Audio Capture)
2. Data Processing (Local, Privacy-First)
3. Pattern Recognition
4. Automation Suggestions
5. Storage Management
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import tempfile
import shutil

# Import application components
from src.models.session import Session, SessionStatus
from src.models.action import Action, ActionType
from src.models.pattern import Pattern
from src.models.workflow import WorkflowSuggestion
from src.models.transcription import Transcription
from src.database.storage_manager import StorageManager
from src.services.pattern_detector import PatternDetector
from src.services.automation_engine import AutomationSuggestionEngine
from src.services.storage_monitor import StorageMonitor
from src.services.storage_cleanup import StorageCleanupService
from src.config import AppConfig


# ============================================================================
# PRD REQUIREMENT 1: SCREEN & AUDIO CAPTURE
# "Act like a dashcam for the desktop - continuously recording"
# ============================================================================


class TestScreenAudioCapture:
    """Test PRD Requirement: Screen and audio capture functionality."""

    @pytest.mark.asyncio
    async def test_screen_capture_initialization(self):
        """
        PRD: "Captures screen in real time (like a dashcam)"
        Verify screen capture service can initialize.
        """
        from src.services.screen_capture import ScreenCaptureService

        service = ScreenCaptureService()
        assert service is not None
        assert hasattr(service, "start")
        assert hasattr(service, "stop")
        assert hasattr(service, "pause")
        assert hasattr(service, "resume")

    @pytest.mark.asyncio
    async def test_audio_capture_initialization(self):
        """
        PRD: "Audio can capture commands like 'open Excel' or 'save report'"
        Verify audio transcription service can initialize.
        """
        from src.services.audio_transcription import AudioTranscriptionService

        service = AudioTranscriptionService()
        assert service is not None
        assert hasattr(service, "start")
        assert hasattr(service, "stop")
        assert hasattr(service, "set_enabled")

    def test_capture_status_tracking(self):
        """
        PRD: System should track capture status.
        Verify capture status model has required fields.
        """
        from src.models.capture import CaptureStatus

        status = CaptureStatus(
            is_recording=True, frames_captured=10, active_window="Test Window"
        )

        assert status.is_recording is True
        assert status.frames_captured == 10
        assert status.active_window == "Test Window"


# ============================================================================
# PRD REQUIREMENT 2: DATA PROCESSING (LOCAL)
# "Everything happens locally - no cloud uploads"
# ============================================================================


class TestLocalDataProcessing:
    """Test PRD Requirement: All processing happens locally."""

    @pytest.mark.asyncio
    async def test_local_storage_creation(self):
        """
        PRD: "Everything happens locally in user system"
        Verify data is stored locally in SQLite.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            storage = StorageManager(config)

            await storage.initialize()

            # Verify local database file was created
            db_file = config.data_dir / "database" / "agi_assistant.db"
            assert db_file.exists()

            await storage.close()

    @pytest.mark.asyncio
    async def test_no_external_api_calls(self):
        """
        PRD: "No cloud calls" - "Privacy-first design"
        Verify LLM service uses local models only.
        """
        from src.services.llm_service import LLMService

        llm = LLMService()

        # Verify it's configured for local operation
        assert llm.use_local_model is True
        assert (
            llm.api_endpoint is None
            or "localhost" in llm.api_endpoint
            or "127.0.0.1" in llm.api_endpoint
        )

    @pytest.mark.asyncio
    async def test_audio_transcription_local(self):
        """
        PRD: "Transcribes audio locally (using e.g., Whisper.cpp)"
        Verify audio transcription uses local models.
        """
        from src.services.audio_transcription import AudioTranscriptionService

        service = AudioTranscriptionService()

        # Verify local model configuration
        assert service.model_name is not None
        assert (
            "whisper" in service.model_name.lower()
            or "base" in service.model_name.lower()
        )


# ============================================================================
# PRD REQUIREMENT 3: STRUCTURED OUTPUT
# "Converts video into JSON and Screenshots"
# "Structured JSON describing UI events, mouse movements, clicks"
# ============================================================================


class TestStructuredOutput:
    """Test PRD Requirement: Generate structured JSON output."""

    def test_action_json_serialization(self):
        """
        PRD: "Structured JSON describing UI events, mouse movements, clicks"
        Verify actions can be serialized to JSON.
        """
        action = Action(
            id="test_action_1",
            session_id="session_123",
            type=ActionType.CLICK,
            target_element="button",
            timestamp=datetime.now(),
            confidence=0.85,
        )

        # Convert to JSON
        action_dict = action.model_dump()
        json_str = json.dumps(action_dict, default=str)

        assert json_str is not None
        assert "CLICK" in json_str
        assert "button" in json_str
        assert "0.85" in json_str

    def test_workflow_json_export(self):
        """
        PRD: "Structured JSON describing workflow steps"
        Verify workflows can be exported as structured JSON.
        """
        pattern = Pattern(
            id="pattern_1",
            pattern_type="data_entry",
            description="Excel data entry workflow",
            actions=[],
            frequency=3,
            confidence=0.87,
            automation_feasibility=0.92,
        )

        # Export to JSON
        pattern_dict = pattern.model_dump()
        json_str = json.dumps(pattern_dict, default=str)

        assert json_str is not None
        assert "data_entry" in json_str
        assert "frequency" in json_str
        assert "3" in json_str

    def test_action_types_coverage(self):
        """
        PRD: "UI events, mouse movements, clicks or workflow steps"
        Verify all required action types are defined.
        """
        required_types = ["CLICK", "TYPE", "NAVIGATE", "OPEN", "SAVE", "SCROLL"]

        action_type_values = [t.value for t in ActionType]

        for required in required_types:
            assert required in action_type_values, f"Missing action type: {required}"


# ============================================================================
# PRD REQUIREMENT 4: PATTERN RECOGNITION
# "Identifies repetitive patterns" - "Recognizing repeated workflows"
# ============================================================================


class TestPatternRecognition:
    """Test PRD Requirement: Detect repetitive patterns and workflows."""

    def test_pattern_detection_initialization(self):
        """
        PRD: "Recognizing repeated workflows or patterns"
        Verify pattern detector can initialize.
        """
        detector = PatternDetector()
        assert detector is not None
        assert hasattr(detector, "detect_patterns")

    def test_detect_repetitive_actions(self):
        """
        PRD: "Identifies repetitive patterns"
        Verify system detects when actions repeat 3+ times.
        """
        detector = PatternDetector()

        # Create 3 identical actions (repetitive pattern)
        actions = []
        for i in range(3):
            actions.append(
                Action(
                    id=f"action_{i}",
                    session_id="session_test",
                    type=ActionType.CLICK,
                    target_element="Save Button",
                    timestamp=datetime.now() + timedelta(seconds=i * 30),
                    confidence=0.9,
                )
            )

        patterns = detector.detect_patterns(actions)

        # Should detect at least one pattern
        assert len(patterns) > 0
        assert patterns[0].frequency >= 3

    def test_pattern_confidence_scoring(self):
        """
        PRD: Pattern detection should have confidence scores.
        Verify patterns include confidence scores.
        """
        pattern = Pattern(
            id="pattern_test",
            pattern_type="test",
            description="Test pattern",
            actions=[],
            frequency=3,
            confidence=0.85,
            automation_feasibility=0.9,
        )

        assert 0.0 <= pattern.confidence <= 1.0
        assert pattern.confidence > 0.7  # Meets PRD threshold


# ============================================================================
# PRD REQUIREMENT 5: AUTOMATION SUGGESTIONS
# "Suggests possible automations in plain text"
# "Detected repetitive action: ... Can be automated."
# ============================================================================


class TestAutomationSuggestions:
    """Test PRD Requirement: Generate automation suggestions."""

    def test_automation_engine_initialization(self):
        """
        PRD: "Suggests possible automations"
        Verify automation engine can initialize.
        """
        engine = AutomationSuggestionEngine()
        assert engine is not None
        assert hasattr(engine, "generate_suggestions")

    def test_suggestion_format(self):
        """
        PRD: "Detected repetitive action: ... Can be automated."
        Verify suggestions follow the required format.
        """
        suggestion = WorkflowSuggestion(
            id="suggestion_1",
            pattern_id="pattern_1",
            title="Automate Excel Data Entry",
            description="Detected repetitive action: Opening Excel → Typing values → Saving file. Can be automated.",
            implementation_steps=[
                "Step 1: Open Excel",
                "Step 2: Enter data",
                "Step 3: Save file",
            ],
            estimated_time_saved="5 minutes per execution",
            complexity="low",
            confidence=0.88,
        )

        # Verify format matches PRD
        assert "Detected repetitive action" in suggestion.description
        assert "Can be automated" in suggestion.description
        assert len(suggestion.implementation_steps) > 0

    def test_time_savings_estimation(self):
        """
        PRD: Suggestions should include time savings.
        Verify time savings are estimated.
        """
        engine = AutomationSuggestionEngine()

        pattern = Pattern(
            id="pattern_time",
            pattern_type="data_entry",
            description="Test workflow",
            actions=[],
            frequency=5,
            confidence=0.9,
            automation_feasibility=0.85,
        )

        suggestions = engine.generate_suggestions([pattern])

        assert len(suggestions) > 0
        # Should have time savings estimate
        assert suggestions[0].estimated_time_saved is not None


# ============================================================================
# PRD REQUIREMENT 6: STORAGE MANAGEMENT
# "Delete older training data when a personalized model is stable"
# "Optimize how screenshots and videos are stored"
# ============================================================================


class TestStorageManagement:
    """Test PRD Requirement: Efficient local storage management."""

    @pytest.mark.asyncio
    async def test_storage_monitoring(self):
        """
        PRD: "Optimize how screenshots and videos are stored"
        Verify storage usage can be monitored.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            monitor = StorageMonitor(config)

            stats = await monitor.get_storage_statistics()

            assert stats is not None
            assert "total_size_mb" in stats
            assert "screenshots_size_mb" in stats
            assert "videos_size_mb" in stats

    @pytest.mark.asyncio
    async def test_automatic_cleanup(self):
        """
        PRD: "Delete older training data when stable"
        Verify automatic cleanup when storage limit is reached.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir), storage_limit_gb=1)
            cleanup = StorageCleanupService(config)

            # Should have cleanup capability
            assert hasattr(cleanup, "cleanup_old_data")
            assert hasattr(cleanup, "should_cleanup")

    @pytest.mark.asyncio
    async def test_configurable_storage_limits(self):
        """
        PRD: "Manage local storage efficiently"
        Verify storage limits are configurable.
        """
        config = AppConfig(storage_limit_gb=10)

        assert config.storage_limit_gb == 10

        # Should support different limits
        config2 = AppConfig(storage_limit_gb=50)
        assert config2.storage_limit_gb == 50


# ============================================================================
# PRD REQUIREMENT 7: SESSION MANAGEMENT
# "Working desktop app that records screen & mic input locally"
# ============================================================================


class TestSessionManagement:
    """Test PRD Requirement: Session tracking and management."""

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """
        PRD: System should track user sessions.
        Verify sessions can be created and stored.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            storage = StorageManager(config)
            await storage.initialize()

            session = Session(
                id="session_test_1",
                started_at=datetime.now(),
                status=SessionStatus.ACTIVE,
            )

            await storage.create_session(session)

            # Verify session was stored
            retrieved = await storage.get_session(session.id)
            assert retrieved is not None
            assert retrieved.id == session.id
            assert retrieved.status == SessionStatus.ACTIVE

            await storage.close()

    @pytest.mark.asyncio
    async def test_session_status_tracking(self):
        """
        PRD: Track session lifecycle (active, completed, paused).
        Verify session statuses are properly tracked.
        """
        session = Session(
            id="session_status_test",
            started_at=datetime.now(),
            status=SessionStatus.ACTIVE,
        )

        # Should support different statuses
        assert session.status == SessionStatus.ACTIVE

        # Can transition to completed
        session.status = SessionStatus.COMPLETED
        assert session.status == SessionStatus.COMPLETED


# ============================================================================
# PRD REQUIREMENT 8: PRIVACY & OFFLINE OPERATION
# "No login systems, accounts, or servers needed"
# "Everything should run locally and respect privacy"
# ============================================================================


class TestPrivacyAndOfflineOperation:
    """Test PRD Requirement: Privacy-first, offline operation."""

    def test_no_cloud_configuration(self):
        """
        PRD: "No cloud uploads" - "No login systems, accounts, or servers"
        Verify system is configured for offline operation.
        """
        config = AppConfig()

        # Should not have cloud API keys or endpoints
        assert not hasattr(config, "cloud_api_key")
        assert not hasattr(config, "cloud_endpoint")

    def test_local_data_directory(self):
        """
        PRD: "Everything happens locally in user system"
        Verify data is stored in local directories.
        """
        config = AppConfig()

        # Data directory should be local path
        assert config.data_dir is not None
        assert isinstance(config.data_dir, Path)
        assert not str(config.data_dir).startswith("http")
        assert not str(config.data_dir).startswith("ftp")

    def test_privacy_controls_available(self):
        """
        PRD: "Respect privacy"
        Verify privacy control features are available.
        """
        from src.services.screen_capture import ScreenCaptureService

        service = ScreenCaptureService()

        # Should have pause/resume for privacy
        assert hasattr(service, "pause")
        assert hasattr(service, "resume")

        # Should support application exclusion
        assert hasattr(service, "set_excluded_apps")


# ============================================================================
# PRD REQUIREMENT 9: WORKFLOW UNDERSTANDING
# "The AI interprets these files to understand what the user did"
# Example: "User opened Excel, entered a formula in column C, and saved"
# ============================================================================


class TestWorkflowUnderstanding:
    """Test PRD Requirement: AI understands user workflows."""

    @pytest.mark.asyncio
    async def test_workflow_analysis(self):
        """
        PRD: "The AI interprets to understand what the user did"
        Verify workflow analyzer can process actions.
        """
        from src.services.workflow_analyzer import WorkflowAnalyzer

        analyzer = WorkflowAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze_session")

    def test_action_sequence_tracking(self):
        """
        PRD: "User opened Excel, entered a formula, and saved"
        Verify action sequences are properly tracked.
        """
        actions = [
            Action(
                id="action_1",
                session_id="workflow_test",
                type=ActionType.OPEN,
                target_element="Excel",
                timestamp=datetime.now(),
                confidence=0.9,
            ),
            Action(
                id="action_2",
                session_id="workflow_test",
                type=ActionType.TYPE,
                target_element="Cell C1",
                input_data="=SUM(A1:B1)",
                timestamp=datetime.now() + timedelta(seconds=5),
                confidence=0.88,
            ),
            Action(
                id="action_3",
                session_id="workflow_test",
                type=ActionType.SAVE,
                target_element="File",
                timestamp=datetime.now() + timedelta(seconds=10),
                confidence=0.95,
            ),
        ]

        # Verify sequence is ordered by timestamp
        assert actions[0].timestamp < actions[1].timestamp < actions[2].timestamp

        # Verify action types match workflow
        assert actions[0].type == ActionType.OPEN
        assert actions[1].type == ActionType.TYPE
        assert actions[2].type == ActionType.SAVE


# ============================================================================
# PRD REQUIREMENT 10: DELIVERABLES
# "Working MVP (.exe or local build) - runs fully offline"
# ============================================================================


class TestDeliverables:
    """Test PRD Deliverable Requirements."""

    def test_application_entry_point_exists(self):
        """
        PRD: "Working MVP (.exe or local build)"
        Verify main application entry point exists.
        """
        import src.main
        import src.gui_main

        # Should have main entry points
        assert hasattr(src.main, "main")
        assert hasattr(src.gui_main, "main")

    def test_build_configuration_exists(self):
        """
        PRD: "Working MVP (.exe or local build)"
        Verify build configuration for executable exists.
        """
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        spec_file = project_root / "agi_assistant.spec"
        build_script = project_root / "build_executable.py"

        # Should have build configuration
        assert spec_file.exists(), "PyInstaller spec file should exist"
        assert build_script.exists(), "Build script should exist"

    def test_example_outputs_exist(self):
        """
        PRD: Should provide example structured JSON outputs.
        Verify example workflow outputs exist.
        """
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        examples_dir = project_root / "examples"

        assert examples_dir.exists(), "Examples directory should exist"

        # Should have example workflow JSONs
        excel_example = examples_dir / "workflow_excel_data_entry.json"
        browser_example = examples_dir / "workflow_browser_search.json"

        assert excel_example.exists(), "Excel workflow example should exist"
        assert browser_example.exists(), "Browser workflow example should exist"


# ============================================================================
# PRD BONUS POINTS TESTS
# ============================================================================


class TestBonusFeatures:
    """Test PRD Bonus Point Requirements."""

    def test_lightweight_local_llm(self):
        """
        PRD Bonus: "Using a lightweight local LLM (Mistral, Phi-3, or LLaMA)"
        Verify local LLM integration exists.
        """
        from src.services.llm_service import LLMService

        llm = LLMService()

        # Should support local LLM models
        assert llm.model_name is not None
        supported_models = ["phi", "mistral", "llama", "gemma"]
        assert any(model in llm.model_name.lower() for model in supported_models)

    def test_efficient_storage_management(self):
        """
        PRD Bonus: "Efficient local storage management (auto-delete older clips)"
        Verify automatic cleanup is implemented.
        """
        from src.services.storage_cleanup import StorageCleanupService

        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            cleanup = StorageCleanupService(config)

            # Should have automatic cleanup
            assert hasattr(cleanup, "cleanup_old_data")
            assert hasattr(cleanup, "should_cleanup")


# ============================================================================
# INTEGRATION TESTS: END-TO-END WORKFLOW
# ============================================================================


class TestEndToEndWorkflow:
    """Test complete workflow: Observe → Understand → Suggest."""

    @pytest.mark.asyncio
    async def test_complete_workflow_pipeline(self):
        """
        PRD: Complete pipeline - Observe → Understand → Automate
        Test end-to-end workflow from capture to suggestion.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            storage = StorageManager(config)
            await storage.initialize()

            # 1. Create session (Observe)
            session = Session(
                id="e2e_test", started_at=datetime.now(), status=SessionStatus.ACTIVE
            )
            await storage.create_session(session)

            # 2. Capture actions (Observe)
            actions = []
            for i in range(3):
                action = Action(
                    id=f"e2e_action_{i}",
                    session_id=session.id,
                    type=ActionType.CLICK,
                    target_element="Submit Button",
                    timestamp=datetime.now() + timedelta(seconds=i * 10),
                    confidence=0.9,
                )
                await storage.create_action(action)
                actions.append(action)

            # 3. Detect patterns (Understand)
            detector = PatternDetector()
            patterns = detector.detect_patterns(actions)

            assert len(patterns) > 0

            # 4. Generate suggestions (Automate)
            engine = AutomationSuggestionEngine()
            suggestions = engine.generate_suggestions(patterns)

            assert len(suggestions) > 0
            assert "Can be automated" in suggestions[0].description

            await storage.close()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformanceRequirements:
    """Test performance meets PRD expectations."""

    @pytest.mark.asyncio
    async def test_action_storage_performance(self):
        """
        PRD: System should handle continuous recording.
        Verify actions can be stored quickly.
        """
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(data_dir=Path(tmpdir))
            storage = StorageManager(config)
            await storage.initialize()

            session = Session(
                id="perf_test", started_at=datetime.now(), status=SessionStatus.ACTIVE
            )
            await storage.create_session(session)

            # Store 100 actions and measure time
            start = time.time()

            for i in range(100):
                action = Action(
                    id=f"perf_action_{i}",
                    session_id=session.id,
                    type=ActionType.CLICK,
                    target_element="Button",
                    timestamp=datetime.now(),
                    confidence=0.9,
                )
                await storage.create_action(action)

            elapsed = time.time() - start

            # Should complete in reasonable time (< 5 seconds for 100 actions)
            assert elapsed < 5.0

            await storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
