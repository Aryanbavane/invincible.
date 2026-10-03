from dataclasses import dataclass

from backend.app.core.processing_config import ProcessingConfig
from backend.app.schemas.sensors import EMGReading, FusionResult, IRReading


@dataclass(frozen=True)
class FusionDecision:
    result: FusionResult
    level: str
    feedback: str | None
    rejection_reason: str | None


class SensorFusionService:
    def __init__(self, config: ProcessingConfig) -> None:
        self.config = config

    def fuse(
        self,
        ir: IRReading,
        emg: EMGReading,
        emg_activity_reported: bool = True,
    ) -> FusionDecision:
        valid_ir_blink = ir.duration_ms > 0 and ir.confidence > 0
        threshold_crossed = (
            emg.threshold is not None and emg.activity > emg.threshold
        )
        emg_active = threshold_crossed and emg_activity_reported

        if not valid_ir_blink:
            fusion_confidence = 0.0
            rejection_reason = "no_valid_ir_blink"
        else:
            total_weight = (
                self.config.ir_confidence_weight
                + self.config.emg_confidence_weight
            )
            fusion_confidence = (
                ir.confidence * self.config.ir_confidence_weight
                + emg.confidence * self.config.emg_confidence_weight
            ) / total_weight
            rejection_reason = None

        confirmed = (
            valid_ir_blink
            and emg_active
            and fusion_confidence >= self.config.intent_confirmed_min
        )
        if not emg_active and valid_ir_blink:
            fusion_confidence = min(
                fusion_confidence, self.config.intent_confirmed_min - 1
            )
            rejection_reason = "emg_below_threshold"

        if confirmed:
            level = "intent_confirmed"
            feedback = None
        elif fusion_confidence >= self.config.possible_intent_min:
            level = "possible_intent"
            feedback = None
        else:
            level = "low"
            feedback = "Signal uncertain, please repeat"

        return FusionDecision(
            result=FusionResult(
                ir_confidence=ir.confidence,
                emg_confidence=emg.confidence,
                fusion_confidence=fusion_confidence,
                intent_confirmed=confirmed,
            ),
            level=level,
            feedback=feedback,
            rejection_reason=rejection_reason,
        )