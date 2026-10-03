from typing import Literal

BlinkType = Literal["SHORT", "LONG"]


class BlinkDetectionService:
    def __init__(self, short_blink_max_ms: int = 800, long_blink_min_ms: int = 800):
        if short_blink_max_ms < 0 or long_blink_min_ms < 0:
            raise ValueError("Blink duration boundaries cannot be negative")
        self.short_blink_max_ms = short_blink_max_ms
        self.long_blink_min_ms = long_blink_min_ms

    def classify(
        self, duration_ms: int, intent_confirmed: bool = True
    ) -> BlinkType | None:
        if not intent_confirmed or duration_ms < 0:
            return None
        if duration_ms < self.short_blink_max_ms:
            return "SHORT"
        if duration_ms >= self.long_blink_min_ms:
            return "LONG"
        return None