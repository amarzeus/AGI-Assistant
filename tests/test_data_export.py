"""Test data export functionality."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.services.data_exporter import DataExporter
from src.database.storage_manager import StorageManager
from src.config import get_config, set_config, AppConfig
from src.models.session import Session, SessionStatus
from src.models.action import Action, ActionType
from src.models.transcription import Transcription


async def test_data_export():
    """Test data export functionality."""
    print("Testing Data Export Service")
    print("=" * 50)
    
    # Create temporary data directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temp directory: {temp_dir}")
    
    try:
        # Configure with temp directory
        config = AppConfig()
        config.data_dir = temp_dir
        set_config(config)
        config.ensure_directories()
        
        # Initialize storage manager
        storage_manager = StorageManager()
        await storage_manager.initialize()
        
        # Initialize data exporter
        data_exporter = DataExporter()
        await data_exporter.initialize()
        
        print("\n1. Creating test data...")
        
        # Create test session
        session = Session(
            id="test-session-001",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            status=SessionStatus.COMPLETED,
            capture_count=10,
            transcription_count=5,
            detected_actions=8,
            storage_size=1024000
        )
        await storage_manager.save_session(session)
        
        # Create test actions
        actions = []
        for i in range(5):
            action = Action(
                id=f"action-{i:03d}",
                session_id=session.id,
                timestamp=datetime.now() - timedelta(minutes=30-i*5),
                type=ActionType.CLICK if i % 2 == 0 else ActionType.TYPE,
                application="TestApp",
                window_title="Test Window",
                target_element=f"Button{i}",
                input_data=f"test input {i}" if i % 2 == 1 else None,
                screenshot_path=f"screenshot_{i}.png",
                confidence=0.85 + (i * 0.02)
            )
            actions.append(action)
            await storage_manager.save_action(action)
        
        # Create test transcriptions
        transcriptions = []
        for i in range(3):
            transcription = Transcription(
                id=f"transcription-{i:03d}",
                timestamp=datetime.now() - timedelta(minutes=25-i*8),
                text=f"This is test transcription number {i}",
                confidence=0.90 + (i * 0.02),
                language="en",
                duration=2.5
            )
            transcriptions.append(transcription)
            await storage_manager.save_transcription(transcription)
        
        print(f"   Created session: {session.id}")
        print(f"   Created {len(actions)} actions")
        print(f"   Created {len(transcriptions)} transcriptions")
        
        print("\n2. Testing JSON export...")
        
        # Test JSON export
        json_result = await data_exporter.export_workflow_data(
            session_id=session.id,
            format='json',
            include_patterns=False,  # No patterns created in this test
            include_suggestions=False  # No suggestions created in this test
        )
        
        print(f"   JSON export success: {json_result['success']}")
        print(f"   Export file: {json_result.get('export_file', 'N/A')}")
        print(f"   Records exported: {json_result.get('records_exported', 0)}")
        print(f"   File size: {json_result.get('file_size_bytes', 0)} bytes")
        
        # Verify JSON file exists and has content
        if json_result['success']:
            json_file = Path(json_result['export_file'])
            if json_file.exists():
                print(f"   ✓ JSON file exists: {json_file.name}")
                
                # Read and verify content
                import json
                with open(json_file, 'r') as f:
                    json_data = json.load(f)
                
                print(f"   ✓ Sessions in export: {len(json_data.get('sessions', []))}")
                print(f"   ✓ Actions in export: {len(json_data.get('actions', []))}")
                print(f"   ✓ Transcriptions in export: {len(json_data.get('transcriptions', []))}")
                print(f"   ✓ Metadata included: {'metadata' in json_data}")
        
        print("\n3. Testing YAML export...")
        
        # Test YAML export
        yaml_result = await data_exporter.export_workflow_data(
            session_id=session.id,
            format='yaml',
            include_patterns=False,
            include_suggestions=False
        )
        
        print(f"   YAML export success: {yaml_result['success']}")
        print(f"   Export file: {yaml_result.get('export_file', 'N/A')}")
        print(f"   Records exported: {yaml_result.get('records_exported', 0)}")
        
        print("\n4. Testing CSV export...")
        
        # Test CSV export
        csv_result = await data_exporter.export_workflow_data(
            session_id=session.id,
            format='csv',
            include_patterns=False,
            include_suggestions=False
        )
        
        print(f"   CSV export success: {csv_result['success']}")
        print(f"   Export file: {csv_result.get('export_file', 'N/A')}")
        print(f"   Records exported: {csv_result.get('records_exported', 0)}")
        
        print("\n5. Testing date range export...")
        
        # Test date range export
        start_date = datetime.now() - timedelta(hours=2)
        end_date = datetime.now()
        
        range_result = await data_exporter.export_workflow_data(
            start_date=start_date,
            end_date=end_date,
            format='json',
            include_patterns=False,
            include_suggestions=False
        )
        
        print(f"   Date range export success: {range_result['success']}")
        print(f"   Records exported: {range_result.get('records_exported', 0)}")
        
        print("\n6. Testing session backup...")
        
        # Test session backup
        backup_result = await data_exporter.export_session_backup(
            session_id=session.id,
            include_media=False  # No media files in this test
        )
        
        print(f"   Session backup success: {backup_result['success']}")
        print(f"   Backup file: {backup_result.get('backup_file', 'N/A')}")
        print(f"   Actions count: {backup_result.get('actions_count', 0)}")
        print(f"   Transcriptions count: {backup_result.get('transcriptions_count', 0)}")
        
        print("\n7. Testing analytics report...")
        
        # Test analytics report
        analytics_result = await data_exporter.export_analytics_report(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"   Analytics report success: {analytics_result['success']}")
        print(f"   Report file: {analytics_result.get('report_file', 'N/A')}")
        print(f"   Sessions analyzed: {analytics_result.get('sessions_analyzed', 0)}")
        print(f"   Actions analyzed: {analytics_result.get('actions_analyzed', 0)}")
        
        print("\n8. Testing storage manager export...")
        
        # Test storage manager export
        json_export = await storage_manager.export_workflows('json')
        yaml_export = await storage_manager.export_workflows('yaml')
        
        print(f"   Storage manager JSON export length: {len(json_export)} chars")
        print(f"   Storage manager YAML export length: {len(yaml_export)} chars")
        
        print("\n9. Getting export statistics...")
        
        # Get exporter stats
        stats = data_exporter.get_stats()
        print(f"   Exports created: {stats['exports_created']}")
        print(f"   Total records exported: {stats['total_records_exported']}")
        print(f"   Supported formats: {stats['supported_formats']}")
        print(f"   Export path: {stats['export_path']}")
        
        # List export files
        export_path = Path(stats['export_path'])
        if export_path.exists():
            export_files = list(export_path.glob('*'))
            print(f"   Export files created: {len(export_files)}")
            for file in export_files:
                print(f"     - {file.name} ({file.stat().st_size} bytes)")
        
        # Cleanup
        await storage_manager.close()
        
        print("\n✓ Data export service test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temp directory: {temp_dir}")


if __name__ == "__main__":
    asyncio.run(test_data_export())