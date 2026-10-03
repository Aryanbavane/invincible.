# BlinkBridge Engineering Conventions

## Scope and product rules
- BlinkBridge is a 24-hour hackathon prototype for assistive communication using intentional blink patterns.
- Intent detection combines IR eye-state changes with matching EMG Muscle Sensor V3.0 activity; neither sensor alone confirms intent in dual-sensor mode.
- Do not add authentication, machine learning, a chatbot, cloud text-to-speech, or automatic emergency-service calling.
- Never describe the system as medically accurate, medical-grade, or certified.
- Do not assume GPIO pins, voltages, sample rates, or sensor thresholds. Keep unknown hardware values configurable and mark them `TODO — CONFIGURE DURING HARDWARE INTEGRATION`.
- Caregiver alerts are local application/device events only unless an explicitly scoped feature says otherwise.

## Code conventions
- Keep backend code in `backend/`, frontend code in `frontend/`, and tests in `tests/`.
- Use FastAPI, Pydantic, SQLite, and pytest for backend work. Keep database creation limited to the six planned tables.
- Keep command-to-message/audio mappings in backend configuration, not UI code.
- Keep sensor processing deterministic and independently testable; do not add ML or make clinical claims.
- Add focused tests for behavior and API/data contracts. Run the relevant tests after each implementation phase.
- Keep hardware access behind configuration/service boundaries; backend startup and tests must work without connected hardware.

## Run commands
From the `blinkbridge/` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Run tests with:

```powershell
python -m pytest
```

The Live Dashboard is implemented in `frontend/`; Calibration, History, Device, and Settings remain placeholders until separately scoped.