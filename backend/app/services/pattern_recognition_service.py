from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from backend.app.services.blink_detection_service import BlinkType


def _as_utc(value: datetime | str | None, clock: Callable[[], datetime]) -> datetime:
    if value is None:
        value = clock()
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class _ConfirmedBlink:
    blink_type: BlinkType
    timestamp: datetime
    ir_confidence: float
    emg_confidence: float
    fusion_confidence: float
    source: str


@dataclass(frozen=True)
class PatternResult:
    sequence: tuple[str, ...]
    name: str
    mapping_pattern: str
    timestamp: datetime
    ir_confidence: float
    emg_confidence: float
    fusion_confidence: float
    source: str


class PatternRecognitionService:
    def __init__(
        self,
        pattern_gap_ms: int = 1500,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if pattern_gap_ms < 0:
            raise ValueError("Pattern gap cannot be negative")
        self.pattern_gap_ms = pattern_gap_ms
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._blinks: list[_ConfirmedBlink] = []

    def add_blink(
        self,
        blink_type: BlinkType,
        timestamp: datetime | str | None = None,
        ir_confidence: float = 100,
        emg_confidence: float = 100,
        fusion_confidence: float = 100,
        source: str = "live",
    ) -> PatternResult | None:
        current_time = _as_utc(timestamp, self._clock)
        finalized = self.flush(current_time)
        self._blinks.append(
            _ConfirmedBlink(
                blink_type=blink_type,
                timestamp=current_time,
                ir_confidence=ir_confidence,
                emg_confidence=emg_confidence,
                fusion_confidence=fusion_confidence,
                source=source,
            )
        )
        return finalized

    def flush(self, timestamp: datetime | str | None = None) -> PatternResult | None:
        if not self._blinks:
            return None
        current_time = _as_utc(timestamp, self._clock)
        last_time = self._blinks[-1].timestamp
        gap_ms = (current_time - last_time).total_seconds() * 1000
        if gap_ms < self.pattern_gap_ms:
            return None

        blinks, self._blinks = self._blinks, []
        sequence = tuple(blink.blink_type for blink in blinks)
        if all(blink_type == "SHORT" for blink_type in sequence):
            mapping_pattern = f"{len(sequence)} short"
        elif len(sequence) == 2 and all(
            blink_type == "LONG" for blink_type in sequence
        ):
            mapping_pattern = "long+long"
        elif all(blink_type == "LONG" for blink_type in sequence):
            mapping_pattern = f"{len(sequence)} long"
        else:
            mapping_pattern = "+".join(blink_type.lower() for blink_type in sequence)

        count = len(blinks)
        return PatternResult(
            sequence=sequence,
            name="_".join(sequence),
            mapping_pattern=mapping_pattern,
            timestamp=last_time,
            ir_confidence=sum(blink.ir_confidence for blink in blinks) / count,
            emg_confidence=sum(blink.emg_confidence for blink in blinks) / count,
            fusion_confidence=sum(blink.fusion_confidence for blink in blinks) / count,
            source=blinks[0].source,
        )