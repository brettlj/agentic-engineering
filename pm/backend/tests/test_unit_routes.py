from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_route_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_hello_route_returns_message() -> None:
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI API"}
