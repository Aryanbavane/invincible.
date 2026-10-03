import random
from datetime import datetime, timedelta, timezone

from backend.app.schemas.sensors import SensorEvent


class DemoService:
    _PATTERNS = {
        "YES": ("SHORT",),
        "NO": ("SHORT", "SHORT"),
        "HELP": ("LONG",),
        "WATER": ("SHORT", "SHORT", "SHORT"),
        "PAIN": ("SHORT", "SHORT", "SHORT", "SHORT"),
        "COME_HERE": ("SHORT", "SHORT", "SHORT", "SHORT", "SHORT"),
        "EMERGENCY": ("LONG", "LONG"),
    }

    def generate(
        self,
        scenario: str,
        device_id: str = "DEMO001",
        timestamp: datetime | None = None,
    ) -> list[SensorEvent]:
        scenario = scenario.upper()
        start = timestamp or datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if scenario not in self._PATTERNS and scenario not in {
            "LOW_CONFIDENCE",
            "SENSOR_NOISE",
            "DEVICE_OFFLINE",
        }:
            raise ValueError(f"Unsupported demo scenario: {scenario}")
        if scenario == "DEVICE_OFFLINE":
            return []

        blink_types = self._PATTERNS.get(scenario, ("SHORT",))
        low_confidence = scenario == "LOW_CONFIDENCE"
        sensor_noise = scenario == "SENSOR_NOISE"
        randomizer = random.Random(sum(map(ord, scenario)))
        events = [
            self._event(
                device_id,
                start,
                "OPEN",
                active=not low_confidence,
                confidence=20 if low_confidence else 100,
                signal_value=101 if sensor_noise else None,
            )
        ]
        current = start
        for blink_type in blink_types:
            current += timedelta(milliseconds=280 + randomizer.randint(-25, 25))
            events.append(
                self._event(
                    device_id,
                    current,
                    "CLOSED",
                    active=not low_confidence,
                    confidence=20 if low_confidence else 100,
                    signal_value=99 if sensor_noise else None,
                )
            )
            duration = (
                1000 + randomizer.randint(-30, 30)
                if blink_type == "LONG"
                else 300 + randomizer.randint(-20, 20)
            )
            current += timedelta(milliseconds=duration)
            events.append(
                self._event(
                    device_id,
                    current,
                    "OPEN",
                    active=not low_confidence,
                    confidence=20 if low_confidence else 100,
                    signal_value=101 if sensor_noise else None,
                    duration_ms=duration if low_confidence else 0,
                )
            )
            current += timedelta(milliseconds=260 + randomizer.randint(-20, 20))
        return events

    @staticmethod
    def _event(
        device_id: str,
        timestamp: datetime,
        ir_state: str,
        active: bool,
        confidence: float,
        signal_value: float | None,
        duration_ms: int = 0,
    ) -> SensorEvent:
        return SensorEvent(
            device_id=device_id,
            timestamp=timestamp,
            ir_state=ir_state,
            ir_duration_ms=duration_ms,
            emg_raw=1 if not active else 10,
            emg_activity=active,
            emg_confidence=confidence,
            ir_signal_raw=signal_value,
            source="demo",
        )