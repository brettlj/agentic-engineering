import json
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from backend.tests.server_helpers import (
    build_frontend_export,
    free_port,
    start_server,
    wait_for_ready,
    write_test_app_module,
)


def test_e2e_http_smoke(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "data" / "pm.sqlite"
    frontend_dir = tmp_path / "frontend"
    build_frontend_export(frontend_dir)
    app_dir = tmp_path / "smoke_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    write_test_app_module(app_dir / "asgi_app.py")

    port = free_port()
    proc = start_server(root=root, port=port, db_path=db_path, app_dir=app_dir, frontend_dir=frontend_dir)
    try:
        wait_for_ready(f"http://127.0.0.1:{port}/health")
        cookie_jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookie_jar))

        with opener.open(f"http://127.0.0.1:{port}/") as response:
            login_page = response.read().decode("utf-8")

        with opener.open(f"http://127.0.0.1:{port}/api/hello") as response:
            payload = response.read().decode("utf-8")

        assert "Checking session..." in login_page
        assert "Hello from FastAPI API" in payload

        with opener.open(f"http://127.0.0.1:{port}/board") as response:
            assert response.geturl().endswith("/")

        with opener.open(
            Request(
                f"http://127.0.0.1:{port}/api/auth/login",
                data=json.dumps({"username": "user", "password": "password"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ) as response:
            assert response.status == 200

        with opener.open(f"http://127.0.0.1:{port}/api/auth/session") as response:
            session_data = json.loads(response.read().decode("utf-8"))
        assert session_data == {"authenticated": True, "username": "user"}

        with opener.open(f"http://127.0.0.1:{port}/api/board") as response:
            board_payload = json.loads(response.read().decode("utf-8"))
        board_data = board_payload["board"]
        board_data["columns"][0]["title"] = "Persisted Column"

        with opener.open(
            Request(
                f"http://127.0.0.1:{port}/api/board",
                data=json.dumps(
                    {
                        "board": board_data,
                        "expected_version": board_payload["version"],
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="PUT",
            )
        ) as response:
            updated = json.loads(response.read().decode("utf-8"))
        assert updated["version"] == board_payload["version"] + 1

        with opener.open(f"http://127.0.0.1:{port}/") as response:
            assert response.geturl().endswith("/board")

        try:
            opener.open(
                Request(
                    f"http://127.0.0.1:{port}/api/auth/login",
                    data=json.dumps({"username": "user", "password": "wrong"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
            )
            raise AssertionError("Invalid credentials should fail.")
        except HTTPError as exc:
            assert exc.code == 401
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    second_port = free_port()
    second_proc = start_server(root=root, port=second_port, db_path=db_path, app_dir=app_dir, frontend_dir=frontend_dir)
    try:
        wait_for_ready(f"http://127.0.0.1:{second_port}/health")
        second_opener = build_opener(HTTPCookieProcessor(CookieJar()))

        with second_opener.open(
            Request(
                f"http://127.0.0.1:{second_port}/api/auth/login",
                data=json.dumps({"username": "user", "password": "password"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ):
            pass

        with second_opener.open(f"http://127.0.0.1:{second_port}/api/board") as response:
            persisted = json.loads(response.read().decode("utf-8"))
        assert persisted["board"]["columns"][0]["title"] == "Persisted Column"
    finally:
        second_proc.terminate()
        second_proc.wait(timeout=10)
