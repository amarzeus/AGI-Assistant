#!/usr/bin/env python3
"""
Integration test for all AGI Assistant services.
Tests the complete workflow from pattern detection to data export.
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.services.pattern_detector import PatternDetector
from src.services.storage_monitor import StorageMonitor
from src.services.data_exporter import DataExporter
from src.services.automation_engine import AutomationSuggestionEngine
from src.models.session import Session, SessionStatus
from src.models.action import Action, ActionType
from src.models.transcription import Transcription


async def test_services_integration():
    """Test integration of all services."""
    logger = get_app_logger()
    logger.info("Starting services integration test")
    
    try:
        # Initialize services
        storage_manager = StorageManager()
        await storage_manager.initialize()
        
        pattern_detector = PatternDetector()
        await pattern_detector.initialize()
        
        storage_monitor = StorageMonitor()
        await storage_monitor.initialize()
        
        data_exporter = DataExporter()
        await data_exporter.initialize()
        
        automation_engine = AutomationSuggestionEngine()
        await automation_engine.initialize()
        
        logger.info("All services initialized successfully")
        
        # Create test session
        import uuid
        session = Session(
            id=str(uuid.uuid4()),
            start_time=datetime.now() - timedelta(minutes=30),
            end_time=datetime.now(),
            status=SessionStatus.COMPLETED
        )
        await storage_manager.save_session(session)
        logger.info(f"Created test session: {session.id}")
        
        # Create test actions (repetitive pattern)
        test_actions = []
        base_time = datetime.now() - timedelta(minutes=25)
        
        # Create a repetitive pattern: click -> type -> click (repeated 3 times)
        for i in range(3):
            time_offset = i * 5  # 5 minutes apart
            
            # Click action
            click_action = Action(
                session_id=session.id,
                timestamp=base_time + timedelta(minutes=time_offset),
                type=ActionType.CLICK,
                application="Excel",
                window_title="Microsoft Excel",
                target_element="Button",
                confidence=0.9
            )
            test_actions.append(click_action)
            
            # Type action
            type_action = Action(
                session_id=session.id,
                timestamp=base_time + timedelta(minutes=time_offset, seconds=30),
                type=ActionType.TYPE,
                application="Excel",
                window_title="Microsoft Excel",
                target_element="TextBox",
                input_data="test data",
                confidence=0.85
            )
            test_actions.append(type_action)
            
            # Another click action
            click2_action = Action(
                session_id=session.id,
                timestamp=base_time + timedelta(minutes=time_offset, seconds=60),
                type=ActionType.CLICK,
                application="Excel",
                window_title="Microsoft Excel",
                target_element="SaveButton",
                confidence=0.9
            )
            test_actions.append(click2_action)
        
        # Save actions
        for action in test_actions:
            await storage_manager.save_action(action)
        
        logger.info(f"Created {len(test_actions)} test actions")
        
        # Create test transcription
        transcription = Transcription(
            session_id=session.id,
            timestamp=base_time + timedelta(minutes=10),
            text="I need to enter this data into Excel",
            confidence=0.9,
            language="en",
            duration_seconds=3.5
        )
        await storage_manager.save_transcription(transcription)
        logger.info("Created test transcription")
        
        # Test pattern detection
        logger.info("Testing pattern detection...")
        patterns = await pattern_detector.detect_patterns_in_actions(test_actions)
        logger.info(f"Detected {len(patterns)} patterns")
        
        for pattern in patterns:
            logger.info(f"Pattern: {pattern.description} (frequency: {pattern.frequency}, feasibility: {pattern.automation_feasibility:.2f})")
        
        # Test automation suggestions
        if patterns:
            logger.info("Testing automation suggestion generation...")
            suggestions = await automation_engine.generate_suggestions_from_patterns(patterns)
            logger.info(f"Generated {len(suggestions)} automation suggestions")
            
            for suggestion in suggestions:
                logger.info(f"Suggestion: {suggestion.title} (confidence: {suggestion.confidence:.2f}, complexity: {suggestion.complexity})")
        
        # Test storage monitoring
        logger.info("Testing storage monitoring...")
        storage_stats = await storage_monitor.get_storage_stats()
        logger.info(f"Storage stats: {storage_stats.total_used_gb:.3f}GB used, {storage_stats.session_count} sessions")
        
        # Test data export
        logger.info("Testing data export...")
        export_result = await data_exporter.export_workflow_data(
            session_id=session.id,
            format='json',
            include_patterns=True,
            include_suggestions=True
        )
        
        if export_result['success']:
            logger.info(f"Export successful: {export_result['records_exported']} records exported to {export_result['export_file']}")
            
            # Verify export file
            export_path = Path(export_result['export_file'])
            if export_path.exists():
                with open(export_path, 'r') as f:
                    export_data = json.load(f)
                
                logger.info(f"Export contains: {len(export_data.get('sessions', []))} sessions, "
                          f"{len(export_data.get('actions', []))} actions, "
                          f"{len(export_data.get('transcriptions', []))} transcriptions, "
                          f"{len(export_data.get('patterns', []))} patterns")
        else:
            logger.error(f"Export failed: {export_result.get('error', 'Unknown error')}")
        
        # Test analytics report
        logger.info("Testing analytics report generation...")
        analytics_result = await data_exporter.export_analytics_report(
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now()
        )
        
        if analytics_result['success']:
            logger.info(f"Analytics report generated: {analytics_result['report_file']}")
        else:
            logger.error(f"Analytics report failed: {analytics_result.get('error', 'Unknown error')}")
        
        # Test service statistics
        logger.info("Service statistics:")
        logger.info(f"Pattern Detector: {pattern_detector.get_stats()}")
        logger.info(f"Storage Monitor: {storage_monitor.get_stats()}")
        logger.info(f"Data Exporter: {data_exporter.get_stats()}")
        logger.info(f"Automation Engine: {automation_engine.get_stats()}")
        
        logger.info("Services integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Services integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("AGI Assistant Services Integration Test")
    print("=" * 50)
    
    success = await test_services_integration()
    
    if success:
        print("\n✅ All services integration tests passed!")
        return 0
    else:
        print("\n❌ Services integration tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)