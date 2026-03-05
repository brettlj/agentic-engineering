from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.ai import OpenRouterClientError, StructuredAIResponse
from backend.app.models.board import BoardPayload
from backend.app.main import create_app


class StubAIClient:
    model = "stub-model"

    def __init__(
        self,
        response: StructuredAIResponse | None = None,
        error: OpenRouterClientError | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    def connectivity_check(self) -> str:
        return "4"

    def structured_board_chat(
        self,
        board: BoardPayload,
        question: str,
        conversation_history: list[dict[str, str]],
    ) -> StructuredAIResponse:
        self.calls.append(
            {
                "board": board.model_dump(),
                "question": question,
                "conversation_history": conversation_history,
            }
        )
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise RuntimeError("StubAIClient requires response or error.")
        return self._response


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


def _login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200


def test_ai_chat_no_update_returns_message_and_keeps_board_version(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)
    stub = StubAIClient(
        response=StructuredAIResponse(
            assistant_message="No board update needed.",
            should_update_board=False,
            board_update=None,
        )
    )
    client = TestClient(
        create_app(frontend_dir=frontend_dir, db_path=db_path, ai_client=stub),
        follow_redirects=False,
    )
    _login(client)

    board_before = client.get("/api/board").json()
    response = client.post(
        "/api/ai/chat",
        json={
            "question": "What should I do next?",
            "conversation_history": [{"role": "user", "content": "I need priorities."}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"] == "No board update needed."
    assert payload["should_update_board"] is False
    assert payload["version"] == board_before["version"]

    board_after = client.get("/api/board").json()
    assert board_after["version"] == board_before["version"]
    assert board_after["board"] == board_before["board"]

    assert len(stub.calls) == 1
    assert stub.calls[0]["question"] == "What should I do next?"
    assert stub.calls[0]["conversation_history"] == [{"role": "user", "content": "I need priorities."}]
    assert stub.calls[0]["board"] == board_before["board"]


def test_ai_chat_update_persists_board_snapshot(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)

    current_board_client = TestClient(
        create_app(
            frontend_dir=frontend_dir,
            db_path=db_path,
            ai_client=StubAIClient(
                response=StructuredAIResponse(
                    assistant_message="No update for initial read.",
                    should_update_board=False,
                    board_update=None,
                )
            ),
        ),
        follow_redirects=False,
    )
    _login(current_board_client)
    original = current_board_client.get("/api/board").json()

    updated_board = deepcopy(original["board"])
    updated_board["columns"][0]["title"] = "AI Planned"

    stub = StubAIClient(
        response=StructuredAIResponse(
            assistant_message="Updated your board.",
            should_update_board=True,
            board_update=BoardPayload.model_validate(updated_board),
        )
    )
    client = TestClient(
        create_app(frontend_dir=frontend_dir, db_path=db_path, ai_client=stub),
        follow_redirects=False,
    )
    _login(client)

    response = client.post(
        "/api/ai/chat",
        json={"question": "Rename first column.", "conversation_history": []},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["should_update_board"] is True
    assert payload["board"]["columns"][0]["title"] == "AI Planned"
    assert payload["version"] == original["version"] + 1

    persisted = client.get("/api/board").json()
    assert persisted["board"]["columns"][0]["title"] == "AI Planned"
    assert persisted["version"] == original["version"] + 1


def test_ai_chat_invalid_ai_output_does_not_corrupt_board(tmp_path: Path) -> None:
    frontend_dir = tmp_path / "frontend"
    db_path = tmp_path / "data" / "pm.sqlite"
    _build_frontend_export(frontend_dir)

    stub = StubAIClient(error=OpenRouterClientError("OpenRouter structured response failed validation."))
    client = TestClient(
        create_app(frontend_dir=frontend_dir, db_path=db_path, ai_client=stub),
        follow_redirects=False,
    )
    _login(client)

    before = client.get("/api/board").json()

    failed = client.post(
        "/api/ai/chat",
        json={"question": "Do something", "conversation_history": []},
    )
    assert failed.status_code == 502

    after = client.get("/api/board").json()
    assert after == before

    board_update = deepcopy(before["board"])
    board_update["columns"][0]["title"] = "Manual API update still works"
    put_response = client.put(
        "/api/board",
        json={"board": board_update, "expected_version": before["version"]},
    )
    assert put_response.status_code == 200
    assert put_response.json()["board"]["columns"][0]["title"] == "Manual API update still works"
