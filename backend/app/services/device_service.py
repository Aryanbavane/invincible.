import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.database import initialize_database


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DeviceService:
    def __init__(self, database_path: str | Path, offline_timeout_seconds: float = 15):
        self.database_path = Path(database_path)
        self.offline_timeout_seconds = offline_timeout_seconds
        initialize_database(self.database_path)

    def heartbeat(
        self, device_id: str, timestamp: datetime | str, battery: float
    ) -> dict[str, Any]:
        last_seen = _as_utc(timestamp).isoformat()
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT OR IGNORE INTO devices (device_id) VALUES (?)", (device_id,)
            )
            connection.execute(
                "UPDATE devices SET status = 'ONLINE' WHERE device_id = ?",
                (device_id,),
            )
            connection.execute(
                """
                INSERT INTO device_heartbeats (device_id, status, last_seen, battery)
                VALUES (?, 'ONLINE', ?, ?)
                """,
                (device_id, last_seen, battery),
            )
        return {
            "device_id": device_id,
            "status": "ONLINE",
            "last_seen": last_seen,
            "battery": battery,
        }

    def observe_event(self, device_id: str, timestamp: datetime | str) -> None:
        last_seen = _as_utc(timestamp).isoformat()
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT OR IGNORE INTO devices (device_id) VALUES (?)", (device_id,)
            )
            connection.execute(
                "UPDATE devices SET status = 'ONLINE' WHERE device_id = ?",
                (device_id,),
            )
            connection.execute(
                """
                INSERT INTO device_heartbeats (device_id, status, last_seen, battery)
                VALUES (?, 'ONLINE', ?, NULL)
                """,
                (device_id, last_seen),
            )

    def status(
        self,
        device_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        current_time = _as_utc(now or datetime.now(timezone.utc))
        query = """
            SELECT d.device_id,
                (SELECT h.last_seen FROM device_heartbeats h
                 WHERE h.device_id = d.device_id
                 ORDER BY h.heartbeat_id DESC LIMIT 1) AS last_seen,
                (SELECT h.battery FROM device_heartbeats h
                 WHERE h.device_id = d.device_id
                 ORDER BY h.heartbeat_id DESC LIMIT 1) AS battery
            FROM devices d
        """
        parameters: tuple[Any, ...] = ()
        if device_id is not None:
            query += " WHERE d.device_id = ?"
            parameters = (device_id,)
        query += " ORDER BY d.device_id"
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            records = [dict(row) for row in connection.execute(query, parameters)]

        if device_id is not None and not records:
            records = [{"device_id": device_id, "last_seen": None, "battery": None}]

        results: list[dict[str, Any]] = []
        for record in records:
            seen = (
                _as_utc(record["last_seen"])
                if record["last_seen"] is not None
                else None
            )
            age_seconds = (
                (current_time - seen).total_seconds() if seen is not None else None
            )
            status = (
                "ONLINE"
                if age_seconds is not None
                and age_seconds <= self.offline_timeout_seconds
                else "OFFLINE"
            )
            results.append(
                {
                    "device_id": record["device_id"],
                    "status": status,
                    "last_seen": record["last_seen"],
                    "battery": record["battery"],
                    "age_seconds": age_seconds,
                }
            )
            with closing(sqlite3.connect(self.database_path)) as connection, connection:
                connection.execute(
                    "UPDATE devices SET status = ? WHERE device_id = ?",
                    (status, record["device_id"]),
                )

        if device_id is not None:
            return results[0]
        return results