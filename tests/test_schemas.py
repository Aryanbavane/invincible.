from backend.app.schemas.sensors import CommandEvent, EMGReading, FusionResult, IRReading


def test_sensor_and_command_schemas_accept_expected_contracts():
    emg = EMGReading(
        raw=10, filtered=8, baseline=2, activity=6, threshold=5, confidence=80
    )
    ir = IRReading(state="CLOSED", duration_ms=300, confidence=90)
    fusion = FusionResult(
        ir_confidence=90,
        emg_confidence=80,
        fusion_confidence=85,
        intent_confirmed=True,
    )
    event = CommandEvent(
        device_id="BLINK001",
        pattern="1 short",
        command="YES",
        message="Yes",
        ir_confidence=90,
        emg_confidence=80,
        fusion_confidence=85,
        audio_id="0001",
        timestamp="2026-10-03T12:00:00Z",
    )

    assert emg.activity == 6
    assert ir.state == "CLOSED"
    assert fusion.intent_confirmed is True
    assert event.audio_id == "0001"