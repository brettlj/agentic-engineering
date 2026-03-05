import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app.ai import OpenRouterClient, OpenRouterClientError, StructuredAIResponse
from backend.app.auth import (
    SESSION_COOKIE_NAME,
    clear_session,
    create_session,
    credentials_are_valid,
    get_username_for_token,
)
from backend.app.board import BoardPayload, BoardResponse, BoardUpdateRequest
from backend.app.db import BoardVersionConflict, initialize_database, read_board, write_board

STATIC_DIR = Path(__file__).parent / "static"
STATIC_INDEX = STATIC_DIR / "index.html"
FRONTEND_DIR = STATIC_DIR / "frontend"
DEFAULT_DB_PATH = Path("data/pm.sqlite")


class LoginRequest(BaseModel):
    username: str
    password: str


class AIConnectivityResponse(BaseModel):
    model: str
    output: str


class AIConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AIChatRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_history: list[AIConversationTurn] = Field(default_factory=list)


class AIChatResponse(BaseModel):
    assistant_message: str
    should_update_board: bool
    board: BoardPayload
    version: int


def create_app(
    frontend_dir: Path | None = None,
    db_path: Path | None = None,
    ai_client: OpenRouterClient | None = None,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP API")
    app.state.sessions: dict[str, str] = {}
    app.state.db_path = db_path or Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH)))
    initialize_database(app.state.db_path)
    app.state.ai_client = ai_client or OpenRouterClient.from_env()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/hello")
    def hello() -> dict[str, str]:
        return {"message": "Hello from FastAPI API"}

    @app.get("/api/auth/session")
    def session(request: Request) -> dict[str, str | bool | None]:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        username = get_username_for_token(app.state.sessions, token)
        return {"authenticated": username is not None, "username": username}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest) -> JSONResponse:
        if not credentials_are_valid(payload.username, payload.password):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        state = create_session(app.state.sessions, payload.username)
        response = JSONResponse(
            {"authenticated": True, "username": state["username"]},
            status_code=200,
        )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=state["token"],
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/api/auth/logout")
    def logout(request: Request) -> JSONResponse:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        clear_session(app.state.sessions, token)
        response = JSONResponse({"authenticated": False}, status_code=200)
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return response

    def current_username(request: Request) -> str | None:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        return get_username_for_token(app.state.sessions, token)

    def require_authenticated_username(request: Request) -> str:
        username = current_username(request)
        if username is None:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return username

    @app.get("/api/board")
    def get_board(request: Request) -> BoardResponse:
        username = require_authenticated_username(request)
        board_data, version = read_board(app.state.db_path, username)
        return BoardResponse(board=board_data, version=version)

    @app.put("/api/board")
    def put_board(request: Request, payload: BoardUpdateRequest) -> BoardResponse:
        username = require_authenticated_username(request)
        try:
            version = write_board(
                app.state.db_path,
                username,
                payload.board,
                payload.expected_version,
            )
        except BoardVersionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return BoardResponse(board=payload.board, version=version)

    @app.get("/api/ai/connectivity")
    def ai_connectivity(request: Request) -> AIConnectivityResponse:
        require_authenticated_username(request)
        try:
            output = app.state.ai_client.connectivity_check()
        except OpenRouterClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return AIConnectivityResponse(model=app.state.ai_client.model, output=output)

    @app.post("/api/ai/chat")
    def ai_chat(request: Request, payload: AIChatRequest) -> AIChatResponse:
        username = require_authenticated_username(request)
        board_data, version = read_board(app.state.db_path, username)
        current_board = BoardPayload.model_validate(board_data)
        history = [turn.model_dump() for turn in payload.conversation_history]

        try:
            ai_response: StructuredAIResponse = app.state.ai_client.structured_board_chat(
                current_board,
                payload.question,
                history,
            )
        except OpenRouterClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if ai_response.should_update_board:
            if ai_response.board_update is None:
                raise HTTPException(
                    status_code=502,
                    detail="AI response indicated an update but no board update was supplied.",
                )
            try:
                updated_version = write_board(
                    app.state.db_path,
                    username,
                    ai_response.board_update,
                    version,
                )
            except BoardVersionConflict as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

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

    resolved_frontend_dir = frontend_dir or FRONTEND_DIR

    if resolved_frontend_dir.exists():
        root_index = resolved_frontend_dir / "index.html"
        board_index_nested = resolved_frontend_dir / "board" / "index.html"
        board_index_flat = resolved_frontend_dir / "board.html"

        def resolve_board_index() -> Path | None:
            if board_index_nested.exists():
                return board_index_nested
            if board_index_flat.exists():
                return board_index_flat
            return None

        @app.get("/")
        def root(request: Request):
            board_index = resolve_board_index()
            if current_username(request) and board_index is not None:
                return RedirectResponse(url="/board", status_code=303)
            if root_index.exists():
                return FileResponse(root_index)
            return FileResponse(STATIC_INDEX)

        @app.get("/board")
        @app.get("/board/")
        def board(request: Request):
            board_index = resolve_board_index()
            if not current_username(request):
                return RedirectResponse(url="/", status_code=303)
            if board_index is not None:
                return FileResponse(board_index)
            return RedirectResponse(url="/", status_code=303)

        app.mount("/", StaticFiles(directory=resolved_frontend_dir, html=True), name="frontend")
    else:
        @app.get("/")
        def root() -> FileResponse:
            return FileResponse(STATIC_INDEX)

    return app


app = create_app()
