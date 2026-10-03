from fastapi import APIRouter, Request

from backend.app.schemas.api import SettingsUpdate

router = APIRouter()


@router.get("/api/settings")
def get_settings(request: Request):
    return request.app.state.runtime.current_settings()


@router.put("/api/settings")
def update_settings(payload: SettingsUpdate, request: Request):
    values = payload.model_dump(exclude_none=True)
    return request.app.state.runtime.update_settings(values)