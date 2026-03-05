import pytest
from pydantic import ValidationError

from backend.app.models.board import BoardPayload, DEFAULT_BOARD


def test_board_payload_accepts_default_board() -> None:
    payload = BoardPayload.model_validate(DEFAULT_BOARD)
    assert payload.columns[0].id == "col-backlog"


def test_board_payload_rejects_unknown_card_reference() -> None:
    invalid_board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["missing"]}],
        "cards": {},
    }
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(invalid_board)


def test_board_payload_rejects_orphaned_card() -> None:
    invalid_board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": []}],
        "cards": {"card-1": {"id": "card-1", "title": "T", "details": "D"}},
    }
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(invalid_board)
