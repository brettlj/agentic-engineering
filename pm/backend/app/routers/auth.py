"""Authentication routes — login, logout, and session status.

This router handles the cookie-based session authentication flow:
1. POST /login — validate credentials, create a session, set a cookie.
2. GET /session — check if the current cookie maps to a valid session.
3. POST /logout — destroy the session and clear the cookie.

Rate limiting is applied to the login endpoint to prevent brute-force
attacks. All session state lives in memory (app.state.sessions).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.app.auth import (
    SESSION_COOKIE_NAME,
    clear_session,
    create_session,
    credentials_are_valid,
    get_username_for_token,
)
from backend.app.dependencies import RateLimiter, Sessions
from backend.app.models.api import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session")
def session(request: Request, sessions: Sessions) -> dict[str, str | bool | None]:
    """Check whether the caller has a valid session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    username = get_username_for_token(sessions, token)
    return {"authenticated": username is not None, "username": username}


@router.post("/login")
def login(
    request: Request,
    payload: LoginRequest,
    sessions: Sessions,
    limiter: RateLimiter,
) -> JSONResponse:
    """Authenticate with username/password and receive a session cookie.

    Returns 429 if too many attempts from the same IP.
    Returns 401 if the credentials are invalid.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
        )
    if not credentials_are_valid(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    state = create_session(sessions, payload.username)
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


@router.post("/logout")
def logout(request: Request, sessions: Sessions) -> JSONResponse:
    """Destroy the current session and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    clear_session(sessions, token)
    response = JSONResponse({"authenticated": False}, status_code=200)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response
