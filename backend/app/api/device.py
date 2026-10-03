from fastapi import APIRouter, Query, Request

from backend.app.schemas.api import HeartbeatRequest

router = APIRouter()


@router.post("/api/device/heartbeat")
async def heartbeat(payload: HeartbeatRequest, request: Request):
    runtime = request.app.state.runtime
    runtime.mode = "live"
    runtime.prepare_live_device(payload.device_id)
    runtime.apply_saved_calibration(payload.device_id)
    result = runtime.device_service.heartbeat(
        payload.device_id, payload.timestamp, payload.battery
    )
    result["mode"] = runtime.mode
    await runtime.websocket_manager.broadcast(
        {"type": "DEVICE_STATUS", "payload": result}
    )
    return result


@router.get("/api/device/status")
async def device_status(
    request: Request, device_id: str | None = Query(default=None, min_length=1)
):
    runtime = request.app.state.runtime
    result = runtime.device_service.status(device_id)
    if isinstance(result, list):
        for status in result:
            await runtime.websocket_manager.broadcast(
                {"type": "DEVICE_STATUS", "payload": {**status, "mode": runtime.mode}}
            )
    else:
        await runtime.websocket_manager.broadcast(
            {
                "type": "DEVICE_STATUS",
                "payload": {**result, "mode": runtime.mode},
            }
        )
    return result