from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    battery: float = Field(ge=0, le=100, allow_inf_nan=False)


class CalibrationRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    emg_baseline: float = Field(allow_inf_nan=False)
    emg_threshold: float = Field(gt=0, allow_inf_nan=False)


class SettingsUpdate(BaseModel):
    device_offline_timeout_seconds: float | None = Field(default=None, gt=0)
    supported_sensor_mode: Literal["dual", "ir_only", "emg_only"] | None = None

    @model_validator(mode="after")
    def require_setting(self):
        if all(
            value is None
            for value in (
                self.device_offline_timeout_seconds,
                self.supported_sensor_mode,
            )
        ):
            raise ValueError("Provide at least one setting to update")
        return self


class EmergencyRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    language: Literal["en", "hi", "mr"] = "en"
    source: Literal["live", "demo"] = "live"


class DemoSimulationRequest(BaseModel):
    scenario: Literal[
        "YES",
        "NO",
        "HELP",
        "WATER",
        "PAIN",
        "COME_HERE",
        "LOW_CONFIDENCE",
        "SENSOR_NOISE",
        "EMERGENCY",
        "DEVICE_OFFLINE",
    ]
    device_id: str = Field(default="DEMO001", min_length=1, max_length=100)
    language: Literal["en", "hi", "mr"] = "en"