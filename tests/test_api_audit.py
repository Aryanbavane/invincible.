from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "BLINKBRIDGE_DATABASE_PATH", str(tmp_path / "api-test.sqlite3")
    )
    with TestClient(app) as test_client:
        yield test_client


def _sensor_payload(device_id: str, timestamp: datetime, state: str):
    return {
        "device_id": device_id,
        "timestamp": timestamp.isoformat(),
        "ir_state": state,
        "ir_duration_ms": 0,
        "emg_raw": 10,
        "emg_activity": True,
        "emg_confidence": 100,
    }


def test_health_settings_calibration_history_stats_and_emergency_routes(client):
    assert client.get("/health").json() == {"status": "ok"}
    settings = client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["device_offline_timeout_seconds"] == 15
    assert client.put(
        "/api/settings", json={"device_offline_timeout_seconds": 20}
    ).json()["device_offline_timeout_seconds"] == 20

    assert client.get("/api/calibration?device_id=BLINK001").json() == {
        "device_id": "BLINK001",
        "calibrated": False,
    }
    saved = client.post(
        "/api/calibration",
        json={"device_id": "BLINK001", "emg_baseline": 10, "emg_threshold": 5},
    )
    assert saved.status_code == 200
    assert client.get("/api/calibration?device_id=BLINK001").json()[
        "emg_threshold"
    ] == 5

    now = datetime.now(timezone.utc)
    heartbeat = client.post(
        "/api/device/heartbeat",
        json={"device_id": "BLINK001", "timestamp": now.isoformat(), "battery": 82},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "ONLINE"
    assert client.get("/api/device/status?device_id=BLINK001").json()[
        "status"
    ] == "ONLINE"

    emergency = client.post("/api/emergency", json={"device_id": "BLINK001"})
    assert emergency.status_code == 200
    assert emergency.json()["command"]["audio_id"] == "0007"
    emergency_id = emergency.json()["emergency_id"]
    acknowledged = client.post(f"/api/emergency/{emergency_id}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged"] == 1
    assert acknowledged.json()["acknowledged_at"]

    history = client.get("/api/history").json()
    assert any(item["event_type"] == "emergency" for item in history["events"])
    stats = client.get("/api/stats/today").json()
    assert "total" in stats and "emergency_total" in stats


def test_heartbeat_device_goes_offline_after_default_timeout(client):
    stale = datetime.now(timezone.utc) - timedelta(seconds=16)
    response = client.post(
        "/api/device/heartbeat",
        json={"device_id": "STALE001", "timestamp": stale.isoformat(), "battery": 50},
    )

    assert response.status_code == 200
    status = client.get("/api/device/status?device_id=STALE001").json()
    assert status["status"] == "OFFLINE"
    assert status["age_seconds"] > 15


def test_sensor_event_runs_fusion_pattern_command_and_returns_audio_id(client):
    calibration = client.post(
        "/api/calibration",
        json={"device_id": "LIVE001", "emg_baseline": 0, "emg_threshold": 5},
    )
    assert calibration.status_code == 200
    start = datetime.now(timezone.utc)
    sensor_results = []
    for offset, state in ((0, "OPEN"), (100, "CLOSED"), (400, "OPEN")):
        response = client.post(
            "/api/sensor/event",
            json=_sensor_payload(
                "LIVE001", start + timedelta(milliseconds=offset), state
            ),
        )
        assert response.status_code == 200
        sensor_results.append(response.json())
    final = client.post(
        "/api/sensor/event",
        json=_sensor_payload(
            "LIVE001", start + timedelta(milliseconds=1901), "OPEN"
        ),
    )

    assert final.status_code == 200
    result = final.json()
    assert result["source"] == "live"
    assert sensor_results[2]["fusion"]["intent_confirmed"] is True
    assert result["command"]["command"] == "YES"
    assert result["command"]["audio_id"] == "0001"
    assert client.get("/api/history?device_id=LIVE001").json()["events"][0][
        "source"
    ] == "live"


def test_blink_alias_runs_sensor_pipeline(client):
    response = client.post(
        "/api/blink",
        json=_sensor_payload("BLINK_ALIAS", datetime.now(timezone.utc), "OPEN"),
    )
    assert response.status_code == 200
    assert response.json()["device_id"] == "BLINK_ALIAS"


@pytest.mark.parametrize(
    "payload",
    [
        {"device_id": "BAD", "timestamp": "not-a-date", "battery": 101},
        {"device_id": "BAD", "timestamp": "2026-10-03T12:00:00Z", "battery": 101},
    ],
)
def test_malformed_payload_returns_readable_422_without_crashing(client, payload):
    response = client.post("/api/device/heartbeat", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]
    assert client.get("/health").status_code == 200


def test_malformed_sensor_payload_returns_422_without_crashing(client):
    response = client.post(
        "/api/sensor/event",
        json={
            "device_id": "BAD",
            "timestamp": "2026-10-03T12:00:00Z",
            "ir_state": "BLINKING",
            "emg_raw": "not-a-number",
            "emg_activity": True,
            "emg_confidence": 101,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]
    assert client.get("/health").status_code == 200


def test_all_demo_scenarios_use_demo_source_and_water_returns_audio_id(client):
    scenarios = (
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
    )
    responses = {
        scenario: client.post("/api/demo/simulate", json={"scenario": scenario})
        for scenario in scenarios
    }

    assert all(response.status_code == 200 for response in responses.values())
    water = responses["WATER"].json()
    assert water["audio_id"] == "0004"
    assert water["command"]["command"] == "WATER"
    assert water["events_processed"] == 7
    assert all(event["source"] == "demo" for event in water["sensor_events"])
    water_events = water["sensor_events"]
    blink_durations = [
        round(
            (
                datetime.fromisoformat(water_events[index + 1]["timestamp"])
                - datetime.fromisoformat(water_events[index]["timestamp"])
            ).total_seconds()
            * 1000
        )
        for index in (1, 3, 5)
    ]
    assert all(270 <= duration <= 330 for duration in blink_durations)
    assert len(set(blink_durations)) > 1
    assert responses["HELP"].json()["command"]["command"] == "HELP"
    assert responses["EMERGENCY"].json()["audio_id"] == "0007"
    assert responses["LOW_CONFIDENCE"].json()["command"] is None
    assert responses["SENSOR_NOISE"].json()["command"] is None
    assert responses["DEVICE_OFFLINE"].json()["device_status"]["status"] == "OFFLINE"

    history = client.get("/api/history?device_id=DEMO001").json()["events"]
    assert any(item.get("command") == "WATER" and item["source"] == "demo" for item in history)


def test_demo_mode_switches_to_live_on_real_sensor_event(client):
    assert client.post("/api/demo/simulate", json={"scenario": "YES"}).status_code == 200
    assert client.get("/api/settings").json()["mode"] == "demo"

    response = client.post(
        "/api/sensor/event",
        json=_sensor_payload("ESP32_REAL", datetime.now(timezone.utc), "OPEN"),
    )
    assert response.status_code == 200
    assert client.get("/api/settings").json()["mode"] == "live"


def test_real_heartbeat_switches_demo_mode_to_live(client):
    assert client.post("/api/demo/simulate", json={"scenario": "YES"}).status_code == 200
    assert client.get("/api/settings").json()["mode"] == "demo"

    response = client.post(
        "/api/device/heartbeat",
        json={
            "device_id": "ESP32_HEARTBEAT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "battery": 79,
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "live"
    assert client.get("/api/settings").json()["mode"] == "live"


def test_first_launch_seeds_demo_history(client):
    events = client.get("/api/history").json()["events"]

    assert len(events) >= 3
    assert all(event["source"] == "demo" for event in events[:3])


def test_seed_data_is_not_duplicated_on_second_startup(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "BLINKBRIDGE_DATABASE_PATH", str(tmp_path / "restart.sqlite3")
    )
    with TestClient(app) as first_client:
        first_count = first_client.get("/api/history").json()["count"]
    with TestClient(app) as second_client:
        second_count = second_client.get("/api/history").json()["count"]

    assert first_count == second_count == 3


def test_low_confidence_demo_does_not_write_a_communication_event(client):
    response = client.post(
        "/api/demo/simulate",
        json={"scenario": "LOW_CONFIDENCE", "device_id": "LOWCONF001"},
    )

    assert response.status_code == 200
    assert response.json()["command"] is None
    assert client.get("/api/history?device_id=LOWCONF001").json()["events"] == []


def test_dashboard_websocket_broadcasts_device_and_sensor_events(client):
    with client.websocket_connect("/ws/dashboard") as websocket:
        assert websocket.receive_json()["type"] == "DEVICE_STATUS"
        heartbeat = client.post(
            "/api/device/heartbeat",
            json={
                "device_id": "WS001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "battery": 75,
            },
        )
        assert heartbeat.status_code == 200
        assert websocket.receive_json()["type"] == "DEVICE_STATUS"

        simulated = client.post("/api/demo/simulate", json={"scenario": "WATER"})
        assert simulated.status_code == 200
        received_types = set()
        for _ in range(30):
            message = websocket.receive_json()
            received_types.add(message["type"])
            if message["type"] == "COMMAND_DETECTED":
                break

    assert {"SENSOR_UPDATE", "BLINK_DETECTED", "COMMAND_DETECTED"} <= received_types


def test_dashboard_websocket_broadcasts_emergency_transitions(client):
    with client.websocket_connect("/ws/dashboard") as websocket:
        websocket.receive_json()
        help_response = client.post(
            "/api/demo/simulate", json={"scenario": "HELP"}
        )
        assert help_response.status_code == 200
        received_types = set()
        for _ in range(20):
            message = websocket.receive_json()
            received_types.add(message["type"])
            if message["type"] == "COMMAND_DETECTED":
                break
        assert "EMERGENCY_PENDING" in received_types

        emergency_response = client.post(
            "/api/demo/simulate", json={"scenario": "EMERGENCY"}
        )
        assert emergency_response.status_code == 200
        for _ in range(30):
            message = websocket.receive_json()
            received_types.add(message["type"])
            if message["type"] == "EMERGENCY_CONFIRMED":
                break

    assert "EMERGENCY_CONFIRMED" in received_types