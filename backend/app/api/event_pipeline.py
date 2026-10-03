from typing import Any

from backend.app.runtime import RuntimeContext
from backend.app.schemas.sensors import SensorEvent


async def publish_processing_result(
    runtime: RuntimeContext, result: dict[str, Any]
) -> None:
    await runtime.websocket_manager.broadcast(
        {"type": "SENSOR_UPDATE", "payload": result}
    )
    if result.get("blink_type"):
        await runtime.websocket_manager.broadcast(
            {
                "type": "BLINK_DETECTED",
                "device_id": result["device_id"],
                "source": result["source"],
                "blink_type": result["blink_type"],
                "duration_ms": result["ir"]["duration_ms"],
                "fusion_confidence": result["fusion"]["fusion_confidence"],
            }
        )
    for event in result.get("events_to_broadcast", []):
        event_type = event.get("type")
        if event_type == "command":
            await runtime.websocket_manager.broadcast(
                {"type": "COMMAND_DETECTED", "payload": event["event"]}
            )
        elif event_type == "possible_emergency":
            await runtime.websocket_manager.broadcast(
                {"type": "EMERGENCY_PENDING", "payload": event}
            )
        elif event_type == "emergency_confirmed":
            await runtime.websocket_manager.broadcast(
                {"type": "EMERGENCY_CONFIRMED", "payload": event}
            )
        elif event_type == "help_emitted":
            await runtime.websocket_manager.broadcast(
                {"type": "COMMAND_DETECTED", "payload": event.get("command")}
            )


async def process_sensor_event(
    runtime: RuntimeContext, event: SensorEvent, language: str = "en"
) -> dict[str, Any]:
    if event.source == "live":
        runtime.mode = "live"
        runtime.prepare_live_device(event.device_id)
        runtime.apply_saved_calibration(event.device_id)
        runtime.device_service.observe_event(event.device_id, event.timestamp)
        status = runtime.device_service.status(event.device_id)
        await runtime.websocket_manager.broadcast(
            {
                "type": "DEVICE_STATUS",
                "payload": {**status, "mode": runtime.mode},
            }
        )
    result = runtime.sensor_processing.process(event, language)
    await publish_processing_result(runtime, result)
    return result


async def publish_polled_events(
    runtime: RuntimeContext, events: list[dict[str, Any]], source: str
) -> None:
    for event in events:
        event_type = event.get("type")
        if event_type == "command":
            payload = {**event["event"], "source": source}
            await runtime.websocket_manager.broadcast(
                {"type": "COMMAND_DETECTED", "payload": payload}
            )
        elif event_type == "help_emitted":
            payload = event.get("command")
            await runtime.websocket_manager.broadcast(
                {"type": "COMMAND_DETECTED", "payload": payload}
            )
        elif event_type == "emergency_confirmed":
            await runtime.websocket_manager.broadcast(
                {"type": "EMERGENCY_CONFIRMED", "payload": event}
            )
        elif event_type == "possible_emergency":
            await runtime.websocket_manager.broadcast(
                {"type": "EMERGENCY_PENDING", "payload": event}
            )