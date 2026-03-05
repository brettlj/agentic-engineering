from __future__ import annotations

import hmac
import secrets
import time
from typing import TypedDict

VALID_USERNAME = "user"
VALID_PASSWORD = "password"
SESSION_COOKIE_NAME = "pm_session"
SESSION_TTL_SECONDS = 86400  # 24 hours
MAX_ACTIVE_SESSIONS = 100
LOGIN_RATE_WINDOW_SECONDS = 60
LOGIN_RATE_MAX_ATTEMPTS = 10


class SessionState(TypedDict):
    token: str
    username: str


class SessionEntry(TypedDict):
    username: str
    created_at: float


SessionStore = dict[str, SessionEntry]


class LoginRateLimiter:
    def __init__(
        self,
        window_seconds: int = LOGIN_RATE_WINDOW_SECONDS,
        max_attempts: int = LOGIN_RATE_MAX_ATTEMPTS,
    ) -> None:
        self._window = window_seconds
        self._max = max_attempts
        self._attempts: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        attempts = self._attempts.get(key, [])
        attempts = [t for t in attempts if now - t < self._window]
        self._attempts[key] = attempts
        if len(attempts) >= self._max:
            return False
        attempts.append(now)
        return True


def credentials_are_valid(username: str, password: str) -> bool:
    username_ok = hmac.compare_digest(username, VALID_USERNAME)
    password_ok = hmac.compare_digest(password, VALID_PASSWORD)
    return username_ok and password_ok


def create_session(sessions: SessionStore, username: str) -> SessionState:
    _expire_old_sessions(sessions)
    if len(sessions) >= MAX_ACTIVE_SESSIONS:
        _evict_oldest_session(sessions)
    token = secrets.token_urlsafe(32)
    sessions[token] = {"username": username, "created_at": time.monotonic()}
    return {"token": token, "username": username}


def clear_session(sessions: SessionStore, token: str | None) -> None:
    if token:
        sessions.pop(token, None)


def get_username_for_token(sessions: SessionStore, token: str | None) -> str | None:
    if token is None:
        return None
    entry = sessions.get(token)
    if entry is None:
        return None
    if time.monotonic() - entry["created_at"] > SESSION_TTL_SECONDS:
        sessions.pop(token, None)
        return None
    return entry["username"]


def _expire_old_sessions(sessions: SessionStore) -> None:
    now = time.monotonic()
    expired = [t for t, e in sessions.items() if now - e["created_at"] > SESSION_TTL_SECONDS]
    for t in expired:
        sessions.pop(t, None)


def _evict_oldest_session(sessions: SessionStore) -> None:
    if not sessions:
        return
    oldest_token = min(sessions, key=lambda t: sessions[t]["created_at"])
    sessions.pop(oldest_token, None)
