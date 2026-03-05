"""AI chat and connectivity routes.

These routes connect the frontend AI sidebar to the LLM backend.
The connectivity endpoint is a quick smoke test; the chat endpoint
handles the full flow of sending a question, getting a response,
and optionally updating the board.

NOTE: These routes use sync handlers with blocking urllib calls.
FastAPI runs sync handlers in a thread pool, so each in-flight AI
request holds a thread for up to the configured timeout. Acceptable
for MVP single-user use; for concurrent load, convert to async def
with an async HTTP client (e.g., aiohttp or httpx).
"""

from fastapi import APIRouter, HTTPException

from backend.app.ai import OpenRouterClientError
from backend.app.dependencies import AIClient, CurrentUser, DbPath
from backend.app.models.api import AIChatRequest, AIChatResponse, AIConnectivityResponse
from backend.app.repositories.board_repo import BoardVersionConflict
from backend.app.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/connectivity")
def ai_connectivity(username: CurrentUser, ai_client: AIClient) -> AIConnectivityResponse:
    """Quick check that the LLM provider is reachable and responding."""
    try:
        return ai_service.check_connectivity(ai_client)
    except OpenRouterClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/chat")
def ai_chat(
    username: CurrentUser,
    db_path: DbPath,
    ai_client: AIClient,
    payload: AIChatRequest,
) -> AIChatResponse:
    """Send a question to the AI assistant, optionally mutating the board.

    The service reads the current board, sends it with the question to the
    LLM, and persists any returned board changes. Returns the assistant's
    reply and the current (possibly updated) board state.
    """
    history = [turn.model_dump() for turn in payload.conversation_history]
    try:
        return ai_service.chat(
            db_path, username, ai_client, payload.question, history,
        )
    except OpenRouterClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except BoardVersionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
