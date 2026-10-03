import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from backend.app.api.calibration import router as calibration_router
from backend.app.api.communication import router as communication_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.demo import router as demo_router
from backend.app.api.device import router as device_router
from backend.app.api.emergency import router as emergency_router
from backend.app.api.health import router as health_router
from backend.app.api.sensor import router as sensor_router
from backend.app.api.settings import router as settings_router
from backend.app.runtime import RuntimeContext


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    database_path = Path(
        os.getenv("BLINKBRIDGE_DATABASE_PATH", "data/blinkbridge.sqlite3")
    )
    runtime = RuntimeContext(database_path)
    runtime.seed_demo_history()
    app.state.runtime = runtime
    yield


app = FastAPI(title="BlinkBridge API", lifespan=lifespan)
for router in (
    health_router,
    device_router,
    sensor_router,
    communication_router,
    calibration_router,
    settings_router,
    emergency_router,
    demo_router,
    dashboard_router,
):
    app.include_router(router)