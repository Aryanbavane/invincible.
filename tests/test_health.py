from fastapi.testclient import TestClient

from backend.main import app


def test_health_endpoint_initializes_database_and_returns_ok(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "BLINKBRIDGE_DATABASE_PATH", str(tmp_path / "blinkbridge.sqlite3")
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}