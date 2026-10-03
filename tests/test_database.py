import sqlite3

from backend.app.core.database import TABLE_NAMES, initialize_database


def test_database_creates_exactly_the_required_tables(tmp_path):
    database_path = tmp_path / "nested" / "blinkbridge.sqlite3"

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert tables == set(TABLE_NAMES)


def test_database_migrates_existing_tables_without_adding_tables(tmp_path):
    database_path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE communication_events (
                event_id INTEGER PRIMARY KEY, device_id TEXT, pattern TEXT,
                command TEXT, message TEXT, ir_confidence REAL, emg_confidence REAL,
                fusion_confidence REAL, audio_id TEXT, timestamp TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE emergency_events (
                emergency_id INTEGER PRIMARY KEY, device_id TEXT, message TEXT,
                acknowledged INTEGER DEFAULT 0, created_at TEXT,
                acknowledged_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE device_heartbeats (
                heartbeat_id INTEGER PRIMARY KEY, device_id TEXT,
                status TEXT, last_seen TEXT
            )
            """
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        columns = {
            table: {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            for table in (
                "communication_events",
                "emergency_events",
                "device_heartbeats",
            )
        }

    assert table_names == set(TABLE_NAMES)
    assert "source" in columns["communication_events"]
    assert "source" in columns["emergency_events"]
    assert "battery" in columns["device_heartbeats"]