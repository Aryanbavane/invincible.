from collections import deque
from math import sqrt

from backend.app.schemas.sensors import EMGReading


class EMGProcessingService:
    def __init__(
        self,
        baseline: float | None,
        threshold: float | None,
        moving_average_window: int = 5,
        rms_window: int = 5,
    ) -> None:
        if moving_average_window < 1 or rms_window < 1:
            raise ValueError("EMG filter windows must be positive")
        if threshold is not None and threshold <= 0:
            raise ValueError("EMG threshold must be positive when configured")
        self.baseline = baseline
        self.threshold = threshold
        self._raw_values: deque[float] = deque(maxlen=moving_average_window)
        self._baseline_deltas: deque[float] = deque(maxlen=rms_window)

    def update_calibration(
        self, emg_baseline: float | None, threshold: float | None
    ) -> None:
        if threshold is not None and threshold <= 0:
            raise ValueError("EMG threshold must be positive")
        self.baseline = emg_baseline
        self.threshold = threshold
        self._raw_values.clear()
        self._baseline_deltas.clear()

    def process(self, emg_raw: float) -> EMGReading:
        self._raw_values.append(float(emg_raw))
        filtered = sum(self._raw_values) / len(self._raw_values)
        if self.baseline is None:
            return EMGReading(
                raw=emg_raw,
                filtered=filtered,
                baseline=None,
                activity=0,
                threshold=self.threshold,
                confidence=0,
            )

        self._baseline_deltas.append(filtered - self.baseline)
        activity = sqrt(
            sum(delta * delta for delta in self._baseline_deltas)
            / len(self._baseline_deltas)
        )
        emg_activity_score = 0.0
        if self.threshold is not None:
            emg_activity_score = min(100.0, activity / self.threshold * 100.0)
        return EMGReading(
            raw=emg_raw,
            filtered=filtered,
            baseline=self.baseline,
            activity=activity,
            threshold=self.threshold,
            confidence=emg_activity_score,
        )