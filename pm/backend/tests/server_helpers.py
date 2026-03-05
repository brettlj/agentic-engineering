"""Shared test infrastructure for E2E and live server tests."""

import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_ready(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3):
                return
        except Exception:
            time.sleep(0.2)
    raise AssertionError(f"Server did not become ready: {url}")


def build_frontend_export(frontend_dir: Path) -> None:
    board_dir = frontend_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "index.html").write_text(
        "<html><body>Checking session...</body></html>", encoding="utf-8"
    )
    (board_dir / "index.html").write_text(
        "<html><body>Kanban Studio</body></html>", encoding="utf-8"
    )


def write_test_app_module(module_path: Path) -> None:
    module_path.write_text(
        """
import os
from pathlib import Path

from backend.app.main import create_app

app = create_app(
    frontend_dir=Path(os.environ["PM_FRONTEND_PATH"]),
    db_path=Path(os.environ["PM_DB_PATH"]),
)
""".strip(),
        encoding="utf-8",
    )


def start_server(
    root: Path,
    port: int,
    db_path: Path,
    *,
    app_dir: Path,
    frontend_dir: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.Popen:
    env = os.environ.copy()
    env["PM_DB_PATH"] = str(db_path)
    env["PM_FRONTEND_PATH"] = str(frontend_dir)
    env["PYTHONPATH"] = str(root)
    if extra_env:
        env.update(extra_env)
    return subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "asgi_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=app_dir,
        env=env,
    )
