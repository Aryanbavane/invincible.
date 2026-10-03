import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.database import initialize_database


class CalibrationService:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        initialize_database(self.database_path)

    def get(self, device_id: str) -> dict[str, Any]:
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT calibration_id, device_id, baseline AS emg_baseline,
                    threshold AS emg_threshold, calibrated_at
                FROM calibrations WHERE device_id = ?
                ORDER BY calibration_id DESC LIMIT 1
                """,
                (device_id,),
            ).fetchone()
        return dict(row) if row else {"device_id": device_id, "calibrated": False}

    def save(
        self,
        device_id: str,
        emg_baseline: float,
        emg_threshold: float,
        calibrated_at: datetime | None = None,
    ) -> dict[str, Any]:
        timestamp = (calibrated_at or datetime.now(timezone.utc)).isoformat()
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "INSERT OR IGNORE INTO devices (device_id) VALUES (?)", (device_id,)
            )
            cursor = connection.execute(
                """
                INSERT INTO calibrations (device_id, baseline, threshold, calibrated_at)
                VALUES (?, ?, ?, ?)
                """,
                (device_id, emg_baseline, emg_threshold, timestamp),
            )
            calibration_id = int(cursor.lastrowid)
        return {
            "calibration_id": calibration_id,
            "device_id": device_id,
            "emg_baseline": emg_baseline,
            "emg_threshold": emg_threshold,
            "calibrated_at": timestamp,
            "calibrated": True,
        }