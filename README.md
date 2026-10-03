# BlinkBridge

BlinkBridge is a hackathon prototype that combines IR eye-state changes with matching EMG activity to identify intentional blink patterns, speak mapped messages through a DFPlayer Mini, and create local caregiver alerts.

The backend includes REST routes, a dashboard WebSocket, deterministic dual-sensor processing, SQLite history, and demo scenarios that pass synthetic sensor events through the same processing pipeline used for live events. The frontend includes the Live Dashboard; Calibration, History, Device, and Settings pages are placeholders. Physical ESP32/IR/EMG/DFPlayer integration is not implemented yet. Hardware-dependent values must be configured during integration; this prototype is not medical-grade or certified.

## Backend setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Check `http://127.0.0.1:8000/health`. Run tests with `python -m pytest`.

Run the isolated API workflow smoke test with:

```powershell
python scripts/smoke_test.py
```

The API includes device heartbeat/status, sensor event/blink ingestion, calibration, settings, emergency acknowledgement, history/today stats, and demo simulation under `/api/`. The dashboard WebSocket is `/ws/dashboard`. Device status defaults to `OFFLINE` after 15 seconds without a heartbeat; configure `DEVICE_OFFLINE_TIMEOUT_SECONDS` to change it.

Set hardware configuration through environment variables using `.env.example` as a reference. Blank pin, sample-rate, and threshold values are intentionally not guessed. `.env.example` is a template; the application reads the process environment.

The frontend uses React, Vite, TypeScript, Tailwind, lucide-react, and Recharts. Demo-generated sensor events and seeded history are marked with `source: "demo"`. The demo emits timestamped blink sequences with bounded timing jitter but does not connect to hardware or play audio itself; audio IDs identify the DFPlayer mapping. See [RUN.md](RUN.md) for Windows setup and [AGENTS.md](AGENTS.md) for conventions.

Browser captures from the live dashboard verification are in `docs/screenshots/`: [idle](docs/screenshots/idle.png), [WATER detected](docs/screenshots/water-detected.png), [low confidence](docs/screenshots/low-confidence.png), and [emergency overlay](docs/screenshots/emergency-overlay.png).