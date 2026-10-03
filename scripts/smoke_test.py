import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _check(name: str, passed: bool, detail: str) -> None:
    label = "PASS" if passed else "FAIL"
    print(f"{label}: {name} - {detail}")
    if not passed:
        raise SystemExit(1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="blinkbridge-smoke-") as temporary:
        os.environ["BLINKBRIDGE_DATABASE_PATH"] = str(
            Path(temporary) / "empty-start.sqlite3"
        )
        from fastapi.testclient import TestClient

        from backend.main import app

        with TestClient(app) as client:
            heartbeat = client.post(
                "/api/device/heartbeat",
                json={
                    "device_id": "SMOKE001",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "battery": 88,
                },
            )
            _check(
                "heartbeat",
                heartbeat.status_code == 200
                and heartbeat.json().get("status") == "ONLINE",
                heartbeat.text,
            )

            water = client.post(
                "/api/demo/simulate",
                json={"scenario": "WATER", "device_id": "SMOKE_DEMO"},
            )
            water_body = water.json()
            _check(
                "simulate WATER",
                water.status_code == 200
                and water_body.get("audio_id") == "0004"
                and water_body.get("events_processed") == 7,
                f"audio_id={water_body.get('audio_id')}, events={water_body.get('events_processed')}",
            )

            history = client.get("/api/history?device_id=SMOKE_DEMO").json()
            water_event = next(
                (
                    event
                    for event in history["events"]
                    if event.get("command") == "WATER"
                ),
                None,
            )
            _check(
                "WATER in history",
                water_event is not None and water_event.get("source") == "demo",
                f"found={water_event is not None}",
            )

            emergency = client.post(
                "/api/demo/simulate",
                json={"scenario": "EMERGENCY", "device_id": "SMOKE_DEMO"},
            )
            emergency_body = emergency.json()
            emergency_id = emergency_body.get("emergency_id")
            _check(
                "simulate EMERGENCY",
                emergency.status_code == 200
                and emergency_body.get("audio_id") == "0007"
                and emergency_id is not None,
                f"audio_id={emergency_body.get('audio_id')}, emergency_id={emergency_id}",
            )

            acknowledgement = client.post(
                f"/api/emergency/{emergency_id}/acknowledge"
            )
            _check(
                "acknowledge emergency",
                acknowledgement.status_code == 200
                and acknowledgement.json().get("acknowledged") == 1,
                acknowledgement.text,
            )

            final_history = client.get("/api/history?device_id=SMOKE_DEMO").json()
            acknowledged_record = next(
                (
                    event
                    for event in final_history["events"]
                    if event.get("emergency_id") == emergency_id
                ),
                None,
            )
            _check(
                "acknowledged emergency in history",
                acknowledged_record is not None
                and acknowledged_record.get("acknowledged") == 1,
                f"found={acknowledged_record is not None}",
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())