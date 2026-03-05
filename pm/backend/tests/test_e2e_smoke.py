import json
import os
import socket
import subprocess
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_ready(url: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url):
                return
        except URLError:
            time.sleep(0.2)
    raise AssertionError(f"Server did not become ready: {url}")


def _start_server(root: Path, port: int, db_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PM_DB_PATH"] = str(db_path)
    return subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        env=env,
    )


def test_e2e_http_smoke(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "data" / "pm.sqlite"

    port = _free_port()
    proc = _start_server(root=root, port=port, db_path=db_path)
    try:
        _wait_for_ready(f"http://127.0.0.1:{port}/health")
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

    second_port = _free_port()
    second_proc = _start_server(root=root, port=second_port, db_path=db_path)
    try:
        _wait_for_ready(f"http://127.0.0.1:{second_port}/health")
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
