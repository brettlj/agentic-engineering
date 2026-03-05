"""AI chat service — orchestrates board state, LLM calls, and persistence.

This is the most complex service in the application. A single chat request
involves multiple steps:

1. Read the current board from the database.
2. Send the board, question, and conversation history to the LLM.
3. If the LLM returns a board mutation, persist it to the database.
4. Return the assistant's message and the (possibly updated) board.

By keeping this orchestration in a service rather than a route handler,
the route stays thin and the logic is easier to test in isolation.
"""

from pathlib import Path

from backend.app.ai import OpenRouterClient, StructuredAIResponse
from backend.app.models.api import AIChatResponse, AIConnectivityResponse
from backend.app.models.board import BoardPayload
from backend.app.repositories.board_repo import read_board, write_board


def check_connectivity(ai_client: OpenRouterClient) -> AIConnectivityResponse:
    """Send a simple prompt to the LLM provider and return the result.

    Used by GET /api/ai/connectivity as a health check for the AI backend.
    """
    output = ai_client.connectivity_check()
    return AIConnectivityResponse(model=ai_client.model, output=output)


def chat(
    db_path: Path,
    username: str,
    ai_client: OpenRouterClient,
    question: str,
    conversation_history: list[dict[str, str]],
) -> AIChatResponse:
    """Process an AI chat request end-to-end.

    Reads the board, calls the LLM, optionally persists an update,
    and returns the response. Raises OpenRouterClientError on LLM
    failures and BoardVersionConflict on concurrent writes.
    """
    board_data, version = read_board(db_path, username)
    current_board = BoardPayload.model_validate(board_data)

    ai_response: StructuredAIResponse = ai_client.structured_board_chat(
        current_board, question, conversation_history,
    )

    if ai_response.should_update_board:
        if ai_response.board_update is None:
            raise ValueError(
                "AI response indicated an update but no board data was supplied."
            )
        updated_version = write_board(
            db_path, username, ai_response.board_update, version,
        )
        return AIChatResponse(
            assistant_message=ai_response.assistant_message,
            should_update_board=True,
            board=ai_response.board_update,
            version=updated_version,
        )

    return AIChatResponse(
        assistant_message=ai_response.assistant_message,
        should_update_board=False,
        board=current_board,
        version=version,
    )
