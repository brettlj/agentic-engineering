"""Request and response schemas for API endpoints.

These Pydantic models define the shape of data flowing in and out of the
REST API. FastAPI uses them for:
- Automatic request body validation (returns 422 on invalid input).
- Response serialization and OpenAPI documentation generation.

Models here are "API-level" concerns (HTTP request/response shapes) as
opposed to the domain models in models/board.py.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.models.board import BoardPayload


class LoginRequest(BaseModel):
    """Credentials submitted to POST /api/auth/login."""

    username: str
    password: str


class AIConnectivityResponse(BaseModel):
    """Response from GET /api/ai/connectivity — confirms the LLM provider is reachable."""

    model: str
    output: str


class AIConversationTurn(BaseModel):
    """A single message in the conversation history sent with an AI chat request.

    The conversation_history field in AIChatRequest is a list of these turns,
    alternating between user and assistant roles.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AIChatRequest(BaseModel):
    """Payload for POST /api/ai/chat.

    Includes the user's new question and optionally the prior conversation
    history so the AI has context for follow-up questions.
    """

    question: str = Field(min_length=1)
    conversation_history: list[AIConversationTurn] = Field(default_factory=list)


class AIChatResponse(BaseModel):
    """Response from POST /api/ai/chat.

    Always includes the assistant's text reply and the current board state.
    When should_update_board is True, the board field contains the AI's
    modifications (already persisted to the database).
    """

    assistant_message: str
    should_update_board: bool
    board: BoardPayload
    version: int
