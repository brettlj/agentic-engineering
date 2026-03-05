"""Domain models for the Kanban board.

These models represent the core data structures of the application.
BoardPayload is the central type — it describes a complete board snapshot
with columns and cards, and includes validation rules that enforce
structural integrity (no orphaned cards, no missing references, etc.).

DEFAULT_BOARD provides the initial board state for new users.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


DEFAULT_BOARD: dict = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


class CardPayload(BaseModel):
    """A single Kanban card with a unique ID, title, and details text."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str


class ColumnPayload(BaseModel):
    """A board column that holds an ordered list of card IDs."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    cardIds: list[str]


class BoardPayload(BaseModel):
    """A complete board snapshot: ordered columns plus a card lookup dict.

    The model_validator enforces several structural invariants:
    - At least one column must exist.
    - Column IDs must be unique.
    - Every card ID referenced in a column must exist in the cards dict.
    - The cards dict key must match the card's own id field.
    - Every card must appear in at least one column (no orphans).
    """

    columns: list[ColumnPayload]
    cards: dict[str, CardPayload]

    @model_validator(mode="after")
    def validate_board(self) -> "BoardPayload":
        if not self.columns:
            raise ValueError("Board must include at least one column.")

        seen_column_ids: set[str] = set()
        seen_card_refs: set[str] = set()
        for column in self.columns:
            if column.id in seen_column_ids:
                raise ValueError("Column IDs must be unique.")
            seen_column_ids.add(column.id)
            for card_id in column.cardIds:
                seen_card_refs.add(card_id)
                if card_id not in self.cards:
                    raise ValueError(f"Column references unknown card ID: {card_id}")

        for key, card in self.cards.items():
            if key != card.id:
                raise ValueError("Card map key must match card.id.")

        orphaned_cards = set(self.cards.keys()) - seen_card_refs
        if orphaned_cards:
            raise ValueError("All cards must appear in at least one column.")

        return self


class BoardUpdateRequest(BaseModel):
    """PUT /api/board request body — a board snapshot plus the expected version
    for optimistic concurrency control.
    """

    board: BoardPayload
    expected_version: int | None = Field(default=None, ge=1)


class BoardResponse(BaseModel):
    """Standard response for board endpoints — the board plus its version number."""

    board: BoardPayload
    version: int
