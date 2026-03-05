import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

import pytest


def _should_run_live_llm_tests() -> tuple[bool, str]:
    if os.environ.get("RUN_LIVE_LLM_TESTS") != "1":
        return False, "Set RUN_LIVE_LLM_TESTS=1 to run live LLM operation tests."
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "test-key":
        return False, "OPENROUTER_API_KEY must be set to a real key for live LLM tests."
    return True, ""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_ready(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3):
                return
        except Exception:
            time.sleep(0.2)
    raise AssertionError(f"Server did not become ready: {url}")


def _build_frontend_export(frontend_dir: Path) -> None:
    board_dir = frontend_dir / "board"
    board_dir.mkdir(parents=True, exist_ok=True)
    (frontend_dir / "index.html").write_text("<html><body>Sign in</body></html>", encoding="utf-8")
    (board_dir / "index.html").write_text("<html><body>Kanban Studio</body></html>", encoding="utf-8")


def _write_test_app_module(module_path: Path) -> None:
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


def _http_json(opener, method: str, url: str, payload: dict | None = None, timeout: float = 45.0) -> tuple[int, dict]:
    request = Request(
        url,
        data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return int(exc.code), json.loads(body) if body else {}


@contextmanager
def _live_server(tmp_path: Path):
    should_run, reason = _should_run_live_llm_tests()
    if not should_run:
        pytest.skip(reason)

    root = Path(__file__).resolve().parents[2]
    app_dir = tmp_path / "live_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    frontend_dir = tmp_path / "frontend"
    _build_frontend_export(frontend_dir)
    _write_test_app_module(app_dir / "asgi_app.py")

    db_path = tmp_path / "data" / "pm.sqlite"
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    env["PM_DB_PATH"] = str(db_path)
    env["PM_FRONTEND_PATH"] = str(frontend_dir)
    env.setdefault("OPENROUTER_TIMEOUT_SECONDS", "8")

    proc = subprocess.Popen(
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
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_ready(f"{base_url}/health")
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        status, _ = _http_json(
            opener,
            "POST",
            f"{base_url}/api/auth/login",
            {"username": "user", "password": "password"},
        )
        assert status == 200
        yield base_url, opener
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _get_board(base_url: str, opener) -> dict:
    status, payload = _http_json(opener, "GET", f"{base_url}/api/board")
    assert status == 200
    return payload


def _set_board(base_url: str, opener, board_payload: dict) -> None:
    status, _ = _http_json(
        opener,
        "PUT",
        f"{base_url}/api/board",
        {
            "board": board_payload["board"],
            "expected_version": board_payload["version"],
        },
    )
    assert status == 200


def _column_by_title(board_payload: dict, column_title: str) -> dict:
    for column in board_payload["board"]["columns"]:
        if column["title"] == column_title:
            return column
    raise AssertionError(f"Column not found: {column_title}")


def _find_card_id_by_title(board_payload: dict, title: str) -> str | None:
    for card_id, card in board_payload["board"]["cards"].items():
        if card["title"] == title:
            return card_id
    return None


def _add_card_directly(
    base_url: str,
    opener,
    *,
    title: str,
    details: str,
    column_title: str,
    card_id: str,
) -> None:
    board_payload = _get_board(base_url, opener)
    board_payload["board"]["cards"][card_id] = {
        "id": card_id,
        "title": title,
        "details": details,
    }
    column = _column_by_title(board_payload, column_title)
    if card_id not in column["cardIds"]:
        column["cardIds"].append(card_id)
    _set_board(base_url, opener, board_payload)


def _ask_ai(
    base_url: str,
    opener,
    question: str,
    *,
    require_update: bool,
    attempts: int = 1,
) -> dict:
    last_detail = ""
    for _ in range(attempts):
        try:
            status, payload = _http_json(
                opener,
                "POST",
                f"{base_url}/api/ai/chat",
                {"question": question, "conversation_history": []},
                timeout=50.0,
            )
        except (URLError, TimeoutError, OSError) as exc:
            last_detail = f"Network error: {exc}"
            time.sleep(1)
            continue

        if status == 200 and payload.get("should_update_board") is require_update:
            return payload
        last_detail = json.dumps(payload)
        time.sleep(1)

    raise AssertionError(f"AI chat did not satisfy expectation. Last response: {last_detail}")


def test_live_llm_no_change_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        before = _get_board(base_url, opener)
        _ask_ai(
            base_url,
            opener,
            "Provide a one-sentence board summary only. Do not change the board.",
            require_update=False,
        )
        after = _get_board(base_url, opener)
        assert after["version"] == before["version"]
        assert after["board"] == before["board"]


def test_live_llm_create_card_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        title = f"LLM Ops Create {suffix}"
        details = f"Created details {suffix}"
        _ask_ai(
            base_url,
            opener,
            f"Create a new card titled '{title}' in Backlog with details '{details}'.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        card_id = _find_card_id_by_title(board, title)
        assert card_id is not None
        assert board["board"]["cards"][card_id]["details"] == details


def test_live_llm_update_card_title_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        old_title = f"LLM Ops Rename Source {suffix}"
        new_title = f"LLM Ops Rename Target {suffix}"
        _add_card_directly(
            base_url,
            opener,
            title=old_title,
            details="rename source",
            column_title="Backlog",
            card_id=f"card-rename-{suffix}",
        )
        _ask_ai(
            base_url,
            opener,
            f"Rename card '{old_title}' to '{new_title}'.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        assert _find_card_id_by_title(board, old_title) is None
        assert _find_card_id_by_title(board, new_title) is not None


def test_live_llm_update_card_details_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        title = f"LLM Ops Details {suffix}"
        details = f"Updated details {suffix}"
        card_id = f"card-details-{suffix}"
        _add_card_directly(
            base_url,
            opener,
            title=title,
            details="original details",
            column_title="Backlog",
            card_id=card_id,
        )
        _ask_ai(
            base_url,
            opener,
            f"Update details for card '{title}' to '{details}'.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        assert board["board"]["cards"][card_id]["details"] == details


def test_live_llm_move_card_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        title = f"LLM Ops Move {suffix}"
        card_id = f"card-move-{suffix}"
        _add_card_directly(
            base_url,
            opener,
            title=title,
            details="move me",
            column_title="Backlog",
            card_id=card_id,
        )
        _ask_ai(
            base_url,
            opener,
            f"Move card '{title}' to Review.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        review_ids = _column_by_title(board, "Review")["cardIds"]
        backlog_ids = _column_by_title(board, "Backlog")["cardIds"]
        assert card_id in review_ids
        assert card_id not in backlog_ids


def test_live_llm_reorder_within_column_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        target_title = f"LLM Ops Reorder Target {suffix}"
        anchor_title = f"LLM Ops Reorder Anchor {suffix}"
        target_id = f"card-reorder-target-{suffix}"
        anchor_id = f"card-reorder-anchor-{suffix}"
        _add_card_directly(
            base_url,
            opener,
            title=anchor_title,
            details="anchor",
            column_title="Review",
            card_id=anchor_id,
        )
        _add_card_directly(
            base_url,
            opener,
            title=target_title,
            details="target",
            column_title="Review",
            card_id=target_id,
        )
        _ask_ai(
            base_url,
            opener,
            f"In Review, place '{target_title}' before '{anchor_title}'.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        review_ids = _column_by_title(board, "Review")["cardIds"]
        assert review_ids.index(target_id) < review_ids.index(anchor_id)


def test_live_llm_delete_card_operation(tmp_path: Path) -> None:
    with _live_server(tmp_path) as (base_url, opener):
        suffix = str(int(time.time() * 1000))
        title = f"LLM Ops Delete {suffix}"
        card_id = f"card-delete-{suffix}"
        _add_card_directly(
            base_url,
            opener,
            title=title,
            details="delete me",
            column_title="Backlog",
            card_id=card_id,
        )
        _ask_ai(
            base_url,
            opener,
            f"Delete card '{title}'.",
            require_update=True,
        )
        board = _get_board(base_url, opener)
        assert card_id not in board["board"]["cards"]
        assert all(card_id not in column["cardIds"] for column in board["board"]["columns"])
