import os
from dataclasses import dataclass
from typing import Mapping


def _optional_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def _int_value(values: Mapping[str, str], name: str, default: int) -> int:
    return int(values.get(name, default))


def _float_value(values: Mapping[str, str], name: str, default: float) -> float:
    return float(values.get(name, default))


@dataclass(frozen=True)
class ProcessingConfig:
    emg_baseline: float | None = None
    emg_threshold: float | None = None
    moving_average_window: int = 5
    emg_rms_window: int = 5
    ir_threshold: float | None = None
    ir_crossing_margin: float | None = None
    ir_confidence_weight: float = 0.5
    emg_confidence_weight: float = 0.5
    low_confidence_max: float = 69
    possible_intent_min: float = 70
    intent_confirmed_min: float = 85
    short_blink_max_ms: int = 800
    long_blink_min_ms: int = 800
    pattern_gap_ms: int = 1500
    emergency_confirmation_window_seconds: float = 3
    device_offline_timeout_seconds: float = 15

    def __post_init__(self) -> None:
        if self.moving_average_window < 1 or self.emg_rms_window < 1:
            raise ValueError("EMG filter windows must be positive")
        if self.ir_confidence_weight < 0 or self.emg_confidence_weight < 0:
            raise ValueError("Fusion weights cannot be negative")
        if self.ir_confidence_weight + self.emg_confidence_weight == 0:
            raise ValueError("At least one fusion weight must be positive")
        if not 0 <= self.low_confidence_max < self.possible_intent_min:
            raise ValueError("Low and possible confidence levels must be ordered")
        if not self.possible_intent_min < self.intent_confirmed_min <= 100:
            raise ValueError("Intent confirmation confidence must be above possible")
        if self.short_blink_max_ms < 0 or self.long_blink_min_ms < 0:
            raise ValueError("Blink duration boundaries cannot be negative")
        if self.pattern_gap_ms < 0 or self.emergency_confirmation_window_seconds < 0:
            raise ValueError("Pattern and emergency windows cannot be negative")
        if self.device_offline_timeout_seconds <= 0:
            raise ValueError("Device offline timeout must be positive")


def load_processing_config(
    environ: Mapping[str, str] | None = None,
) -> ProcessingConfig:
    values = os.environ if environ is None else environ
    return ProcessingConfig(
        emg_baseline=_optional_float(values.get("EMG_BASELINE")),
        emg_threshold=_optional_float(values.get("EMG_THRESHOLD")),
        moving_average_window=_int_value(values, "EMG_MOVING_AVERAGE_WINDOW", 5),
        emg_rms_window=_int_value(values, "EMG_RMS_WINDOW", 5),
        ir_threshold=_optional_float(values.get("IR_THRESHOLD")),
        ir_crossing_margin=_optional_float(values.get("IR_CROSSING_MARGIN")),
        ir_confidence_weight=_float_value(values, "IR_CONFIDENCE_WEIGHT", 0.5),
        emg_confidence_weight=_float_value(values, "EMG_CONFIDENCE_WEIGHT", 0.5),
        low_confidence_max=_float_value(values, "LOW_CONFIDENCE_MAX", 69),
        possible_intent_min=_float_value(values, "POSSIBLE_INTENT_MIN", 70),
        intent_confirmed_min=_float_value(values, "INTENT_CONFIRMED_MIN", 85),
        short_blink_max_ms=_int_value(values, "SHORT_BLINK_MAX_MS", 800),
        long_blink_min_ms=_int_value(values, "LONG_BLINK_MIN_MS", 800),
        pattern_gap_ms=_int_value(values, "PATTERN_GAP_MS", 1500),
        emergency_confirmation_window_seconds=_float_value(
            values, "EMERGENCY_CONFIRMATION_WINDOW_SECONDS", 3
        ),
        device_offline_timeout_seconds=_float_value(
            values, "DEVICE_OFFLINE_TIMEOUT_SECONDS", 15
        ),
    )


processing_config = load_processing_config()