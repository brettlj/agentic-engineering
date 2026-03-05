from __future__ import annotations

import secrets
from typing import TypedDict

VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_COOKIE_NAME = "pm_session"


class SessionState(TypedDict):
    token: str
    username: str


def credentials_are_valid(username: str, password: str) -> bool:
    return username == VALID_USERNAME and password == VALID_PASSWORD


def create_session(sessions: dict[str, str], username: str) -> SessionState:
    token = secrets.token_urlsafe(32)
    sessions[token] = username
    return {"token": token, "username": username}


def clear_session(sessions: dict[str, str], token: str | None) -> None:
    if token:
        sessions.pop(token, None)


def get_username_for_token(sessions: dict[str, str], token: str | None) -> str | None:
    if token is None:
        return None
    return sessions.get(token)
