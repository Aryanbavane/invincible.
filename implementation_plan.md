# BlinkBridge Implementation Plan

## Architecture
- ESP32 reads the IR eye sensor and EMG Muscle Sensor V3.0; device transport sends timestamped readings to the Python backend. GPIOs and electrical integration remain configurable and unspecified until hardware integration.
- FastAPI owns device-facing API/WebSocket boundaries, deterministic EMG processing, IR event interpretation, sensor fusion, command resolution, event persistence, and caregiver alert events.
- SQLite stores users, devices, calibrations, communication events, emergency events, and device heartbeats. No other application tables are planned.
- React, Vite, TypeScript, Tailwind, lucide-react, and Recharts power the implemented Live Dashboard; Calibration, History, Device, and Settings remain placeholders.
- DFPlayer Mini audio IDs resolve from a backend-owned command mapping; message text includes English, Hindi, and Marathi variants.

## API contracts
- `GET /health` returns `{"status":"ok"}` when the API process is available.
- Device heartbeat/status, sensor-event/blink ingestion, calibration, settings, emergency acknowledgement, history/today stats, and demo simulation routes are implemented under `/api/` with Pydantic validation.
- `/ws/dashboard` broadcasts sensor, blink, command, emergency, and device-status events.
- Demo scenarios generate timestamped synthetic sensor readings and call the same `SensorProcessingService` as live sensor events. Demo event and history rows carry `source: "demo"`; real sensor events switch runtime mode to `live`.
- Device status defaults to offline after 15 seconds without a heartbeat; `DEVICE_OFFLINE_TIMEOUT_SECONDS` is configurable.
- `intent_confirmed` must represent fusion output, not a single-sensor threshold crossing.

## Database schema
- `users`: local user profile and preferred language.
- `devices`: device identity, owning user (optional), and connection status.
- `calibrations`: per-device baseline and threshold values with calibration time.
- `communication_events`: recognized command, message, sensor/fusion confidence, audio ID, and timestamp.
- `emergency_events`: locally raised emergency message and acknowledgement state.
- `device_heartbeats`: device status and last-seen time.
- SQLite setup creates exactly these six tables. Foreign keys are enabled; no authentication or external alert delivery is included.
- Existing databases are migrated by adding source/battery columns to these tables; no new tables are introduced.

## Sensor data models
- EMG: `raw`, `filtered`, `baseline`, `activity`, `threshold`, `confidence`.
- IR: `state` (`OPEN` or `CLOSED`), `duration_ms`, `confidence`.
- Fusion: `ir_confidence`, `emg_confidence`, `fusion_confidence`, `intent_confirmed`.
- Command event: `device_id`, `pattern`, `command`, `message`, the three confidence values, `audio_id`, and `timestamp`.
- Service confidence values are normalized to 0 through 100. Sensor values and hardware thresholds are not treated as medical measurements.

## EMG processing approach
- Apply a configurable moving-average filter, then short-window RMS of filtered-signal deltas from the calibrated baseline (`emgBaseline`). No FFT is used.
- Compare RMS activity with the calibrated configurable threshold and normalize activity to a 0–100 confidence score. Missing calibration/threshold yields no EMG confidence and cannot confirm intent.
- Keep sample rate, filter parameters, threshold, and baseline configurable. Do not choose hardware-specific values until the actual board/sensor and measured noise are available.
- Validate with recorded/synthetic fixtures and sensor disconnection/noise cases before hardware testing.

## Sensor fusion approach
- Timestamp IR transitions and EMG activity windows; accept a candidate gesture only when matching activity occurs inside a configurable temporal window.
- Compute fusion confidence from both sensor confidences and reject mismatched or low-confidence events. The initial weighting/window must be configurable and tuned with bench data, not presented as medically validated.
- Apply a gesture state machine for short/long blink patterns, debounce repeated transitions, and avoid duplicate command emission.
- Keep emergency gestures as local alerts; do not automatically call emergency services.

## Demo and seed behavior
- First startup inserts a small set of history examples only when communication history is empty; examples are marked `demo`.
- Demo WATER produces three short OPEN/CLOSED/OPEN blink sequences with timestamp jitter. These enter the real sensor processor, pattern timer, command mapper, WebSocket broadcast, and SQLite communication history.
- Demo emergency requires two long blinks; one long blink resolves to HELP only after the configurable confirmation window expires.
- Demo signal/noise/offline scenarios are synthetic. No physical sensors, speaker playback, external emergency dispatch, or frontend are simulated as connected hardware.

## Frontend structure
- `components/`: accessible navigation, sensor status, confidence bars, emergency dialog, eye illustration, and timeline.
- `pages/`: Live Dashboard plus placeholders for Calibration, History, Device, and Settings.
- `hooks/`: reconnecting WebSocket and dashboard state.
- `services/`: typed REST client.
- `types/`: frontend API/event contracts.
- `charts/`: synchronized Recharts IR and EMG views.
- `utils/`: reserved for small pure helpers.
- The Live Dashboard consumes the backend API/WebSocket and demo simulator; command mappings stay in backend configuration.

## Testing strategy
- Unit-test hardware environment parsing, exact SQLite table creation/migrations, schema validation, EMG processing, and fusion edge cases.
- API-test routes, malformed payloads, demo/live mode, WebSocket broadcasts, offline timeout, seed idempotency, and emergency acknowledgement with isolated temporary SQLite databases.
- Run `python scripts/smoke_test.py` for heartbeat, WATER history, emergency simulation, acknowledgement, and final history checks.
- Test command mapping completeness, language strings, and unique audio IDs.
- Use deterministic synthetic signal fixtures; later add bench recordings and manual hardware-integration checks without claiming clinical accuracy.
- Run `python -m pytest` after each backend phase. Add frontend checks when UI implementation begins.