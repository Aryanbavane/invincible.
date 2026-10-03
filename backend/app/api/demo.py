from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from backend.app.api.event_pipeline import process_sensor_event, publish_polled_events
from backend.app.schemas.api import DemoSimulationRequest

router = APIRouter()


@router.post("/api/demo/simulate")
async def simulate(payload: DemoSimulationRequest, request: Request):
    runtime = request.app.state.runtime
    runtime.mode = "demo"
    await runtime.websocket_manager.broadcast(
        {"type": "DEVICE_STATUS", "payload": {"mode": runtime.mode}}
    )
    runtime.configure_demo_device(payload.device_id, payload.scenario)

    if payload.scenario == "DEVICE_OFFLINE":
        stale_time = datetime.now(timezone.utc) - timedelta(
            seconds=runtime.device_service.offline_timeout_seconds + 1
        )
        runtime.device_service.heartbeat(payload.device_id, stale_time, 85)
        status = runtime.device_service.status(payload.device_id)
        await runtime.websocket_manager.broadcast(
            {
                "type": "DEVICE_STATUS",
                "payload": {**status, "source": "demo", "mode": runtime.mode},
            }
        )
        return {
            "scenario": payload.scenario,
            "source": "demo",
            "device_status": status,
            "events_processed": 0,
        }

    sensor_events = runtime.demo_service.generate(
        payload.scenario, payload.device_id
    )
    results = [
        await process_sensor_event(runtime, event, payload.language)
        for event in sensor_events
    ]
    last_timestamp = sensor_events[-1].timestamp
    if payload.scenario == "HELP":
        flush_time = last_timestamp + timedelta(
            seconds=runtime.config.emergency_confirmation_window_seconds,
            milliseconds=1,
        )
    elif payload.scenario not in {"LOW_CONFIDENCE", "SENSOR_NOISE"}:
        flush_time = last_timestamp + timedelta(
            milliseconds=runtime.config.pattern_gap_ms + 1
        )
    else:
        flush_time = last_timestamp + timedelta(
            milliseconds=runtime.config.pattern_gap_ms + 1
        )
    polled_events = runtime.sensor_processing.poll(flush_time, payload.language)
    await publish_polled_events(runtime, polled_events, "demo")
    command = next(
        (
            event["event"]
            for result in reversed(results)
            for event in reversed(result["events_to_broadcast"])
            if event.get("type") == "command"
        ),
        None,
    )
    if command is None:
        command = next(
            (
                event.get("event", event.get("command"))
                for event in polled_events
                if event.get("event") or event.get("command")
            ),
            None,
        )
    if command is None:
        command = next(
            (
                action["command"]
                for result in reversed(results)
                for action in reversed(result["emergency_actions"])
                if action.get("command") is not None
            ),
            None,
        )
    emergency_id = next(
        (
            action["emergency_id"]
            for result in reversed(results)
            for action in reversed(result["emergency_actions"])
            if action.get("emergency_id") is not None
        ),
        None,
    )
    return {
        "scenario": payload.scenario,
        "source": "demo",
        "events_processed": len(sensor_events),
        "sensor_events": [event.model_dump(mode="json") for event in sensor_events],
        "command": command,
        "audio_id": command.get("audio_id") if command else None,
        "emergency_id": emergency_id,
        "results": results,
        "events_to_broadcast": polled_events,
    }