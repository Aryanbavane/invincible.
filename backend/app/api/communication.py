from datetime import date
from typing import Any

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/api/history")
def history(
    request: Request,
    device_id: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    runtime = request.app.state.runtime
    communications = runtime.communication.history(device_id, limit)
    emergencies = runtime.sensor_processing.emergency_service.history(device_id)
    entries = [
        {**event, "event_type": "communication", "timestamp": event["timestamp"]}
        for event in communications
    ]
    entries.extend(
        {
            **event,
            "event_type": "emergency",
            "command": "EMERGENCY",
            "audio_id": "0007",
            "timestamp": event["created_at"],
        }
        for event in emergencies
    )
    entries.sort(key=lambda event: event["timestamp"], reverse=True)
    return {"events": entries[:limit], "count": min(len(entries), limit)}


@router.get("/api/stats/today")
def today_stats(request: Request, device_id: str | None = None) -> dict[str, Any]:
    runtime = request.app.state.runtime
    stats = runtime.communication.today_stats(date.today(), device_id)
    emergency_count = sum(
        1
        for item in runtime.sensor_processing.emergency_service.history(device_id)
        if date.fromisoformat(item["created_at"][:10]) == date.today()
    )
    return {**stats, "emergency_total": emergency_count}