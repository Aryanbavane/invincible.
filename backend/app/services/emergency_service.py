import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from backend.app.schemas.sensors import CommandEvent
from backend.app.services.command_service import CommandService
from backend.app.services.communication_service import CommunicationService

logger = logging.getLogger(__name__)


def _as_utc(value: datetime | str | None, clock: Callable[[], datetime]) -> datetime:
    if value is None:
        value = clock()
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class EmergencyAction:
    state: str
    device_id: str
    command_event: CommandEvent | None = None
    emergency_id: int | None = None
    note: str | None = None


@dataclass(frozen=True)
class _PendingEmergency:
    device_id: str
    deadline: datetime
    ir_confidence: float
    emg_confidence: float
    fusion_confidence: float
    language: str
    source: str


class EmergencyService:
    def __init__(
        self,
        communication_service: CommunicationService,
        command_service: CommandService,
        confirmation_window_seconds: float = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if confirmation_window_seconds < 0:
            raise ValueError("Emergency confirmation window cannot be negative")
        self.communication_service = communication_service
        self.command_service = command_service
        self.confirmation_window = timedelta(seconds=confirmation_window_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._pending: dict[str, _PendingEmergency] = {}

    def raise_emergency(
        self,
        device_id: str,
        timestamp: datetime | str | None = None,
        language: str = "en",
        source: str = "live",
    ) -> EmergencyAction:
        current_time = _as_utc(timestamp, self._clock)
        command_event = self.command_service.create_event(
            "long+long",
            device_id,
            100,
            100,
            100,
            current_time,
            language,
            "MANUAL_EMERGENCY",
            source,
        )
        message = command_event.message if command_event is not None else "Emergency"
        emergency_id = self._create_record(device_id, message, current_time, source)
        return EmergencyAction(
            state="EMERGENCY_CONFIRMED",
            device_id=device_id,
            command_event=command_event,
            emergency_id=emergency_id,
        )

    def on_long_blink(
        self,
        device_id: str,
        ir_confidence: float,
        emg_confidence: float,
        fusion_confidence: float,
        timestamp: datetime | str | None = None,
        language: str = "en",
        source: str = "live",
    ) -> list[EmergencyAction]:
        current_time = _as_utc(timestamp, self._clock)
        actions = self.poll(current_time)
        if fusion_confidence < self.command_service.minimum_confidence:
            actions.append(
                EmergencyAction(
                    state="REJECTED",
                    device_id=device_id,
                    note="A confirmed dual-sensor blink is required.",
                )
            )
            return actions
        pending = self._pending.pop(device_id, None)
        if pending is not None and current_time <= pending.deadline:
            combined_ir = (pending.ir_confidence + ir_confidence) / 2
            combined_emg = (pending.emg_confidence + emg_confidence) / 2
            combined_fusion = (pending.fusion_confidence + fusion_confidence) / 2
            command_event = self.command_service.create_event(
                "long+long",
                device_id,
                combined_ir,
                combined_emg,
                combined_fusion,
                current_time,
                language,
                "LONG_LONG",
                source,
            )
            emergency_id = self._create_record(
                device_id,
                command_event.message if command_event is not None else "Emergency",
                current_time,
                source,
            )
            actions.append(
                EmergencyAction(
                    state="EMERGENCY_CONFIRMED",
                    device_id=device_id,
                    command_event=command_event,
                    emergency_id=emergency_id,
                )
            )
            return actions

        self._pending[device_id] = _PendingEmergency(
            device_id=device_id,
            deadline=current_time + self.confirmation_window,
            ir_confidence=ir_confidence,
            emg_confidence=emg_confidence,
            fusion_confidence=fusion_confidence,
            language=language,
            source=source,
        )
        actions.append(
            EmergencyAction(
                state="POSSIBLE_EMERGENCY",
                device_id=device_id,
                note="A second confirmed long blink is required.",
            )
        )
        return actions

    def poll(self, timestamp: datetime | str | None = None) -> list[EmergencyAction]:
        current_time = _as_utc(timestamp, self._clock)
        actions: list[EmergencyAction] = []
        expired = [
            pending
            for pending in self._pending.values()
            if current_time > pending.deadline
        ]
        for pending in expired:
            self._pending.pop(pending.device_id, None)
            command_event = self.command_service.create_event(
                "1 long",
                pending.device_id,
                pending.ir_confidence,
                pending.emg_confidence,
                pending.fusion_confidence,
                pending.deadline,
                pending.language,
                "LONG",
                pending.source,
            )
            if command_event is not None:
                self.communication_service.save(command_event)
            logger.info("emergency not confirmed for device %s", pending.device_id)
            actions.append(
                EmergencyAction(
                    state="HELP_EMITTED",
                    device_id=pending.device_id,
                    command_event=command_event,
                    note="emergency not confirmed",
                )
            )
        return actions

    def _create_record(
        self, device_id: str, message: str, timestamp: datetime, source: str
    ) -> int:
        with closing(
            sqlite3.connect(self.communication_service.database_path)
        ) as connection, connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.communication_service.ensure_device(connection, device_id)
            cursor = connection.execute(
                """
                INSERT INTO emergency_events (device_id, message, created_at, source)
                VALUES (?, ?, ?, ?)
                """,
                (device_id, message, timestamp.isoformat(), source),
            )
            return int(cursor.lastrowid)

    def acknowledge(
        self, emergency_id: int, timestamp: datetime | str | None = None
    ) -> dict[str, Any] | None:
        acknowledged_at = _as_utc(timestamp, self._clock).isoformat()
        with closing(
            sqlite3.connect(self.communication_service.database_path)
        ) as connection, connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                UPDATE emergency_events
                SET acknowledged = 1, acknowledged_at = ?
                WHERE emergency_id = ?
                """,
                (acknowledged_at, emergency_id),
            )
            row = connection.execute(
                "SELECT * FROM emergency_events WHERE emergency_id = ?",
                (emergency_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def history(self, device_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM emergency_events"
        parameters: tuple[Any, ...] = ()
        if device_id is not None:
            query += " WHERE device_id = ?"
            parameters = (device_id,)
        query += " ORDER BY created_at DESC, emergency_id DESC"
        with closing(
            sqlite3.connect(self.communication_service.database_path)
        ) as connection, connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]