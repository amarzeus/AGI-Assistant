"""Storage manager for database operations and file management."""

import aiosqlite
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import json
import gzip
import shutil

from src.config import get_config
from src.logger import get_storage_logger
from src.database.schema import get_init_schema, SCHEMA_VERSION
from src.models.session import Session, SessionStatus
from src.models.action import Action
from src.models.pattern import Pattern
from src.models.transcription import Transcription
from src.models.workflow import WorkflowSuggestion
from src.models.storage import StorageStats


class StorageManager:
    """
    Manages local data storage, retention, and cleanup.
    
    Handles SQLite database operations and file system management.
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_storage_logger()
        self.db_path = self.config.get_data_paths()['db'] / 'agi_assistant.db'
        self._db: Optional[aiosqlite.Connection] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database and create tables."""
        if self._initialized:
            return
        
        self.logger.info("Initializing storage manager")
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        
        # Enable WAL mode for better concurrent access
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        
        # Create schema
        for statement in get_init_schema():
            await self._db.execute(statement)
        
        # Check/update schema version
        await self._ensure_schema_version()
        
        await self._db.commit()
        self._initialized = True
        
        self.logger.info("Storage manager initialized successfully")
    
    async def _ensure_schema_version(self) -> None:
        """Ensure database schema is at correct version."""
        cursor = await self._db.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = await cursor.fetchone()
        
        if row is None:
            # First time setup
            await self._db.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            self.logger.info(f"Database schema initialized at version {SCHEMA_VERSION}")
        elif row['version'] < SCHEMA_VERSION:
            # Migration needed (implement migrations here in future)
            self.logger.warning(f"Database schema migration needed: {row['version']} -> {SCHEMA_VERSION}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False
            self.logger.info("Storage manager closed")
    
    # Session operations
    async def save_session(self, session: Session) -> None:
        """Save or update session."""
        await self._ensure_initialized()
        
        data = session.to_dict()
        await self._db.execute("""
            INSERT OR REPLACE INTO sessions 
            (id, start_time, end_time, capture_count, transcription_count, 
             detected_actions, storage_size, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['start_time'], data['end_time'],
            data['capture_count'], data['transcription_count'],
            data['detected_actions'], data['storage_size'],
            data['status'], data['metadata']
        ))
        await self._db.commit()
        
        self.logger.info(f"Session saved: {session.id}")
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return Session.from_dict(dict(row))
        return None
    
    async def get_active_sessions(self) -> List[Session]:
        """Get all active sessions."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE status = ? ORDER BY start_time DESC",
            (SessionStatus.ACTIVE.value,)
        )
        rows = await cursor.fetchall()
        
        return [Session.from_dict(dict(row)) for row in rows]
    
    async def get_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Session]:
        """Get sessions within date range."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM sessions 
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time DESC
        """, (start_date.isoformat(), end_date.isoformat()))
        rows = await cursor.fetchall()
        
        return [Session.from_dict(dict(row)) for row in rows]
    
    # Action operations
    async def save_action(self, action: Action) -> None:
        """Save action."""
        await self._ensure_initialized()
        
        data = action.to_dict()
        await self._db.execute("""
            INSERT OR REPLACE INTO actions
            (id, session_id, type, timestamp, application, window_title,
             target_element, input_data, screenshot_path, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['session_id'], data['type'], data['timestamp'],
            data['application'], data['window_title'], data['target_element'],
            data['input_data'], data['screenshot_path'], data['confidence'],
            data['metadata']
        ))
        await self._db.commit()
    
    async def get_actions_by_session(self, session_id: str) -> List[Action]:
        """Get all actions for a session."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute(
            "SELECT * FROM actions WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        rows = await cursor.fetchall()
        
        return [Action.from_dict(dict(row)) for row in rows]
    
    async def get_actions_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Action]:
        """Get actions within time range."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM actions
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (start_time.isoformat(), end_time.isoformat()))
        rows = await cursor.fetchall()
        
        return [Action.from_dict(dict(row)) for row in rows]
    
    # Pattern operations
    async def save_pattern(self, pattern: Pattern) -> None:
        """Save or update pattern."""
        await self._ensure_initialized()
        
        data = pattern.to_dict()
        await self._db.execute("""
            INSERT OR REPLACE INTO patterns
            (id, name, actions, occurrences, frequency, average_duration,
             automation_feasibility, created_at, last_detected, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['name'], data['actions'], data['occurrences'],
            data['frequency'], data['average_duration'],
            data['automation_feasibility'], data['created_at'],
            data['last_detected'], data['metadata']
        ))
        await self._db.commit()
        
        self.logger.info(f"Pattern saved: {pattern.name}")
    
    async def get_all_patterns(self) -> List[Pattern]:
        """Get all detected patterns."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute(
            "SELECT * FROM patterns ORDER BY frequency DESC, last_detected DESC"
        )
        rows = await cursor.fetchall()
        
        return [Pattern.from_dict(dict(row)) for row in rows]
    
    async def get_patterns_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Pattern]:
        """Get patterns detected within time range."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM patterns
            WHERE first_detected >= ? AND first_detected <= ?
            ORDER BY frequency DESC, last_detected DESC
        """, (start_time.isoformat(), end_time.isoformat()))
        rows = await cursor.fetchall()
        
        return [Pattern.from_dict(dict(row)) for row in rows]
    
    async def update_pattern_confidence(self, pattern_id: str, confidence: float) -> None:
        """
        Update confidence score for a pattern.
        
        Stores confidence in pattern metadata for tracking workflow reliability.
        
        Args:
            pattern_id: Pattern/workflow identifier
            confidence: Confidence score (0.0 to 1.0)
        """
        await self._ensure_initialized()
        
        try:
            # Get current pattern metadata
            cursor = await self._db.execute(
                "SELECT metadata FROM patterns WHERE id = ?",
                (pattern_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                self.logger.warning(f"Pattern not found: {pattern_id}")
                return
            
            # Parse existing metadata
            import json
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid metadata for pattern {pattern_id}")
            
            # Update confidence in metadata
            metadata['confidence'] = confidence
            metadata['confidence_updated_at'] = datetime.now().isoformat()
            
            # Save updated metadata
            await self._db.execute(
                "UPDATE patterns SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), pattern_id)
            )
            await self._db.commit()
            
            self.logger.info(f"Updated confidence for pattern {pattern_id}: {confidence:.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to update pattern confidence: {e}")
    
    # Transcription operations
    async def save_transcription(self, transcription: Transcription) -> None:
        """Save transcription."""
        await self._ensure_initialized()
        
        data = transcription.to_dict()
        await self._db.execute("""
            INSERT OR REPLACE INTO transcriptions
            (id, text, timestamp, confidence, duration, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['text'], data['timestamp'],
            data['confidence'], data['duration'], data['language']
        ))
        await self._db.commit()
    
    async def get_transcriptions_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Transcription]:
        """Get transcriptions within time range."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM transcriptions
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (start_time.isoformat(), end_time.isoformat()))
        rows = await cursor.fetchall()
        
        return [Transcription.from_dict(dict(row)) for row in rows]
    
    async def get_transcriptions_by_session(self, session_id: str) -> List[Transcription]:
        """Get transcriptions for a specific session."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM transcriptions
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))
        rows = await cursor.fetchall()
        
        return [Transcription.from_dict(dict(row)) for row in rows]
    
    # Workflow suggestion operations
    async def save_workflow_suggestion(self, suggestion: WorkflowSuggestion) -> None:
        """Save workflow suggestion."""
        await self._ensure_initialized()
        
        data = suggestion.to_dict()
        await self._db.execute("""
            INSERT OR REPLACE INTO workflow_suggestions
            (id, pattern_id, title, description, steps, estimated_time_saved,
             complexity, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['id'], data['pattern_id'], data['title'], data['description'],
            data['steps'], data['estimated_time_saved'], data['complexity'],
            data['confidence'], data['created_at'], data['metadata']
        ))
        await self._db.commit()
        
        self.logger.info(f"Workflow suggestion saved: {suggestion.title}")
    
    async def get_all_suggestions(self) -> List[WorkflowSuggestion]:
        """Get all workflow suggestions."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute(
            "SELECT * FROM workflow_suggestions ORDER BY confidence DESC, created_at DESC"
        )
        rows = await cursor.fetchall()
        
        return [WorkflowSuggestion.from_dict(dict(row)) for row in rows]
    
    async def get_workflow_suggestions_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[WorkflowSuggestion]:
        """Get workflow suggestions created within time range."""
        await self._ensure_initialized()
        
        cursor = await self._db.execute("""
            SELECT * FROM workflow_suggestions
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY confidence DESC, created_at DESC
        """, (start_time.isoformat(), end_time.isoformat()))
        rows = await cursor.fetchall()
        
        return [WorkflowSuggestion.from_dict(dict(row)) for row in rows]
    
    async def cleanup_old_data(self, cutoff_date: datetime) -> int:
        """Clean up old database records before cutoff date."""
        await self._ensure_initialized()
        
        records_cleaned = 0
        
        # Clean up old transcriptions
        cursor = await self._db.execute(
            "DELETE FROM transcriptions WHERE timestamp < ?",
            (cutoff_date.isoformat(),)
        )
        records_cleaned += cursor.rowcount
        
        # Clean up old actions (but keep recent ones for pattern analysis)
        # Only clean actions older than cutoff date and not part of recent patterns
        cursor = await self._db.execute(
            "DELETE FROM actions WHERE timestamp < ?",
            (cutoff_date.isoformat(),)
        )
        records_cleaned += cursor.rowcount
        
        # Clean up old patterns that haven't been detected recently
        cursor = await self._db.execute(
            "DELETE FROM patterns WHERE last_detected < ?",
            (cutoff_date.isoformat(),)
        )
        records_cleaned += cursor.rowcount
        
        await self._db.commit()
        
        self.logger.info(f"Cleaned up {records_cleaned} old database records")
        return records_cleaned
    
    # Storage management
    def get_storage_stats(self) -> StorageStats:
        """Get current storage statistics."""
        paths = self.config.get_data_paths()
        
        # Calculate sizes
        video_size = self._get_directory_size(paths['sessions'], pattern='**/*.mp4')
        screenshot_size = self._get_directory_size(paths['sessions'], pattern='**/*.png')
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        total_size = video_size + screenshot_size + db_size
        
        # Get oldest data date
        oldest_date = self._get_oldest_session_date()
        
        # Get session count
        session_count = self._get_session_count_sync()
        
        return StorageStats(
            total_used_gb=total_size / (1024**3),
            video_size_gb=video_size / (1024**3),
            screenshot_size_gb=screenshot_size / (1024**3),
            database_size_gb=db_size / (1024**3),
            oldest_data_date=oldest_date,
            session_count=session_count,
        )
    
    async def delete_old_data(self, before_date: datetime) -> None:
        """Delete data older than specified date."""
        await self._ensure_initialized()
        
        self.logger.info(f"Deleting data before {before_date.isoformat()}")
        
        # Get sessions to delete
        cursor = await self._db.execute(
            "SELECT id FROM sessions WHERE start_time < ?",
            (before_date.isoformat(),)
        )
        sessions = await cursor.fetchall()
        
        # Delete session files
        for session_row in sessions:
            session_id = session_row['id']
            await self._delete_session_files(session_id)
        
        # Delete from database (cascades to actions)
        await self._db.execute(
            "DELETE FROM sessions WHERE start_time < ?",
            (before_date.isoformat(),)
        )
        await self._db.execute(
            "DELETE FROM transcriptions WHERE timestamp < ?",
            (before_date.isoformat(),)
        )
        await self._db.commit()
        
        self.logger.info(f"Deleted {len(sessions)} sessions")
    
    async def delete_session(self, session_id: str) -> None:
        """Delete specific session and its data."""
        await self._ensure_initialized()
        
        self.logger.info(f"Deleting session: {session_id}")
        
        # Delete files
        await self._delete_session_files(session_id)
        
        # Delete from database
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()
    
    async def _delete_session_files(self, session_id: str) -> None:
        """Delete all files for a session."""
        paths = self.config.get_data_paths()
        session_dirs = list(paths['sessions'].glob(f"**/session-{session_id}*"))
        
        for session_dir in session_dirs:
            if session_dir.is_dir():
                shutil.rmtree(session_dir, ignore_errors=True)
    
    async def export_workflows(self, format: str = 'json') -> str:
        """Export workflows in specified format."""
        await self._ensure_initialized()
        
        patterns = await self.get_all_patterns()
        suggestions = await self.get_all_suggestions()
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'patterns': [p.to_dict() for p in patterns],
            'suggestions': [s.to_dict() for s in suggestions],
        }
        
        if format == 'json':
            return json.dumps(export_data, indent=2)
        elif format == 'yaml':
            import yaml
            return yaml.dump(export_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def set_storage_limit(self, limit_gb: int) -> None:
        """Set maximum storage limit."""
        self.config.storage.max_storage_gb = limit_gb
        from src.config import set_config
        set_config(self.config)
        
        self.logger.info(f"Storage limit set to {limit_gb}GB")
    
    # Helper methods
    async def _ensure_initialized(self) -> None:
        """Ensure storage manager is initialized."""
        if not self._initialized:
            await self.initialize()
    
    def _get_directory_size(self, path: Path, pattern: str = '**/*') -> int:
        """Get total size of files in directory matching pattern."""
        if not path.exists():
            return 0
        
        total_size = 0
        for file_path in path.glob(pattern):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def _get_oldest_session_date(self) -> datetime:
        """Get date of oldest session."""
        # This is a sync operation for simplicity
        import sqlite3
        
        if not self.db_path.exists():
            return datetime.now()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT MIN(start_time) as oldest FROM sessions"
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return datetime.now()
    
    def _get_session_count_sync(self) -> int:
        """Get total session count (sync)."""
        import sqlite3
        
        if not self.db_path.exists():
            return 0
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    
    def get_storage_usage(self) -> dict:
        """Get storage usage as a dictionary for UI display."""
        try:
            stats = self.get_storage_stats()
            return {
                'total_size_gb': stats.total_used_gb,
                'video_size_gb': stats.video_size_gb,
                'screenshot_size_gb': stats.screenshot_size_gb,
                'database_size_gb': stats.database_size_gb,
                'session_count': stats.session_count,
                'oldest_data_date': stats.oldest_data_date.isoformat() if stats.oldest_data_date else None
            }
        except Exception as e:
            self.logger.error(f"Error getting storage usage: {e}")
            return {
                'total_size_gb': 0,
                'video_size_gb': 0,
                'screenshot_size_gb': 0,
                'database_size_gb': 0,
                'session_count': 0,
                'oldest_data_date': None
            }

    def get_recent_sessions_sync(self, limit: int = 50) -> List[Dict]:
        """
        Get recent sessions synchronously for UI display.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries with formatted data
        """
        import sqlite3
        
        try:
            if not self.db_path.exists():
                return []
            
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, start_time, end_time, capture_count, 
                       detected_actions, storage_size, status
                FROM sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            sessions = []
            for row in rows:
                start_time = datetime.fromisoformat(row['start_time'])
                end_time = datetime.fromisoformat(row['end_time']) if row['end_time'] else datetime.now()
                duration = int((end_time - start_time).total_seconds())
                
                sessions.append({
                    'id': row['id'],
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'actions_count': row['detected_actions'],
                    'size_mb': row['storage_size'] / (1024 * 1024) if row['storage_size'] else 0,
                    'status': row['status']
                })
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def delete_session_sync(self, session_id: str) -> bool:
        """
        Delete a session synchronously for UI operations.
        
        Args:
            session_id: ID of session to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Run async deletion in event loop
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _delete():
                await self.initialize()
                await self.delete_session(session_id)
                await self.close()
            
            loop.run_until_complete(_delete())
            loop.close()
            
            self.logger.info(f"Session deleted synchronously: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting session synchronously: {e}")
            return False
    
    def delete_all_data_sync(self) -> Dict[str, Any]:
        """
        Delete all data synchronously for UI operations.
        
        Returns:
            Dictionary with deletion statistics
        """
        import sqlite3
        import shutil
        
        try:
            sessions_deleted = 0
            files_removed = 0
            space_freed = 0
            
            # Get session count before deletion
            if self.db_path.exists():
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.execute("SELECT COUNT(*) FROM sessions")
                sessions_deleted = cursor.fetchone()[0]
                conn.close()
            
            # Delete all session files
            paths = self.config.get_data_paths()
            sessions_path = paths['sessions']
            
            if sessions_path.exists():
                # Calculate space before deletion
                for file_path in sessions_path.rglob('*'):
                    if file_path.is_file():
                        space_freed += file_path.stat().st_size
                        files_removed += 1
                
                # Delete sessions directory
                shutil.rmtree(sessions_path, ignore_errors=True)
                sessions_path.mkdir(parents=True, exist_ok=True)
            
            # Delete database
            if self.db_path.exists():
                space_freed += self.db_path.stat().st_size
                self.db_path.unlink()
            
            # Recreate database
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _reinit():
                await self.initialize()
                await self.close()
            
            loop.run_until_complete(_reinit())
            loop.close()
            
            result = {
                'sessions_deleted': sessions_deleted,
                'files_removed': files_removed,
                'space_freed_mb': space_freed / (1024 * 1024)
            }
            
            self.logger.warning(f"All data deleted: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error deleting all data: {e}")
            return {
                'sessions_deleted': 0,
                'files_removed': 0,
                'space_freed_mb': 0,
                'error': str(e)
            }
