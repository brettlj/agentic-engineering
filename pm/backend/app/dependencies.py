"""Shared FastAPI dependencies for route handlers.

Dependencies are functions that FastAPI calls automatically when a route
handler declares them as parameters. This is FastAPI's dependency injection
system — it eliminates boilerplate and keeps route handlers focused on
their core job.

How it works:
    1. You define a function (e.g., get_current_user) that extracts or
       computes something from the incoming request.
    2. You create a type alias using Annotated[ReturnType, Depends(fn)].
    3. Any route parameter annotated with that type will automatically
       receive the function's return value.

Example:
    @router.get("/api/board")
    def get_board(username: CurrentUser, db_path: DbPath) -> BoardResponse:
        ...

    FastAPI sees CurrentUser = Annotated[str, Depends(get_current_user)]
    and calls get_current_user(request) before invoking get_board().
    If the user isn't authenticated, get_current_user raises HTTPException(401)
    and the route handler never runs.

See: https://fastapi.tiangolo.com/tutorial/dependencies/
"""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from backend.app.ai import OpenRouterClient
from backend.app.auth import (
    SESSION_COOKIE_NAME,
    LoginRateLimiter,
    SessionStore,
    get_username_for_token,
)


# ---------------------------------------------------------------------------
# Dependency functions
#
# Each function receives a Request object and extracts one piece of
# shared application state. FastAPI calls these automatically when a
# route handler parameter uses the corresponding Annotated type alias.
# ---------------------------------------------------------------------------


def get_db_path(request: Request) -> Path:
    """Retrieve the SQLite database path from application state."""
    return request.app.state.db_path


def get_sessions(request: Request) -> SessionStore:
    """Retrieve the in-memory session store from application state."""
    return request.app.state.sessions


def get_ai_client(request: Request) -> OpenRouterClient:
    """Retrieve the OpenRouter API client from application state."""
    return request.app.state.ai_client


def get_login_limiter(request: Request) -> LoginRateLimiter:
    """Retrieve the login rate limiter from application state."""
    return request.app.state.login_limiter


def get_current_user(request: Request) -> str:
    """Validate the session cookie and return the authenticated username.

    Raises HTTPException(401) if the session is missing, expired, or
    invalid. Use this dependency on any route that requires authentication.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    username = get_username_for_token(request.app.state.sessions, token)
    if username is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return username


def get_optional_user(request: Request) -> str | None:
    """Return the authenticated username if a valid session exists, or None.

    Unlike get_current_user, this does NOT raise on missing auth. Useful
    for routes that behave differently for logged-in vs. anonymous users
    (e.g., the root page redirects authenticated users to /board).
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return get_username_for_token(request.app.state.sessions, token)


# ---------------------------------------------------------------------------
# Annotated type aliases
#
# These combine a Python type with a Depends() marker. When you use one
# as a route handler parameter type, FastAPI:
#   1. Calls the dependency function.
#   2. Passes the return value as that parameter.
#
# This is cleaner than writing Depends(...) inline in every handler.
# ---------------------------------------------------------------------------

DbPath = Annotated[Path, Depends(get_db_path)]
"""Inject the SQLite database file path."""

Sessions = Annotated[SessionStore, Depends(get_sessions)]
"""Inject the in-memory session store dict."""

AIClient = Annotated[OpenRouterClient, Depends(get_ai_client)]
"""Inject the configured OpenRouter API client."""

RateLimiter = Annotated[LoginRateLimiter, Depends(get_login_limiter)]
"""Inject the login rate limiter."""

CurrentUser = Annotated[str, Depends(get_current_user)]
"""Inject the authenticated username (raises 401 if not logged in)."""

OptionalUser = Annotated[str | None, Depends(get_optional_user)]
"""Inject the username if logged in, or None if anonymous."""
