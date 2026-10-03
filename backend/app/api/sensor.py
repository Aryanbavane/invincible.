from fastapi import APIRouter, Request

from backend.app.api.event_pipeline import process_sensor_event
from backend.app.schemas.sensors import SensorEvent

router = APIRouter()


@router.post("/api/sensor/event")
async def sensor_event(payload: SensorEvent, request: Request):
    return await process_sensor_event(request.app.state.runtime, payload)


@router.post("/api/blink")
async def blink_event(payload: SensorEvent, request: Request):
    return await process_sensor_event(request.app.state.runtime, payload)