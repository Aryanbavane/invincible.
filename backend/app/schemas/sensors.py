from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EMGReading(BaseModel):
    raw: float
    filtered: float
    baseline: float | None
    activity: float
    threshold: float | None
    confidence: float = Field(ge=0, le=100)


class IRReading(BaseModel):
    state: Literal["OPEN", "CLOSED"]
    duration_ms: int = Field(ge=0)
    confidence: float = Field(ge=0, le=100)


class FusionResult(BaseModel):
    ir_confidence: float = Field(ge=0, le=100)
    emg_confidence: float = Field(ge=0, le=100)
    fusion_confidence: float = Field(ge=0, le=100)
    intent_confirmed: bool


class CommandEvent(BaseModel):
    device_id: str
    pattern: str
    command: str
    message: str
    ir_confidence: float = Field(ge=0, le=100)
    emg_confidence: float = Field(ge=0, le=100)
    fusion_confidence: float = Field(ge=0, le=100)
    audio_id: str
    timestamp: str
    source: Literal["live", "demo"] = "live"


class SensorEvent(BaseModel):
    device_id: str
    timestamp: datetime
    ir_state: Literal["OPEN", "CLOSED"]
    ir_duration_ms: int = Field(default=0, ge=0)
    emg_raw: float
    emg_activity: bool
    emg_confidence: float = Field(ge=0, le=100)
    ir_signal_raw: float | None = None
    source: Literal["live", "demo"] = "live"