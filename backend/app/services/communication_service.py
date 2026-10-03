import os
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.app.core.database import initialize_database
from backend.app.schemas.sensors import CommandEvent


class CommunicationService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        minimum_confidence: float = 85,
    ) -> None:
        self.database_path = Path(
            database_path
            or os.getenv("BLINKBRIDGE_DATABASE_PATH", "data/blinkbridge.sqlite3")
        )
        self.minimum_confidence = minimum_confidence
        initialize_database(self.database_path)

    @staticmethod
    def ensure_device(connection: sqlite3.Connection, device_id: str) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO devices (device_id) VALUES (?)", (device_id,)
        )

    def save(self, event: CommandEvent) -> int | None:
        if event.fusion_confidence < self.minimum_confidence:
            return None
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.ensure_device(connection, event.device_id)
            cursor = connection.execute(
                """
                INSERT INTO communication_events (
                    device_id, pattern, command, message, ir_confidence,
                    emg_confidence, fusion_confidence, audio_id, timestamp, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.device_id,
                    event.pattern,
                    event.command,
                    event.message,
                    event.ir_confidence,
                    event.emg_confidence,
                    event.fusion_confidence,
                    event.audio_id,
                    event.timestamp,
                    event.source,
                ),
            )
            return int(cursor.lastrowid)

    def history(
        self, device_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("History limit must be positive")
        query = "SELECT * FROM communication_events"
        parameters: list[Any] = []
        if device_id is not None:
            query += " WHERE device_id = ?"
            parameters.append(device_id)
        query += " ORDER BY timestamp DESC, event_id DESC LIMIT ?"
        parameters.append(limit)
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def today_stats(
        self, today: date | None = None, device_id: str | None = None
    ) -> dict[str, Any]:
        selected_date = today or datetime.now().date()
        query = (
            "SELECT command, COUNT(*) AS count FROM communication_events "
            "WHERE date(timestamp) = ?"
        )
        parameters: list[Any] = [selected_date.isoformat()]
        if device_id is not None:
            query += " AND device_id = ?"
            parameters.append(device_id)
        query += " GROUP BY command ORDER BY command"
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            rows = connection.execute(query, parameters).fetchall()
        by_command = {command: count for command, count in rows}
        return {
            "date": selected_date.isoformat(),
            "total": sum(by_command.values()),
            "by_command": by_command,
        }