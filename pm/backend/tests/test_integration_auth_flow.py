from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.auth import SESSION_COOKIE_NAME
from backend.app.main import create_app


def _build_frontend_export(frontend_dir: Path) -> None:
    board_dir = frontend_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "index.html").write_text(
        "<html><body><h1>Sign in</h1></body></html>",
        encoding="utf-8",
    )
    (board_dir / "index.html").write_text(
        "<html><body><h1>Kanban Studio</h1></body></html>",
        encoding="utf-8",
    )


def test_protected_board_requires_session_cookie(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)
    client = TestClient(create_app(frontend_dir=frontend_dir, db_path=db_path), follow_redirects=False)

    board = client.get("/board")
    assert board.status_code == 303
    assert board.headers["location"] == "/"

    root = client.get("/")
    assert root.status_code == 200
    assert "Sign in" in root.text


def test_login_and_logout_session_flow(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)
    client = TestClient(create_app(frontend_dir=frontend_dir, db_path=db_path), follow_redirects=False)

    bad_login = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )
    assert bad_login.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login.status_code == 200
    assert SESSION_COOKIE_NAME in login.cookies

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json() == {"authenticated": True, "username": "user"}

    root = client.get("/")
    assert root.status_code == 303
    assert root.headers["location"] == "/board"

    board = client.get("/board")
    assert board.status_code == 200
    assert "Kanban Studio" in board.text

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    session_after = client.get("/api/auth/session")
    assert session_after.status_code == 200
    assert session_after.json() == {"authenticated": False, "username": None}
