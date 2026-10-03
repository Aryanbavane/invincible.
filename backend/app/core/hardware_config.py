import os
from dataclasses import dataclass
from typing import Mapping


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None


def _optional_float(value: str | None) -> float | None:
    return float(value) if value else None


@dataclass(frozen=True)
class HardwareConfig:
    emg_adc_pin: int | None
    ir_sensor_pin: int | None
    device_id: str
    emg_sample_rate: int | None
    emg_threshold: float | None
    ir_threshold: float | None
    supported_sensor_mode: str


def load_hardware_config(
    environ: Mapping[str, str] | None = None,
) -> HardwareConfig:
    values = os.environ if environ is None else environ
    return HardwareConfig(
        emg_adc_pin=_optional_int(values.get("EMG_ADC_PIN")),
        ir_sensor_pin=_optional_int(values.get("IR_SENSOR_PIN")),
        device_id=values.get("DEVICE_ID", "BLINK001"),
        emg_sample_rate=_optional_int(values.get("EMG_SAMPLE_RATE")),
        emg_threshold=_optional_float(values.get("EMG_THRESHOLD")),
        ir_threshold=_optional_float(values.get("IR_THRESHOLD")),
        supported_sensor_mode=values.get("SUPPORTED_SENSOR_MODE", "dual"),
    )


# TODO — CONFIGURE DURING HARDWARE INTEGRATION; no board-specific values are assumed.
hardware_config = load_hardware_config()