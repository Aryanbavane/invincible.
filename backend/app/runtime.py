import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.app.core.processing_config import ProcessingConfig, load_processing_config
from backend.app.services.calibration_service import CalibrationService
from backend.app.services.command_service import CommandService
from backend.app.services.communication_service import CommunicationService
from backend.app.services.demo_service import DemoService
from backend.app.services.device_service import DeviceService
from backend.app.services.sensor_processing_service import SensorProcessingService
from backend.app.services.websocket_manager import WebSocketManager


class RuntimeContext:
    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(
            database_path
            or os.getenv("BLINKBRIDGE_DATABASE_PATH", "data/blinkbridge.sqlite3")
        )
        self.config: ProcessingConfig = load_processing_config()
        self.communication = CommunicationService(
            self.database_path, self.config.intent_confirmed_min
        )
        self.commands = CommandService(self.config.intent_confirmed_min)
        self.sensor_processing = SensorProcessingService(
            config=self.config,
            database_path=self.database_path,
            communication_service=self.communication,
            command_service=self.commands,
        )
        self.device_service = DeviceService(
            self.database_path, self.config.device_offline_timeout_seconds
        )
        self.calibration_service = CalibrationService(self.database_path)
        self.demo_service = DemoService()
        self.websocket_manager = WebSocketManager()
        self.mode = "live"
        self._applied_calibrations: dict[str, int] = {}
        self._demo_devices: set[str] = set()
        self.settings: dict[str, Any] = {
            "device_offline_timeout_seconds": self.config.device_offline_timeout_seconds,
            "supported_sensor_mode": os.getenv("SUPPORTED_SENSOR_MODE", "dual"),
        }

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        self.settings.update(values)
        self.device_service.offline_timeout_seconds = float(
            self.settings["device_offline_timeout_seconds"]
        )
        return self.current_settings()

    def current_settings(self) -> dict[str, Any]:
        return {**self.settings, "mode": self.mode}

    def seed_demo_history(self) -> bool:
        if self.communication.history(limit=1):
            return False
        now = datetime.now(timezone.utc)
        for offset, pattern in enumerate(("1 short", "3 short", "4 short")):
            event = self.commands.create_event(
                pattern,
                "DEMO001",
                96,
                94,
                95,
                now - timedelta(hours=offset * 2),
                "en",
                source="demo",
            )
            if event is not None:
                self.communication.save(event)
        return True

    def configure_demo_device(self, device_id: str, scenario: str) -> None:
        self._demo_devices.add(device_id)
        self.sensor_processing.set_device_calibration(device_id, 0, 5)
        self.sensor_processing.set_device_ir_calibration(
            device_id,
            100 if scenario == "SENSOR_NOISE" else None,
            10 if scenario == "SENSOR_NOISE" else None,
        )

    def prepare_live_device(self, device_id: str) -> None:
        if device_id in self._demo_devices:
            self.sensor_processing.clear_device_calibration(device_id)
            self._demo_devices.discard(device_id)
            self._applied_calibrations.pop(device_id, None)

    def apply_saved_calibration(self, device_id: str) -> None:
        calibration = self.calibration_service.get(device_id)
        if not calibration.get("calibrated"):
            return
        calibration_id = int(calibration["calibration_id"])
        if self._applied_calibrations.get(device_id) == calibration_id:
            return
        self.sensor_processing.set_device_calibration(
            device_id,
            float(calibration["emg_baseline"]),
            float(calibration["emg_threshold"]),
        )
        self._applied_calibrations[device_id] = calibration_id