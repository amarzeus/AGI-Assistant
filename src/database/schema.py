"""Database schema definitions."""

# SQL schema for SQLite database

SCHEMA_VERSION = 1

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    capture_count INTEGER DEFAULT 0,
    transcription_count INTEGER DEFAULT 0,
    detected_actions INTEGER DEFAULT 0,
    storage_size INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    application TEXT NOT NULL,
    window_title TEXT NOT NULL,
    target_element TEXT,
    input_data TEXT,
    screenshot_path TEXT,
    confidence REAL DEFAULT 0.0,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""

CREATE_PATTERNS_TABLE = """
CREATE TABLE IF NOT EXISTS patterns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    actions TEXT NOT NULL,
    occurrences TEXT NOT NULL,
    frequency INTEGER DEFAULT 0,
    average_duration REAL DEFAULT 0.0,
    automation_feasibility REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    last_detected TEXT NOT NULL,
    metadata TEXT,
    UNIQUE(name)
);
"""

CREATE_TRANSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    duration REAL DEFAULT 0.0,
    language TEXT DEFAULT 'en',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_WORKFLOW_SUGGESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS workflow_suggestions (
    id TEXT PRIMARY KEY,
    pattern_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    steps TEXT NOT NULL,
    estimated_time_saved INTEGER DEFAULT 0,
    complexity TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE
);
"""

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes for performance
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_actions_session_id ON actions(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(type);",
    "CREATE INDEX IF NOT EXISTS idx_transcriptions_timestamp ON transcriptions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_patterns_frequency ON patterns(frequency DESC);",
    "CREATE INDEX IF NOT EXISTS idx_patterns_last_detected ON patterns(last_detected);",
]

# All table creation statements
ALL_TABLES = [
    CREATE_SCHEMA_VERSION_TABLE,
    CREATE_SESSIONS_TABLE,
    CREATE_ACTIONS_TABLE,
    CREATE_PATTERNS_TABLE,
    CREATE_TRANSCRIPTIONS_TABLE,
    CREATE_WORKFLOW_SUGGESTIONS_TABLE,
]


def get_init_schema() -> list:
    """Get all schema initialization statements."""
    return ALL_TABLES + CREATE_INDEXES
