from datetime import datetime, timedelta, timezone
from math import sqrt

from backend.app.core.processing_config import ProcessingConfig
from backend.app.schemas.sensors import EMGReading, IRReading
from backend.app.services.emg_processing_service import EMGProcessingService
from backend.app.services.ir_processing_service import IRProcessingService
from backend.app.services.sensor_fusion_service import SensorFusionService


def test_emg_filter_uses_calibrated_baseline_and_short_window_rms():
    service = EMGProcessingService(
        baseline=100, threshold=5, moving_average_window=2, rms_window=2
    )

    first = service.process(110)
    second = service.process(100)

    assert first.filtered == 110
    assert first.baseline == 100
    assert first.activity == 10
    assert first.confidence == 100
    assert second.filtered == 105
    assert second.activity == sqrt((10**2 + 5**2) / 2)
    assert second.confidence == 100


def test_uncalibrated_emg_never_claims_activity_confidence():
    result = EMGProcessingService(
        baseline=None, threshold=5, moving_average_window=1, rms_window=1
    ).process(120)

    assert result.baseline is None
    assert result.activity == 0
    assert result.confidence == 0


def test_ir_detects_open_closed_open_duration_and_crossing_quality():
    service = IRProcessingService(threshold=100, crossing_margin=10)
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)

    service.process("OPEN", start, signal_value=110)
    service.process("CLOSED", start + timedelta(milliseconds=100), signal_value=90)
    result = service.process(
        "OPEN", start + timedelta(milliseconds=400), signal_value=110
    )

    assert result.state == "OPEN"
    assert result.duration_ms == 300
    assert result.confidence == 100


def test_ir_near_threshold_crossing_has_lower_confidence():
    service = IRProcessingService(threshold=100, crossing_margin=10)
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)

    service.process("OPEN", start, signal_value=110)
    service.process("CLOSED", start + timedelta(milliseconds=100), signal_value=101)
    result = service.process(
        "OPEN", start + timedelta(milliseconds=400), signal_value=110
    )

    assert result.confidence == 10


def test_ir_accepts_a_firmware_measured_blink_on_repeated_open_events():
    service = IRProcessingService()
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)

    first = service.process("OPEN", start, duration_hint_ms=250)
    second = service.process(
        "OPEN", start + timedelta(milliseconds=300), duration_hint_ms=275
    )

    assert first.duration_ms == 250
    assert second.duration_ms == 275


def test_fusion_confirms_only_when_completed_ir_and_thresholded_emg_agree():
    service = SensorFusionService(ProcessingConfig())
    ir = IRReading(state="OPEN", duration_ms=300, confidence=100)
    strong_emg = EMGReading(
        raw=110, filtered=110, baseline=100, activity=10, threshold=5, confidence=100
    )
    weak_emg = EMGReading(
        raw=102, filtered=102, baseline=100, activity=2, threshold=5, confidence=40
    )

    agreed = service.fuse(ir, strong_emg)
    weak = service.fuse(ir, weak_emg)
    ir_noise = service.fuse(
        IRReading(state="OPEN", duration_ms=0, confidence=0), strong_emg
    )
    emg_only = service.fuse(
        IRReading(state="OPEN", duration_ms=0, confidence=0), strong_emg
    )

    assert agreed.result.fusion_confidence == 100
    assert agreed.result.intent_confirmed is True
    assert weak.result.intent_confirmed is False
    assert weak.level == "possible_intent"
    assert ir_noise.rejection_reason == "no_valid_ir_blink"
    assert emg_only.result.fusion_confidence == 0
    assert emg_only.result.intent_confirmed is False