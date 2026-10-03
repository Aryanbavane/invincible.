# Run BlinkBridge on Windows

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer with npm
- PowerShell 5.1 or PowerShell 7

Python 3.14.7, Node.js 24.21.0, and npm 11.19.0 were used for this build.

## Backend

Open a PowerShell terminal and run:

```powershell
Set-Location "$HOME\OneDrive\Desktop\invincible\blinkbridge"
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
$env:BLINKBRIDGE_DATABASE_PATH = "$PWD\data\blinkbridge.sqlite3"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Leave that terminal open. The API health check is `http://127.0.0.1:8000/health`.

## Frontend

Open a second PowerShell terminal and run:

```powershell
Set-Location "$HOME\OneDrive\Desktop\invincible\blinkbridge"
.\.venv\Scripts\Activate.ps1
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`. The Vite development server proxies API and WebSocket traffic to port 8000.

## Tests and smoke test

From the project root with the virtual environment active:

```powershell
python -m pytest tests -q
python scripts\smoke_test.py
```

The smoke test uses a temporary empty SQLite database and verifies heartbeat, simulated WATER in history, simulated EMERGENCY, acknowledgement, and the acknowledged emergency history entry.

## Hardware note

Do not copy hardware pin, voltage, sampling, or threshold assumptions from this prototype. Configure unknown hardware values during hardware integration. The current speaker and sensor feeds are simulated unless connected through a future ESP32 integration.