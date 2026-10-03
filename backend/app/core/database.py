import sqlite3
from contextlib import closing
from pathlib import Path

TABLE_NAMES = (
    "users",
    "devices",
    "calibrations",
    "communication_events",
    "emergency_events",
    "device_heartbeats",
)

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        display_name TEXT NOT NULL,
        preferred_language TEXT NOT NULL DEFAULT 'en',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id),
        status TEXT NOT NULL DEFAULT 'unknown',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calibrations (
        calibration_id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL REFERENCES devices(device_id),
        baseline REAL NOT NULL,
        threshold REAL NOT NULL,
        calibrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS communication_events (
        event_id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL REFERENCES devices(device_id),
        pattern TEXT NOT NULL,
        command TEXT NOT NULL,
        message TEXT NOT NULL,
        ir_confidence REAL NOT NULL,
        emg_confidence REAL NOT NULL,
        fusion_confidence REAL NOT NULL,
        audio_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'live'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS emergency_events (
        emergency_id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL REFERENCES devices(device_id),
        message TEXT NOT NULL,
        acknowledged INTEGER NOT NULL DEFAULT 0 CHECK (acknowledged IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        acknowledged_at TEXT,
        source TEXT NOT NULL DEFAULT 'live'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS device_heartbeats (
        heartbeat_id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL REFERENCES devices(device_id),
        status TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        battery REAL
    )
    """,
)


def initialize_database(database_path: str | Path) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        migrations = {
            "communication_events": ("source", "TEXT NOT NULL DEFAULT 'live'"),
            "emergency_events": ("source", "TEXT NOT NULL DEFAULT 'live'"),
            "device_heartbeats": ("battery", "REAL"),
        }
        for table, (column, definition) in migrations.items():
            columns = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )