from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backend.app.core.processing_config import ProcessingConfig, processing_config
from backend.app.schemas.sensors import CommandEvent, SensorEvent
from backend.app.services.blink_detection_service import BlinkDetectionService
from backend.app.services.command_service import CommandService
from backend.app.services.communication_service import CommunicationService
from backend.app.services.emergency_service import EmergencyAction, EmergencyService
from backend.app.services.emg_processing_service import EMGProcessingService
from backend.app.services.ir_processing_service import IRProcessingService
from backend.app.services.pattern_recognition_service import (
    PatternRecognitionService,
    PatternResult,
)
from backend.app.services.sensor_fusion_service import SensorFusionService


@dataclass
class _DevicePipeline:
    emg: EMGProcessingService
    ir: IRProcessingService
    patterns: PatternRecognitionService


class SensorProcessingService:
    def __init__(
        self,
        config: ProcessingConfig = processing_config,
        database_path: str | Path | None = None,
        clock: Callable[[], datetime] | None = None,
        communication_service: CommunicationService | None = None,
        command_service: CommandService | None = None,
    ) -> None:
        self.config = config
        self.clock = clock
        self.communication_service = communication_service or CommunicationService(
            database_path, config.intent_confirmed_min
        )
        self.command_service = command_service or CommandService(
            config.intent_confirmed_min
        )
        self.fusion_service = SensorFusionService(config)
        self.blink_service = BlinkDetectionService(
            config.short_blink_max_ms, config.long_blink_min_ms
        )
        self.emergency_service = EmergencyService(
            self.communication_service,
            self.command_service,
            config.emergency_confirmation_window_seconds,
            clock,
        )
        self._devices: dict[str, _DevicePipeline] = {}
        self._calibration_overrides: dict[str, tuple[float, float]] = {}

    def _pipeline_for(self, device_id: str) -> _DevicePipeline:
        if device_id not in self._devices:
            baseline, threshold = self._calibration_overrides.get(
                device_id, (self.config.emg_baseline, self.config.emg_threshold)
            )
            self._devices[device_id] = _DevicePipeline(
                emg=EMGProcessingService(
                    baseline=baseline,
                    threshold=threshold,
                    moving_average_window=self.config.moving_average_window,
                    rms_window=self.config.emg_rms_window,
                ),
                ir=IRProcessingService(
                    threshold=self.config.ir_threshold,
                    crossing_margin=self.config.ir_crossing_margin,
                ),
                patterns=PatternRecognitionService(
                    self.config.pattern_gap_ms, self.clock
                ),
            )
        return self._devices[device_id]

    def set_device_calibration(
        self, device_id: str, emg_baseline: float, emg_threshold: float
    ) -> None:
        self._calibration_overrides[device_id] = (emg_baseline, emg_threshold)
        pipeline = self._devices.get(device_id)
        if pipeline is not None:
            pipeline.emg.update_calibration(emg_baseline, emg_threshold)

    def clear_device_calibration(self, device_id: str) -> None:
        self._calibration_overrides.pop(device_id, None)
        pipeline = self._devices.get(device_id)
        if pipeline is not None:
            pipeline.emg.update_calibration(
                self.config.emg_baseline, self.config.emg_threshold
            )
            pipeline.ir.threshold = self.config.ir_threshold
            pipeline.ir.crossing_margin = self.config.ir_crossing_margin

    def set_device_ir_calibration(
        self,
        device_id: str,
        ir_threshold: float | None,
        crossing_margin: float | None,
    ) -> None:
        pipeline = self._pipeline_for(device_id)
        pipeline.ir.threshold = ir_threshold
        pipeline.ir.crossing_margin = crossing_margin

    def _resolve_pattern(
        self, pattern: PatternResult, device_id: str, language: str
    ) -> CommandEvent | None:
        if any(blink_type != "SHORT" for blink_type in pattern.sequence):
            return None
        event = self.command_service.resolve(pattern, device_id, language)
        if event is None:
            return None
        event_id = self.communication_service.save(event)
        if event_id is None:
            return None
        return event

    @staticmethod
    def _action_broadcast(action: EmergencyAction) -> dict[str, Any]:
        return {
            "type": action.state.lower(),
            "device_id": action.device_id,
            "emergency_id": action.emergency_id,
            "note": action.note,
            "command": action.command_event.model_dump()
            if action.command_event is not None
            else None,
        }

    def poll(
        self, timestamp: datetime | str | None = None, language: str = "en"
    ) -> list[dict[str, Any]]:
        broadcasts: list[dict[str, Any]] = []
        for device_id, pipeline in self._devices.items():
            pattern = pipeline.patterns.flush(timestamp)
            if pattern is not None:
                command = self._resolve_pattern(pattern, device_id, language)
                if command is not None:
                    broadcasts.append(
                        {"type": "command", "event": command.model_dump()}
                    )
        broadcasts.extend(
            self._action_broadcast(action)
            for action in self.emergency_service.poll(timestamp)
        )
        return broadcasts

    def process(
        self, sensor_event: SensorEvent | dict[str, Any], language: str = "en"
    ) -> dict[str, Any]:
        event = (
            sensor_event
            if isinstance(sensor_event, SensorEvent)
            else SensorEvent.model_validate(sensor_event)
        )
        timestamp = event.timestamp
        pipeline = self._pipeline_for(event.device_id)
        broadcasts: list[dict[str, Any]] = []
        command_event: CommandEvent | None = None
        emergency_actions: list[EmergencyAction] = []

        for action in self.emergency_service.poll(timestamp):
            emergency_actions.append(action)
            broadcasts.append(self._action_broadcast(action))

        pending_pattern = pipeline.patterns.flush(timestamp)
        if pending_pattern is not None:
            command_event = self._resolve_pattern(pending_pattern, event.device_id, language)
            if command_event is not None:
                broadcasts.append(
                    {"type": "command", "event": command_event.model_dump()}
                )

        emg = pipeline.emg.process(event.emg_raw)
        emg = emg.model_copy(
            update={"confidence": min(emg.confidence, event.emg_confidence)}
        )
        ir = pipeline.ir.process(
            event.ir_state,
            timestamp,
            event.ir_signal_raw,
            event.ir_duration_ms,
        )
        decision = self.fusion_service.fuse(ir, emg, event.emg_activity)
        blink_type = None

        if decision.result.intent_confirmed:
            blink_type = self.blink_service.classify(ir.duration_ms)
            if blink_type is not None:
                pending_pattern = pipeline.patterns.add_blink(
                    blink_type,
                    timestamp,
                    decision.result.ir_confidence,
                    decision.result.emg_confidence,
                    decision.result.fusion_confidence,
                    event.source,
                )
                if pending_pattern is not None:
                    command_event = self._resolve_pattern(
                        pending_pattern, event.device_id, language
                    ) or command_event
                    if command_event is not None:
                        broadcasts.append(
                            {"type": "command", "event": command_event.model_dump()}
                        )
                if blink_type == "LONG":
                    emergency_actions.extend(
                        self.emergency_service.on_long_blink(
                            event.device_id,
                            decision.result.ir_confidence,
                            decision.result.emg_confidence,
                            decision.result.fusion_confidence,
                            timestamp,
                            language,
                            event.source,
                        )
                    )
            else:
                broadcasts.append(
                    {"type": "blink_ambiguous", "duration_ms": ir.duration_ms}
                )

        broadcasts.extend(
            self._action_broadcast(action)
            for action in emergency_actions
        )
        if decision.feedback is not None:
            broadcasts.append(
                {
                    "type": "signal_uncertain",
                    "message": decision.feedback,
                    "fusion_confidence": decision.result.fusion_confidence,
                }
            )
        elif decision.level == "possible_intent":
            broadcasts.append(
                {
                    "type": "possible_intent",
                    "fusion_confidence": decision.result.fusion_confidence,
                }
            )

        return {
            "device_id": event.device_id,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "emg": emg.model_dump(),
            "ir": ir.model_dump(),
            "fusion": decision.result.model_dump(),
            "fusion_level": decision.level,
            "rejection_reason": decision.rejection_reason,
            "blink_type": blink_type,
            "command": command_event.model_dump() if command_event else None,
            "emergency_actions": [
                {
                    "state": action.state,
                    "emergency_id": action.emergency_id,
                    "note": action.note,
                    "command": action.command_event.model_dump()
                    if action.command_event is not None
                    else None,
                }
                for action in emergency_actions
            ],
            "events_to_broadcast": broadcasts,
        }