import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas.sensors import CommandEvent
from backend.app.services.pattern_recognition_service import PatternResult


class CommandService:
    def __init__(
        self,
        minimum_confidence: float = 85,
        mapping_path: str | Path | None = None,
    ) -> None:
        if not 0 <= minimum_confidence <= 100:
            raise ValueError("Minimum confidence must be between 0 and 100")
        self.minimum_confidence = minimum_confidence
        path = Path(mapping_path) if mapping_path else (
            Path(__file__).parents[1] / "core" / "command_mapping.json"
        )
        with path.open(encoding="utf-8") as mapping_file:
            mapping = json.load(mapping_file)
        self._commands = {item["pattern"]: item for item in mapping["commands"]}

    def resolve(
        self, pattern: PatternResult, device_id: str, language: str = "en"
    ) -> CommandEvent | None:
        return self.create_event(
            pattern.mapping_pattern,
            device_id,
            pattern.ir_confidence,
            pattern.emg_confidence,
            pattern.fusion_confidence,
            pattern.timestamp,
            language,
            pattern.name,
            pattern.source,
        )

    def create_event(
        self,
        mapping_pattern: str,
        device_id: str,
        ir_confidence: float,
        emg_confidence: float,
        fusion_confidence: float,
        timestamp: datetime | str,
        language: str = "en",
        pattern_name: str | None = None,
        source: str = "live",
    ) -> CommandEvent | None:
        if fusion_confidence < self.minimum_confidence:
            return None
        command = self._commands.get(mapping_pattern)
        if command is None:
            return None
        message_fields = {"en": "message", "hi": "hindi", "mr": "marathi"}
        if language not in message_fields:
            raise ValueError("Language must be one of: en, hi, mr")
        event_time = timestamp
        if isinstance(event_time, datetime):
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            event_time = event_time.isoformat()
        return CommandEvent(
            device_id=device_id,
            pattern=pattern_name or mapping_pattern,
            command=command["command"],
            message=command[message_fields[language]],
            ir_confidence=ir_confidence,
            emg_confidence=emg_confidence,
            fusion_confidence=fusion_confidence,
            audio_id=command["audio_id"],
            timestamp=event_time,
            source=source,
        )