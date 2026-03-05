import json
import os
import socket
import subprocess
import time
from http.cookiejar import CookieJar
from pathlib import Path
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
        except Exception:
            time.sleep(0.2)
    raise AssertionError(f"Server did not become ready: {url}")


def _write_test_app_module(module_path: Path) -> None:
    module_path.write_text(
        """
from pathlib import Path
import os

from backend.app.ai import StructuredAIResponse
from backend.app.main import create_app


class StubAIClient:
    model = "stub-model"

    def connectivity_check(self) -> str:
        return "4"

    def structured_board_chat(self, board, question: str, conversation_history):
        if "update" in question.lower():
            updated = board.model_copy(deep=True)
            updated.columns[0].title = "AI Updated"
            return StructuredAIResponse(
                assistant_message="Updated your board.",
                should_update_board=True,
                board_update=updated,
            )

        return StructuredAIResponse(
            assistant_message="No update requested.",
            should_update_board=False,
            board_update=None,
        )


app = create_app(
    db_path=Path(os.environ["PM_DB_PATH"]),
    ai_client=StubAIClient(),
)
""".strip(),
        encoding="utf-8",
    )


def _start_server(root: Path, cwd: Path, port: int, db_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    env["PM_DB_PATH"] = str(db_path)
    env.setdefault("OPENROUTER_API_KEY", "test-key")
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
        cwd=cwd,
        env=env,
    )


def test_e2e_ai_chat_returns_message_and_updates_board_only_when_requested(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    _write_test_app_module(app_dir / "asgi_app.py")

    db_path = tmp_path / "data" / "pm.sqlite"
    port = _free_port()
    proc = _start_server(root=root, cwd=app_dir, port=port, db_path=db_path)

    try:
        _wait_for_ready(f"http://127.0.0.1:{port}/health")
        opener = build_opener(HTTPCookieProcessor(CookieJar()))

        with opener.open(
            Request(
                f"http://127.0.0.1:{port}/api/auth/login",
                data=json.dumps({"username": "user", "password": "password"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ) as response:
            assert response.status == 200

        with opener.open(f"http://127.0.0.1:{port}/api/board") as response:
            original = json.loads(response.read().decode("utf-8"))

        no_update_payload = {
            "question": "Summarize the board status.",
            "conversation_history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
        }
        with opener.open(
            Request(
                f"http://127.0.0.1:{port}/api/ai/chat",
                data=json.dumps(no_update_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ) as response:
            no_update = json.loads(response.read().decode("utf-8"))

        assert no_update["assistant_message"] == "No update requested."
        assert no_update["should_update_board"] is False
        assert no_update["version"] == original["version"]
        assert no_update["board"] == original["board"]

        update_payload = {
            "question": "Please update the first column title.",
            "conversation_history": [],
        }
        with opener.open(
            Request(
                f"http://127.0.0.1:{port}/api/ai/chat",
                data=json.dumps(update_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ) as response:
            updated = json.loads(response.read().decode("utf-8"))

        assert updated["assistant_message"] == "Updated your board."
        assert updated["should_update_board"] is True
        assert updated["board"]["columns"][0]["title"] == "AI Updated"
        assert updated["version"] == original["version"] + 1

        with opener.open(f"http://127.0.0.1:{port}/api/board") as response:
            persisted = json.loads(response.read().decode("utf-8"))
        assert persisted["board"]["columns"][0]["title"] == "AI Updated"
        assert persisted["version"] == original["version"] + 1
    finally:
        proc.terminate()
        proc.wait(timeout=10)
