from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_root_serves_fallback_html_when_frontend_export_missing(tmp_path: Path) -> None:
    app = create_app(
        frontend_dir=Path("/tmp/nonexistent-frontend-export"),
        db_path=tmp_path / "data" / "pm.sqlite",
    )
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello world from the backend scaffold" in response.text
    assert "fetch(\"/api/hello\")" in response.text
