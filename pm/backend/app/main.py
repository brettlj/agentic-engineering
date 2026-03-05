"""Application factory and static file configuration.

This module creates the FastAPI application instance, attaches shared
state (database path, session store, AI client), includes all API routers,
and sets up static file serving for the Next.js frontend.

The module-level ``app = create_app()`` at the bottom is what uvicorn
discovers and runs when starting the server.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.ai import OpenRouterClient
from backend.app.auth import LoginRateLimiter
from backend.app.dependencies import OptionalUser
from backend.app.repositories.board_repo import initialize_database
from backend.app.routers import ai, auth, board, health

STATIC_DIR = Path(__file__).parent / "static"
STATIC_INDEX = STATIC_DIR / "index.html"
FRONTEND_DIR = STATIC_DIR / "frontend"
DEFAULT_DB_PATH = Path("data/pm.sqlite")


def create_app(
    frontend_dir: Path | None = None,
    db_path: Path | None = None,
    ai_client: OpenRouterClient | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        frontend_dir: Path to the exported Next.js static files.
                      Defaults to backend/app/static/frontend/.
        db_path:      Path to the SQLite database file. Created automatically
                      if it does not exist.
        ai_client:    Pre-configured OpenRouterClient. Defaults to building
                      one from environment variables.
    """
    app = FastAPI(title="Project Management MVP API")

    # --- Shared application state -------------------------------------------
    # These objects live for the lifetime of the process. Dependency functions
    # in dependencies.py read them via request.app.state so that route handlers
    # don't need to access app.state directly.
    app.state.sessions = {}
    app.state.login_limiter = LoginRateLimiter()
    app.state.db_path = db_path or Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH)))
    initialize_database(app.state.db_path)
    app.state.ai_client = ai_client or OpenRouterClient.from_env()

    # --- API routers --------------------------------------------------------
    # Each router handles a group of related endpoints. Routers are defined in
    # separate modules under backend/app/routers/.
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(board.router)
    app.include_router(ai.router)

    # --- Frontend static file serving ---------------------------------------
    # The Next.js frontend is built into static HTML/JS/CSS files. FastAPI
    # serves these directly so the entire app runs as a single Docker container.
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
        def root(username: OptionalUser):
            board_index = resolve_board_index()
            if username and board_index is not None:
                return RedirectResponse(url="/board", status_code=303)
            if root_index.exists():
                return FileResponse(root_index)
            return FileResponse(STATIC_INDEX)

        @app.get("/board")
        @app.get("/board/")
        def board_page(username: OptionalUser):
            board_index = resolve_board_index()
            if not username:
                return RedirectResponse(url="/", status_code=303)
            if board_index is not None:
                return FileResponse(board_index)
            return RedirectResponse(url="/", status_code=303)

        app.mount(
            "/",
            StaticFiles(directory=resolved_frontend_dir, html=True),
            name="frontend",
        )
    else:

        @app.get("/")
        def root() -> FileResponse:
            return FileResponse(STATIC_INDEX)

    return app


app = create_app()
