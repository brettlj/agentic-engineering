from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_root_and_assets_serve_from_frontend_export(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    assets_dir = frontend_dir / "_next" / "static"
    assets_dir.mkdir(parents=True)

    (frontend_dir / "index.html").write_text(
        "<html><head><title>Kanban Studio</title></head><body>Kanban Studio</body></html>",
        encoding="utf-8",
    )
    (assets_dir / "main.js").write_text("console.log('ok');", encoding="utf-8")

    app = create_app(frontend_dir=frontend_dir, db_path=db_path)
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert "Kanban Studio" in root.text

    asset = client.get("/_next/static/main.js")
    assert asset.status_code == 200
    assert "console.log('ok');" in asset.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
