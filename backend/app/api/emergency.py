from fastapi import APIRouter, HTTPException, Request

from backend.app.schemas.api import EmergencyRequest

router = APIRouter()


@router.post("/api/emergency")
async def raise_emergency(payload: EmergencyRequest, request: Request):
    runtime = request.app.state.runtime
    action = runtime.sensor_processing.emergency_service.raise_emergency(
        payload.device_id,
        payload.timestamp,
        payload.language,
        payload.source,
    )
    result = {
        "state": action.state,
        "emergency_id": action.emergency_id,
        "command": action.command_event.model_dump()
        if action.command_event is not None
        else None,
    }
    await runtime.websocket_manager.broadcast(
        {"type": "EMERGENCY_CONFIRMED", "payload": result}
    )
    return result


@router.post("/api/emergency/{emergency_id}/acknowledge")
async def acknowledge_emergency(emergency_id: int, request: Request):
    runtime = request.app.state.runtime
    result = runtime.sensor_processing.emergency_service.acknowledge(emergency_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Emergency event not found")
    await runtime.websocket_manager.broadcast(
        {"type": "EMERGENCY_CONFIRMED", "payload": result}
    )
    return result