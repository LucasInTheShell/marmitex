import logging

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class FakeDatabase:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def healthcheck(self) -> None:
        if not self.healthy:
            raise RuntimeError("database unavailable")


def test_health_reports_database_status() -> None:
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unavailable() -> None:
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(healthy=False),  # type: ignore[arg-type]
    )
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}


def test_request_log_does_not_capture_query_string(caplog) -> None:
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    with caplog.at_level(logging.INFO, logger="mavi.api"), TestClient(app) as client:
        client.get("/health?cpf=12345678901")

    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "12345678901" not in messages
    assert "route=/health" in messages

