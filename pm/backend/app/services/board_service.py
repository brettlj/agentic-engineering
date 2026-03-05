"""Board service — business logic for reading and writing Kanban boards.

This thin service wraps repository calls and returns API-ready response
models. For now the logic is simple, but having this layer means future
features (e.g., board history, webhooks, access control) have a natural
home without cluttering route handlers.
"""

from pathlib import Path

from backend.app.models.board import BoardPayload, BoardResponse, BoardUpdateRequest
from backend.app.repositories.board_repo import read_board, write_board


def get_board(db_path: Path, username: str) -> BoardResponse:
    """Read the current board for a user and return it as a BoardResponse."""
    board_data, version = read_board(db_path, username)
    return BoardResponse(board=board_data, version=version)


def update_board(
    db_path: Path,
    username: str,
    payload: BoardUpdateRequest,
) -> BoardResponse:
    """Write an updated board to the database with optimistic concurrency.

    Raises BoardVersionConflict (from the repository) if the expected
    version does not match. The router catches this and returns HTTP 409.
    """
    version = write_board(db_path, username, payload.board, payload.expected_version)
    return BoardResponse(board=payload.board, version=version)
