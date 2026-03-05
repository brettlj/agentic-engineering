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
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str


class ColumnPayload(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    cardIds: list[str]


class BoardPayload(BaseModel):
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
    board: BoardPayload
    expected_version: int | None = Field(default=None, ge=1)


class BoardResponse(BaseModel):
    board: BoardPayload
    version: int
