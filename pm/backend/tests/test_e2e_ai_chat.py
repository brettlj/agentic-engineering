import json
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener

from backend.tests.server_helpers import (
    free_port,
    wait_for_ready,
)


def _write_stub_app_module(module_path: Path) -> None:
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


def _start_stub_server(root, cwd, port, db_path):
    import os
    import subprocess

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
    _write_stub_app_module(app_dir / "asgi_app.py")

    db_path = tmp_path / "data" / "pm.sqlite"
    port = free_port()
    proc = _start_stub_server(root=root, cwd=app_dir, port=port, db_path=db_path)

    try:
        wait_for_ready(f"http://127.0.0.1:{port}/health")
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
