from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app


def _build_frontend_export(frontend_dir: Path) -> None:
    board_dir = frontend_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "index.html").write_text("<html><body>Sign in</body></html>", encoding="utf-8")
    (board_dir / "index.html").write_text(
        "<html><body>Kanban Studio</body></html>",
        encoding="utf-8",
    )


def test_database_file_is_created_on_startup(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)
    assert not db_path.exists()

    create_app(frontend_dir=frontend_dir, db_path=db_path)

    assert db_path.exists()


def test_authenticated_user_can_read_update_board_with_version_checks(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)
    client = TestClient(create_app(frontend_dir=frontend_dir, db_path=db_path), follow_redirects=False)

    unauthenticated = client.get("/api/board")
    assert unauthenticated.status_code == 401

    login = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert login.status_code == 200

    board_response = client.get("/api/board")
    assert board_response.status_code == 200
    original = board_response.json()
    assert original["version"] == 1
    assert original["board"]["columns"][0]["title"] == "Backlog"

    updated_board = original["board"]
    updated_board["columns"][0]["title"] = "Planned"

    update = client.put(
        "/api/board",
        json={"board": updated_board, "expected_version": original["version"]},
    )
    assert update.status_code == 200
    assert update.json()["version"] == 2
    assert update.json()["board"]["columns"][0]["title"] == "Planned"

    stale = client.put(
        "/api/board",
        json={"board": updated_board, "expected_version": 1},
    )
    assert stale.status_code == 409

    malformed = client.put(
        "/api/board",
        json={"board": {"columns": [], "cards": {}}, "expected_version": 2},
    )
    assert malformed.status_code == 422

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
