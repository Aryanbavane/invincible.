from datetime import date, datetime, timedelta, timezone

import pytest

from backend.app.core.processing_config import ProcessingConfig
from backend.app.services.blink_detection_service import BlinkDetectionService
from backend.app.services.command_service import CommandService
from backend.app.services.communication_service import CommunicationService
from backend.app.services.emergency_service import EmergencyService
from backend.app.services.pattern_recognition_service import PatternRecognitionService
from backend.app.services.sensor_processing_service import SensorProcessingService


class FakeClock:
    def __init__(self, current: datetime):
        self.current = current

    def __call__(self) -> datetime:
        return self.current


@pytest.mark.parametrize(
    ("duration_ms", "expected"),
    [(799, "SHORT"), (800, "LONG"), (1200, "LONG")],
)
def test_blink_duration_classification(duration_ms, expected):
    assert BlinkDetectionService().classify(duration_ms) == expected


def test_blink_calibration_can_leave_an_ambiguous_duration():
    service = BlinkDetectionService(short_blink_max_ms=600, long_blink_min_ms=900)

    assert service.classify(700) is None
    assert service.classify(500, intent_confirmed=False) is None


def test_pattern_service_uses_injected_clock_and_finalizes_after_gap():
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    clock = FakeClock(start)
    service = PatternRecognitionService(pattern_gap_ms=1500, clock=clock)
    service.add_blink("SHORT", fusion_confidence=90)
    clock.current += timedelta(milliseconds=400)
    service.add_blink("SHORT", fusion_confidence=90)
    clock.current += timedelta(milliseconds=400)
    service.add_blink("SHORT", fusion_confidence=90)

    assert service.flush() is None
    clock.current += timedelta(milliseconds=1500)
    pattern = service.flush()

    assert pattern is not None
    assert pattern.name == "SHORT_SHORT_SHORT"
    assert pattern.mapping_pattern == "3 short"
    assert pattern.fusion_confidence == 90


@pytest.mark.parametrize(
    ("pattern", "expected_command", "audio_id"),
    [
        ("1 short", "YES", "0001"),
        ("2 short", "NO", "0002"),
        ("3 short", "WATER", "0004"),
        ("4 short", "PAIN", "0005"),
        ("5 short", "COME_HERE", "0006"),
    ],
)
def test_command_mapping_for_short_patterns(pattern, expected_command, audio_id):
    event = CommandService().create_event(
        pattern, "BLINK001", 100, 100, 100, "2026-10-03T12:00:00Z"
    )

    assert event is not None
    assert event.command == expected_command
    assert event.audio_id == audio_id


def test_command_message_is_localized_but_command_is_not():
    command_service = CommandService()
    hindi = command_service.create_event(
        "3 short", "BLINK001", 100, 100, 100, "2026-10-03T12:00:00Z", "hi"
    )
    marathi = command_service.create_event(
        "3 short", "BLINK001", 100, 100, 100, "2026-10-03T12:00:00Z", "mr"
    )

    assert hindi is not None and marathi is not None
    assert hindi.command == marathi.command == "WATER"
    assert hindi.message == "मुझे पानी चाहिए।"
    assert marathi.message == "मला पाणी हवे आहे।"


def test_low_confidence_command_is_not_created_or_saved(tmp_path):
    communication = CommunicationService(tmp_path / "events.sqlite3")
    event = CommandService().create_event(
        "1 short", "BLINK001", 100, 100, 84, "2026-10-03T12:00:00Z"
    )

    assert event is None
    assert communication.history() == []
    assert communication.today_stats(date.today()) ["total"] == 0


def test_communication_history_and_today_stats(tmp_path):
    communication = CommunicationService(tmp_path / "events.sqlite3")
    command_service = CommandService()
    event = command_service.create_event(
        "1 short", "BLINK001", 90, 90, 90, "2026-10-03T12:00:00Z"
    )
    assert event is not None

    assert communication.save(event) == 1
    assert communication.history("BLINK001")[0]["command"] == "YES"
    stats = communication.today_stats(date(2026, 10, 3), "BLINK001")
    assert stats == {"date": "2026-10-03", "total": 1, "by_command": {"YES": 1}}


def test_emergency_expires_to_help_and_logs_not_confirmed(tmp_path, caplog):
    caplog.set_level("INFO")
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    clock = FakeClock(start)
    communication = CommunicationService(tmp_path / "emergency.sqlite3")
    service = EmergencyService(
        communication, CommandService(), confirmation_window_seconds=3, clock=clock
    )

    pending = service.on_long_blink("BLINK001", 95, 95, 95)
    assert pending[0].state == "POSSIBLE_EMERGENCY"
    clock.current += timedelta(seconds=3)
    assert service.poll() == []
    clock.current += timedelta(milliseconds=1)
    expired = service.poll()

    assert expired[0].state == "HELP_EMITTED"
    assert expired[0].command_event is not None
    assert expired[0].command_event.command == "HELP"
    assert expired[0].command_event.audio_id == "0003"
    assert "emergency not confirmed" in caplog.text
    assert communication.history()[0]["command"] == "HELP"
    assert service.history() == []


def test_confirmed_long_pair_creates_emergency_history_and_can_be_acknowledged(
    tmp_path,
):
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    communication = CommunicationService(tmp_path / "emergency.sqlite3")
    service = EmergencyService(communication, CommandService(), 3)

    service.on_long_blink("BLINK001", 95, 95, 95, start)
    actions = service.on_long_blink(
        "BLINK001", 95, 95, 95, start + timedelta(seconds=2)
    )

    confirmed = actions[-1]
    assert confirmed.state == "EMERGENCY_CONFIRMED"
    assert confirmed.command_event is not None
    assert confirmed.command_event.audio_id == "0007"
    assert len(service.history("BLINK001")) == 1
    acknowledged = service.acknowledge(
        confirmed.emergency_id, start + timedelta(seconds=3)
    )
    assert acknowledged is not None
    assert acknowledged["acknowledged"] == 1
    assert acknowledged["acknowledged_at"] == (start + timedelta(seconds=3)).isoformat()


def test_ambiguous_long_blink_cannot_start_emergency(tmp_path):
    communication = CommunicationService(tmp_path / "emergency.sqlite3")
    service = EmergencyService(communication, CommandService(), 3)

    action = service.on_long_blink("BLINK001", 100, 100, 84)

    assert action[0].state == "REJECTED"
    assert service.poll(datetime(2026, 10, 4, tzinfo=timezone.utc)) == []
    assert service.history() == []


def _processing_config() -> ProcessingConfig:
    return ProcessingConfig(
        emg_baseline=0,
        emg_threshold=5,
        moving_average_window=1,
        emg_rms_window=1,
    )


def _sensor_event(timestamp, state, active=True, confidence=100, duration=0):
    return {
        "device_id": "BLINK001",
        "timestamp": timestamp.isoformat(),
        "ir_state": state,
        "ir_duration_ms": duration,
        "emg_raw": 10 if active else 0,
        "emg_activity": active,
        "emg_confidence": confidence,
    }


@pytest.mark.parametrize(
    ("blink_count", "expected_command"),
    [(1, "YES"), (2, "NO"), (3, "WATER"), (4, "PAIN"), (5, "COME_HERE")],
)
def test_orchestrator_recognizes_short_blink_command_patterns(
    tmp_path, blink_count, expected_command
):
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    service = SensorProcessingService(
        config=_processing_config(), database_path=tmp_path / "events.sqlite3"
    )
    service.process(_sensor_event(start, "OPEN"))
    last_blink_time = start

    for index in range(blink_count):
        closed_at = start + timedelta(milliseconds=100 + index * 600)
        last_blink_time = closed_at + timedelta(milliseconds=300)
        service.process(_sensor_event(closed_at, "CLOSED"))
        service.process(_sensor_event(last_blink_time, "OPEN"))

    broadcasts = service.poll(last_blink_time + timedelta(milliseconds=1500))
    command_events = [item["event"] for item in broadcasts if item["type"] == "command"]

    assert len(command_events) == 1
    assert command_events[0]["command"] == expected_command
    assert len(service.communication_service.history()) == 1


def test_ir_only_and_emg_only_do_not_save_commands(tmp_path):
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    service = SensorProcessingService(
        config=_processing_config(), database_path=tmp_path / "events.sqlite3"
    )
    service.process(_sensor_event(start, "OPEN", active=True))
    service.process(
        _sensor_event(start + timedelta(milliseconds=100), "CLOSED", active=False, confidence=0)
    )
    ir_only = service.process(
        _sensor_event(start + timedelta(milliseconds=400), "OPEN", active=False, confidence=0)
    )
    emg_only = service.process(
        _sensor_event(start + timedelta(seconds=3), "OPEN", active=True)
    )

    assert ir_only["fusion"]["intent_confirmed"] is False
    assert emg_only["rejection_reason"] == "no_valid_ir_blink"
    assert service.communication_service.history() == []


def test_one_long_blink_emits_help_only_after_confirmation_window(tmp_path):
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    service = SensorProcessingService(
        config=_processing_config(), database_path=tmp_path / "events.sqlite3"
    )
    service.process(_sensor_event(start, "OPEN"))
    service.process(_sensor_event(start + timedelta(milliseconds=100), "CLOSED"))
    long_result = service.process(
        _sensor_event(start + timedelta(milliseconds=1100), "OPEN")
    )

    assert long_result["blink_type"] == "LONG"
    assert long_result["emergency_actions"][0]["state"] == "POSSIBLE_EMERGENCY"
    before_expiry = service.poll(start + timedelta(milliseconds=2600))
    assert not any(item["type"] == "help_emitted" for item in before_expiry)
    assert service.communication_service.history() == []

    after_expiry = service.poll(start + timedelta(milliseconds=4101))
    help_events = [item for item in after_expiry if item["type"] == "help_emitted"]
    assert help_events[0]["command"]["command"] == "HELP"
    assert help_events[0]["command"]["audio_id"] == "0003"


def test_two_long_blinks_confirm_emergency_in_orchestrator(tmp_path):
    start = datetime(2026, 10, 3, tzinfo=timezone.utc)
    service = SensorProcessingService(
        config=_processing_config(), database_path=tmp_path / "events.sqlite3"
    )
    service.process(_sensor_event(start, "OPEN"))
    service.process(_sensor_event(start + timedelta(milliseconds=100), "CLOSED"))
    service.process(_sensor_event(start + timedelta(milliseconds=1100), "OPEN"))
    service.process(_sensor_event(start + timedelta(milliseconds=2100), "CLOSED"))
    second = service.process(
        _sensor_event(start + timedelta(milliseconds=3100), "OPEN")
    )

    assert second["emergency_actions"][-1]["state"] == "EMERGENCY_CONFIRMED"
    assert second["emergency_actions"][-1]["command"]["audio_id"] == "0007"
    assert len(service.emergency_service.history("BLINK001")) == 1
    assert service.communication_service.history() == []