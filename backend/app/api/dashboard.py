from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard(websocket: WebSocket):
    runtime = websocket.app.state.runtime
    manager = runtime.websocket_manager
    await manager.connect(websocket)
    await websocket.send_json(
        {"type": "DEVICE_STATUS", "payload": {"mode": runtime.mode}}
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)