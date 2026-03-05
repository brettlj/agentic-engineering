"""Board CRUD routes.

Provides GET and PUT for the user's Kanban board. Both routes require
authentication (enforced by the CurrentUser dependency).

The PUT endpoint uses optimistic concurrency: the client sends the version
it last read, and the server rejects the write (409) if the board was
modified in the meantime.
"""

from fastapi import APIRouter, HTTPException

from backend.app.dependencies import CurrentUser, DbPath
from backend.app.models.board import BoardResponse, BoardUpdateRequest
from backend.app.repositories.board_repo import BoardVersionConflict
from backend.app.services import board_service

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("")
def get_board(username: CurrentUser, db_path: DbPath) -> BoardResponse:
    """Return the current board state and version for the authenticated user."""
    return board_service.get_board(db_path, username)


@router.put("")
def put_board(
    username: CurrentUser,
    db_path: DbPath,
    payload: BoardUpdateRequest,
) -> BoardResponse:
    """Persist an updated board snapshot.

    Raises HTTP 409 if expected_version doesn't match (another write happened first).
    """
    try:
        return board_service.update_board(db_path, username, payload)
    except BoardVersionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
