from datetime import datetime

from backend.app.schemas.sensors import IRReading


def _timestamp(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class IRProcessingService:
    def __init__(
        self,
        threshold: float | None = None,
        crossing_margin: float | None = None,
    ) -> None:
        if crossing_margin is not None and crossing_margin <= 0:
            raise ValueError("IR crossing margin must be positive")
        self.threshold = threshold
        self.crossing_margin = crossing_margin
        self._state: str | None = None
        self._closed_at: datetime | None = None
        self._closure_confidence = 0.0

    def _crossing_confidence(self, signal_value: float | None) -> float:
        if (
            signal_value is None
            or self.threshold is None
            or self.crossing_margin is None
        ):
            return 100.0
        margin = abs(signal_value - self.threshold)
        return min(100.0, margin / self.crossing_margin * 100.0)

    def process(
        self,
        state: str,
        timestamp: datetime | str,
        signal_value: float | None = None,
        duration_hint_ms: int = 0,
    ) -> IRReading:
        normalized_state = state.upper()
        if normalized_state not in {"OPEN", "CLOSED"}:
            raise ValueError("IR state must be OPEN or CLOSED")
        current_time = _timestamp(timestamp)
        crossing_confidence = self._crossing_confidence(signal_value)
        duration_ms = 0
        confidence = 0.0

        if self._state == "OPEN" and normalized_state == "CLOSED":
            self._closed_at = current_time
            self._closure_confidence = crossing_confidence
        elif self._state == "CLOSED" and normalized_state == "OPEN":
            if self._closed_at is not None:
                duration_ms = max(
                    0, round((current_time - self._closed_at).total_seconds() * 1000)
                )
                confidence = min(self._closure_confidence, crossing_confidence)
            self._closed_at = None
        elif (
            normalized_state == "OPEN"
            and self._state != "CLOSED"
            and duration_hint_ms > 0
        ):
            duration_ms = duration_hint_ms
            confidence = crossing_confidence

        self._state = normalized_state
        return IRReading(
            state=normalized_state,
            duration_ms=duration_ms,
            confidence=confidence,
        )