from fastapi import APIRouter, Query, Request

from backend.app.schemas.api import CalibrationRequest

router = APIRouter()


@router.get("/api/calibration")
def get_calibration(
    request: Request,
    device_id: str = Query(default="BLINK001", min_length=1),
):
    return request.app.state.runtime.calibration_service.get(device_id)


@router.post("/api/calibration")
def save_calibration(payload: CalibrationRequest, request: Request):
    runtime = request.app.state.runtime
    calibration = runtime.calibration_service.save(
        payload.device_id, payload.emg_baseline, payload.emg_threshold
    )
    runtime.sensor_processing.set_device_calibration(
        payload.device_id, payload.emg_baseline, payload.emg_threshold
    )
    runtime._applied_calibrations[payload.device_id] = calibration["calibration_id"]
    return calibration