"""Data export service for Round 2 integration and backup purposes."""

import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import zipfile
import csv

from src.config import get_config
from src.logger import get_app_logger
from src.database.storage_manager import StorageManager
from src.models.session import Session
from src.models.action import Action
from src.models.pattern import Pattern
from src.models.workflow import WorkflowSuggestion
from src.models.transcription import Transcription


class DataExporter:
    """
    Data export service for Round 2 integration and backup purposes.
    
    Features:
    - Export workflows in JSON and YAML formats
    - Export session data with actions and transcriptions
    - Export pattern analysis results
    - Export automation suggestions
    - Create compressed backup archives
    - Support for filtered exports by date range
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Export settings
        self.export_formats = ['json', 'yaml', 'csv']
        self.include_screenshots = False  # Screenshots not included by default due to size
        self.include_video = False  # Video not included by default due to size
        
        # Paths
        self.data_paths = self.config.get_data_paths()
        self.export_path = self.data_paths['exports']
        
        # Storage manager
        self.storage_manager: Optional[StorageManager] = None
        
        # Statistics
        self._exports_created = 0
        self._total_records_exported = 0
        
        self.logger.info("Data exporter initialized")
    
    async def initialize(self) -> None:
        """Initialize data exporter."""
        self.logger.info("Initializing data exporter...")
        
        try:
            # Initialize storage manager
            self.storage_manager = StorageManager()
            await self.storage_manager.initialize()
            
            # Ensure export directory exists
            self.export_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Data exporter initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data exporter: {e}")
            raise
    
    async def export_workflow_data(self, 
                                 session_id: Optional[str] = None,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 format: str = 'json',
                                 include_patterns: bool = True,
                                 include_suggestions: bool = True) -> Dict[str, Any]:
        """
        Export workflow data for Round 2 integration.
        
        Args:
            session_id: Specific session to export (optional)
            start_date: Start date for export range (optional)
            end_date: End date for export range (optional)
            format: Export format ('json', 'yaml', 'csv')
            include_patterns: Include pattern analysis results
            include_suggestions: Include automation suggestions
            
        Returns:
            Dictionary with export results
        """
        try:
            if not self.storage_manager:
                raise ValueError("Storage manager not initialized")
            
            self.logger.info(f"Starting workflow data export (format={format})")
            
            # Determine date range
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)  # Default to last 30 days
            if not end_date:
                end_date = datetime.now()
            
            # Collect data
            export_data = {}
            
            # Export sessions
            if session_id:
                sessions = [await self.storage_manager.get_session(session_id)]
                sessions = [s for s in sessions if s is not None]
            else:
                sessions = await self.storage_manager.get_sessions_by_date_range(start_date, end_date)
            
            export_data['sessions'] = await self._export_sessions_data(sessions)
            
            # Export actions
            actions = await self.storage_manager.get_actions_by_time_range(start_date, end_date)
            export_data['actions'] = await self._export_actions_data(actions)
            
            # Export transcriptions
            transcriptions = await self.storage_manager.get_transcriptions_by_time_range(start_date, end_date)
            export_data['transcriptions'] = await self._export_transcriptions_data(transcriptions)
            
            # Export patterns if requested
            if include_patterns:
                patterns = await self.storage_manager.get_patterns_by_time_range(start_date, end_date)
                export_data['patterns'] = await self._export_patterns_data(patterns)
            
            # Export suggestions if requested
            if include_suggestions:
                suggestions = await self.storage_manager.get_workflow_suggestions_by_time_range(start_date, end_date)
                export_data['workflow_suggestions'] = await self._export_suggestions_data(suggestions)
            
            # Add metadata
            export_data['metadata'] = {
                'export_timestamp': datetime.now().isoformat(),
                'export_format': format,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'session_id': session_id,
                'include_patterns': include_patterns,
                'include_suggestions': include_suggestions,
                'total_sessions': len(export_data['sessions']),
                'total_actions': len(export_data['actions']),
                'total_transcriptions': len(export_data['transcriptions'])
            }
            
            # Save export file
            export_filename = self._generate_export_filename(format, session_id, start_date, end_date)
            export_filepath = await self._save_export_data(export_data, export_filename, format)
            
            # Update statistics
            self._exports_created += 1
            self._total_records_exported += (
                len(export_data['sessions']) + 
                len(export_data['actions']) + 
                len(export_data['transcriptions'])
            )
            
            result = {
                'success': True,
                'export_file': str(export_filepath),
                'format': format,
                'records_exported': (len(export_data.get('sessions', [])) + 
                                  len(export_data.get('actions', [])) + 
                                  len(export_data.get('transcriptions', []))),
                'file_size_bytes': export_filepath.stat().st_size if export_filepath.exists() else 0
            }
            
            self.logger.info(f"Workflow data export completed: {result['records_exported']} records")
            return result
            
        except Exception as e:
            self.logger.error(f"Error exporting workflow data: {e}")
            return {'success': False, 'error': str(e)}
    
    async def export_session_backup(self, 
                                  session_id: str,
                                  include_media: bool = False) -> Dict[str, Any]:
        """
        Export complete session backup including media files.
        
        Args:
            session_id: Session ID to backup
            include_media: Include screenshots and video files
            
        Returns:
            Dictionary with backup results
        """
        try:
            if not self.storage_manager:
                raise ValueError("Storage manager not initialized")
            
            self.logger.info(f"Starting session backup for session {session_id}")
            
            # Get session data
            session = await self.storage_manager.get_session(session_id)
            if not session:
                return {'success': False, 'error': f'Session {session_id} not found'}
            
            # Create backup directory
            backup_dir = self.export_path / f"session_backup_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Export session data
            session_data = await self._export_sessions_data([session])
            actions = await self.storage_manager.get_actions_by_session(session_id)
            actions_data = await self._export_actions_data(actions)
            transcriptions = await self.storage_manager.get_transcriptions_by_session(session_id)
            transcriptions_data = await self._export_transcriptions_data(transcriptions)
            
            # Save structured data
            structured_data = {
                'session': session_data[0] if session_data else None,
                'actions': actions_data,
                'transcriptions': transcriptions_data,
                'metadata': {
                    'backup_timestamp': datetime.now().isoformat(),
                    'session_id': session_id,
                    'include_media': include_media
                }
            }
            
            # Save JSON file
            json_file = backup_dir / 'session_data.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            
            # Copy media files if requested
            media_files_copied = 0
            if include_media:
                session_media_dir = self.data_paths['sessions'] / session_id
                if session_media_dir.exists():
                    # Copy screenshots
                    screenshots_src = session_media_dir / 'screenshots'
                    if screenshots_src.exists():
                        screenshots_dst = backup_dir / 'screenshots'
                        screenshots_dst.mkdir(exist_ok=True)
                        for screenshot in screenshots_src.glob('*.png'):
                            screenshot_dst = screenshots_dst / screenshot.name
                            screenshot_dst.write_bytes(screenshot.read_bytes())
                            media_files_copied += 1
                    
                    # Copy video files
                    video_src = session_media_dir / 'video'
                    if video_src.exists():
                        video_dst = backup_dir / 'video'
                        video_dst.mkdir(exist_ok=True)
                        for video in video_src.glob('*.mp4'):
                            video_dst_file = video_dst / video.name
                            video_dst_file.write_bytes(video.read_bytes())
                            media_files_copied += 1
            
            # Create ZIP archive
            zip_file = self.export_path / f"session_backup_{session_id}.zip"
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in backup_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_dir)
                        zipf.write(file_path, arcname)
            
            # Clean up temporary directory
            import shutil
            shutil.rmtree(backup_dir)
            
            result = {
                'success': True,
                'backup_file': str(zip_file),
                'session_id': session_id,
                'actions_count': len(actions_data),
                'transcriptions_count': len(transcriptions_data),
                'media_files_copied': media_files_copied,
                'file_size_bytes': zip_file.stat().st_size
            }
            
            self.logger.info(f"Session backup completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating session backup: {e}")
            return {'success': False, 'error': str(e)}
    
    async def export_analytics_report(self, 
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Export analytics report with patterns and automation suggestions.
        
        Args:
            start_date: Start date for report (optional)
            end_date: End date for report (optional)
            
        Returns:
            Dictionary with report results
        """
        try:
            if not self.storage_manager:
                raise ValueError("Storage manager not initialized")
            
            # Determine date range
            if not start_date:
                start_date = datetime.now() - timedelta(days=7)  # Default to last week
            if not end_date:
                end_date = datetime.now()
            
            self.logger.info(f"Generating analytics report for {start_date.date()} to {end_date.date()}")
            
            # Collect analytics data
            sessions = await self.storage_manager.get_sessions_by_date_range(start_date, end_date)
            actions = await self.storage_manager.get_actions_by_time_range(start_date, end_date)
            patterns = await self.storage_manager.get_patterns_by_time_range(start_date, end_date)
            suggestions = await self.storage_manager.get_workflow_suggestions_by_time_range(start_date, end_date)
            
            # Generate analytics
            analytics = {
                'summary': {
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'total_sessions': len(sessions),
                    'total_actions': len(actions),
                    'total_patterns': len(patterns),
                    'total_suggestions': len(suggestions),
                    'avg_actions_per_session': len(actions) / len(sessions) if sessions else 0
                },
                'action_breakdown': self._analyze_action_types(actions),
                'pattern_analysis': self._analyze_patterns(patterns),
                'automation_opportunities': self._analyze_suggestions(suggestions),
                'time_analysis': self._analyze_time_patterns(actions),
                'application_usage': self._analyze_application_usage(actions)
            }
            
            # Save report
            report_filename = f"analytics_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
            report_filepath = self.export_path / report_filename
            
            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(analytics, f, indent=2, ensure_ascii=False)
            
            result = {
                'success': True,
                'report_file': str(report_filepath),
                'date_range': f"{start_date.date()} to {end_date.date()}",
                'sessions_analyzed': len(sessions),
                'actions_analyzed': len(actions),
                'patterns_found': len(patterns),
                'suggestions_generated': len(suggestions)
            }
            
            self.logger.info(f"Analytics report generated: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating analytics report: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _export_sessions_data(self, sessions: List[Session]) -> List[Dict[str, Any]]:
        """Export sessions data to dictionary format."""
        return [
            {
                'id': session.id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'status': session.status.value,
                'capture_count': session.capture_count,
                'transcription_count': session.transcription_count,
                'detected_actions': session.detected_actions,
                'storage_size_bytes': session.storage_size,
                'duration_seconds': session.duration_seconds,
                'metadata': session.metadata
            }
            for session in sessions
        ]
    
    async def _export_actions_data(self, actions: List[Action]) -> List[Dict[str, Any]]:
        """Export actions data to dictionary format."""
        return [
            {
                'id': action.id,
                'session_id': action.session_id,
                'timestamp': action.timestamp.isoformat(),
                'type': action.type.value,
                'application': action.application,
                'window_title': action.window_title,
                'target_element': action.target_element,
                'input_data': action.input_data,
                'screenshot_path': action.screenshot_path,
                'confidence': action.confidence,
                'metadata': action.metadata
            }
            for action in actions
        ]
    
    async def _export_transcriptions_data(self, transcriptions: List[Transcription]) -> List[Dict[str, Any]]:
        """Export transcriptions data to dictionary format."""
        return [
            {
                'id': transcription.id,
                'session_id': transcription.session_id,
                'timestamp': transcription.timestamp.isoformat(),
                'text': transcription.text,
                'confidence': transcription.confidence,
                'language': transcription.language,
                'duration_seconds': transcription.duration_seconds
            }
            for transcription in transcriptions
        ]
    
    async def _export_patterns_data(self, patterns: List[Pattern]) -> List[Dict[str, Any]]:
        """Export patterns data to dictionary format."""
        return [
            {
                'id': pattern.id,
                'pattern_type': pattern.pattern_type,
                'description': pattern.description,
                'actions_involved': pattern.actions_involved if isinstance(pattern.actions_involved, list) else [],
                'frequency': pattern.frequency,
                'confidence': pattern.confidence,
                'automation_potential': pattern.automation_potential,
                'automation_feasibility': pattern.automation_feasibility,
                'first_occurrence': pattern.first_occurrence.isoformat(),
                'last_occurrence': pattern.last_occurrence.isoformat()
            }
            for pattern in patterns
        ]
    
    async def _export_suggestions_data(self, suggestions: List[WorkflowSuggestion]) -> List[Dict[str, Any]]:
        """Export workflow suggestions data to dictionary format."""
        return [
            {
                'id': suggestion.id,
                'title': suggestion.title,
                'description': suggestion.description,
                'automation_type': suggestion.automation_type,
                'complexity': suggestion.complexity,
                'confidence': suggestion.confidence,
                'time_saved_estimate': suggestion.time_saved_estimate,
                'implementation_steps': suggestion.implementation_steps,
                'created_at': suggestion.created_at.isoformat()
            }
            for suggestion in suggestions
        ]
    
    def _generate_export_filename(self, format: str, session_id: Optional[str], 
                                start_date: datetime, end_date: datetime) -> str:
        """Generate export filename based on parameters."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if session_id:
            base_name = f"session_{session_id}_{timestamp}"
        else:
            date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            base_name = f"workflow_export_{date_range}_{timestamp}"
        
        return f"{base_name}.{format}"
    
    async def _save_export_data(self, data: Dict[str, Any], filename: str, format: str) -> Path:
        """Save export data in specified format."""
        filepath = self.export_path / filename
        
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == 'yaml':
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        elif format == 'csv':
            # For CSV, we'll create separate files for each data type
            base_path = filepath.with_suffix('')
            
            # Export sessions
            if 'sessions' in data and data['sessions']:
                sessions_file = base_path.with_name(f"{base_path.name}_sessions.csv")
                self._save_csv_data(data['sessions'], sessions_file)
            
            # Export actions
            if 'actions' in data and data['actions']:
                actions_file = base_path.with_name(f"{base_path.name}_actions.csv")
                self._save_csv_data(data['actions'], actions_file)
            
            # Export transcriptions
            if 'transcriptions' in data and data['transcriptions']:
                transcriptions_file = base_path.with_name(f"{base_path.name}_transcriptions.csv")
                self._save_csv_data(data['transcriptions'], transcriptions_file)
            
            # Create a summary file
            summary_file = base_path.with_suffix('.csv')
            with open(summary_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Export Summary'])
                writer.writerow(['Export Time', data['metadata']['export_timestamp']])
                writer.writerow(['Total Sessions', data['metadata']['total_sessions']])
                writer.writerow(['Total Actions', data['metadata']['total_actions']])
                writer.writerow(['Total Transcriptions', data['metadata']['total_transcriptions']])
            
            filepath = summary_file
        
        return filepath
    
    def _save_csv_data(self, data: List[Dict[str, Any]], filepath: Path) -> None:
        """Save data as CSV file."""
        if not data:
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    
    def _analyze_action_types(self, actions: List[Action]) -> Dict[str, Any]:
        """Analyze action types distribution."""
        if not actions:
            return {}
        
        type_counts = {}
        for action in actions:
            action_type = action.type.value
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
        
        total_actions = len(actions)
        return {
            'counts': type_counts,
            'percentages': {k: (v / total_actions) * 100 for k, v in type_counts.items()},
            'most_common': max(type_counts.items(), key=lambda x: x[1]) if type_counts else None
        }
    
    def _analyze_patterns(self, patterns: List[Pattern]) -> Dict[str, Any]:
        """Analyze detected patterns."""
        if not patterns:
            return {}
        
        return {
            'total_patterns': len(patterns),
            'avg_frequency': sum(p.frequency for p in patterns) / len(patterns),
            'avg_confidence': sum(p.confidence for p in patterns) / len(patterns),
            'avg_automation_feasibility': sum(p.automation_feasibility for p in patterns) / len(patterns),
            'high_frequency_patterns': len([p for p in patterns if p.frequency >= 5]),
            'high_confidence_patterns': len([p for p in patterns if p.confidence >= 0.8]),
            'automatable_patterns': len([p for p in patterns if p.automation_feasibility >= 0.7])
        }
    
    def _analyze_suggestions(self, suggestions: List[WorkflowSuggestion]) -> Dict[str, Any]:
        """Analyze automation suggestions."""
        if not suggestions:
            return {}
        
        complexity_counts = {}
        automation_types = {}
        
        for suggestion in suggestions:
            complexity_counts[suggestion.complexity] = complexity_counts.get(suggestion.complexity, 0) + 1
            automation_types[suggestion.automation_type] = automation_types.get(suggestion.automation_type, 0) + 1
        
        return {
            'total_suggestions': len(suggestions),
            'avg_confidence': sum(s.confidence for s in suggestions) / len(suggestions),
            'complexity_distribution': complexity_counts,
            'automation_type_distribution': automation_types,
            'high_confidence_suggestions': len([s for s in suggestions if s.confidence >= 0.8])
        }
    
    def _analyze_time_patterns(self, actions: List[Action]) -> Dict[str, Any]:
        """Analyze time-based patterns in actions."""
        if not actions:
            return {}
        
        hour_counts = {}
        day_counts = {}
        
        for action in actions:
            hour = action.timestamp.hour
            day = action.timestamp.strftime('%A')
            
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            day_counts[day] = day_counts.get(day, 0) + 1
        
        return {
            'hourly_distribution': hour_counts,
            'daily_distribution': day_counts,
            'peak_hour': max(hour_counts.items(), key=lambda x: x[1]) if hour_counts else None,
            'peak_day': max(day_counts.items(), key=lambda x: x[1]) if day_counts else None
        }
    
    def _analyze_application_usage(self, actions: List[Action]) -> Dict[str, Any]:
        """Analyze application usage patterns."""
        if not actions:
            return {}
        
        app_counts = {}
        for action in actions:
            app = action.application or 'Unknown'
            app_counts[app] = app_counts.get(app, 0) + 1
        
        total_actions = len(actions)
        return {
            'application_counts': app_counts,
            'application_percentages': {k: (v / total_actions) * 100 for k, v in app_counts.items()},
            'most_used_application': max(app_counts.items(), key=lambda x: x[1]) if app_counts else None,
            'unique_applications': len(app_counts)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data exporter statistics."""
        return {
            'exports_created': self._exports_created,
            'total_records_exported': self._total_records_exported,
            'supported_formats': self.export_formats,
            'export_path': str(self.export_path),
            'include_screenshots': self.include_screenshots,
            'include_video': self.include_video
        }