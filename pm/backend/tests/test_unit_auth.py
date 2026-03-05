from backend.app.auth import (
    clear_session,
    create_session,
    credentials_are_valid,
    get_username_for_token,
)


def test_credentials_validation() -> None:
    assert credentials_are_valid("user", "password")
    assert not credentials_are_valid("user", "wrong")
    assert not credentials_are_valid("wrong", "password")


def test_create_and_clear_session() -> None:
    sessions: dict[str, str] = {}
    state = create_session(sessions, "user")

    assert state["token"] in sessions
    assert get_username_for_token(sessions, state["token"]) == "user"

    clear_session(sessions, state["token"])
    assert get_username_for_token(sessions, state["token"]) is None
