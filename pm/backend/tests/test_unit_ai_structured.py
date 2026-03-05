import json

import pytest

from backend.app.ai import (
    OpenRouterClient,
    OpenRouterConfig,
    OpenRouterClientError,
    StructuredOperation,
    _looks_like_action_claim,
    _apply_operation_to_board,
    _normalize_structured_response,
    build_board_chat_messages,
)
from backend.app.board import BoardPayload, DEFAULT_BOARD


def test_structured_response_accepts_no_update_payload() -> None:
    parsed = _normalize_structured_response(
        {
            "assistant_message": "No changes needed.",
            "should_update_board": False,
            "board_update": None,
        }
    )
    assert parsed.should_update_board is False
    assert parsed.board_update is None


def test_structured_response_ignores_missing_board_update_when_flagged() -> None:
    parsed = _normalize_structured_response(
        {
            "assistant_message": "Applying updates.",
            "should_update_board": True,
            "board_update": None,
        }
    )
    assert parsed.should_update_board is False
    assert parsed.board_update is None


def test_structured_response_ignores_malformed_board_update() -> None:
    parsed = _normalize_structured_response(
        {
            "assistant_message": "No update requested.",
            "should_update_board": True,
            "board_update": {"summary": "not a board"},
        }
    )
    assert parsed.should_update_board is False
    assert parsed.board_update is None


def test_structured_response_requires_assistant_message() -> None:
    with pytest.raises(OpenRouterClientError):
        _normalize_structured_response(
            {
                "should_update_board": False,
                "board_update": None,
            }
        )


def test_prompt_builder_includes_board_history_and_question() -> None:
    history = [{"role": "user", "content": "Move card 1 to Done."}]
    question = "What changed?"
    messages = build_board_chat_messages(DEFAULT_BOARD, question, history)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    context = json.loads(messages[1]["content"])
    assert context["board"]["columns"][0]["id"] == DEFAULT_BOARD["columns"][0]["id"]
    assert context["conversation_history"] == history
    assert context["user_question"] == question


def test_openrouter_config_reads_provider_routing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENROUTER_CHAT_MODE", "operation")
    monkeypatch.setenv("OPENROUTER_PROVIDER_SORT", "throughput")
    monkeypatch.setenv("OPENROUTER_PROVIDER_ALLOW_FALLBACKS", "false")
    monkeypatch.setenv("OPENROUTER_PROVIDER_REQUIRE_PARAMETERS", "true")
    monkeypatch.setenv("OPENROUTER_PROVIDER_ORDER", "openai,google")

    config = OpenRouterConfig.from_env()
    assert config.timeout_seconds == 12.0
    assert config.model == "openai/gpt-4o-mini"
    assert config.chat_mode == "operation"
    assert config.provider_sort == "throughput"
    assert config.provider_allow_fallbacks is False
    assert config.provider_require_parameters is True
    assert config.provider_order == ("openai", "google")


def test_openrouter_provider_preferences_include_require_parameters() -> None:
    client = OpenRouterClient(
        OpenRouterConfig(
            api_key="key",
            timeout_seconds=10.0,
            provider_sort="latency",
            provider_allow_fallbacks=True,
            provider_require_parameters=True,
            provider_order=("openai",),
        )
    )

    preferences = client._provider_preferences()
    assert preferences == {
        "sort": "latency",
        "allow_fallbacks": True,
        "require_parameters": True,
        "order": ["openai"],
    }


def test_openrouter_config_treats_empty_provider_boolean_env_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_PROVIDER_ALLOW_FALLBACKS", "")
    monkeypatch.setenv("OPENROUTER_PROVIDER_REQUIRE_PARAMETERS", "")

    config = OpenRouterConfig.from_env()
    assert config.provider_allow_fallbacks is False
    assert config.provider_require_parameters is True


def test_openrouter_config_rejects_invalid_chat_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_CHAT_MODE", "bad-mode")
    with pytest.raises(RuntimeError):
        OpenRouterConfig.from_env()


def test_apply_operation_create_card_updates_board() -> None:
    board = BoardPayload.model_validate(DEFAULT_BOARD)
    operation = StructuredOperation(
        intent="create_card",
        create_title="New Test Card",
        create_details="Added from unit test.",
        target_column_title="Backlog",
    )
    updated = _apply_operation_to_board(
        board,
        operation,
    )
    assert updated is not None
    titles = [card.title for card in updated.cards.values()]
    assert "New Test Card" in titles


def test_operation_chat_mode_returns_server_applied_update() -> None:
    class FakeClient(OpenRouterClient):
        def _post_chat_completions(self, payload: dict) -> dict:  # type: ignore[override]
            content = json.dumps(
                {
                    "assistant_message": "Created card from operation mode.",
                    "should_update_board": True,
                    "operation": {
                        "intent": "create_card",
                        "create_title": "Operation Card",
                        "create_details": "Operation details",
                        "target_column_title": "Backlog",
                    },
                }
            )
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content,
                        }
                    }
                ]
            }

    config = OpenRouterConfig(
        api_key="test-key",
        timeout_seconds=10.0,
        model="openai/gpt-4o-mini",
        chat_mode="operation",
        provider_order=("openai",),
    )
    client = FakeClient(config)
    response = client.structured_board_chat(
        BoardPayload.model_validate(DEFAULT_BOARD),
        "Create an operation card.",
        [],
    )
    assert response.should_update_board is True
    assert response.board_update is not None
    assert any(card.title == "Operation Card" for card in response.board_update.cards.values())


def test_operation_mode_retries_on_action_claim_with_no_update() -> None:
    class FakeClient(OpenRouterClient):
        def __init__(self, config: OpenRouterConfig) -> None:
            super().__init__(config)
            self._calls = 0

        def _post_chat_completions(self, payload: dict) -> dict:  # type: ignore[override]
            self._calls += 1
            if self._calls == 1:
                content = json.dumps(
                    {
                        "assistant_message": "I will rename the card now.",
                        "should_update_board": False,
                        "operation": None,
                    }
                )
            else:
                content = json.dumps(
                    {
                        "assistant_message": "Renamed the card.",
                        "should_update_board": True,
                        "operation": {
                            "intent": "update_card_title",
                            "card_title": "Align roadmap themes",
                            "new_title": "Aligned roadmap themes",
                            "new_details": None,
                            "target_column_title": None,
                            "before_card_title": None,
                            "create_title": None,
                            "create_details": None,
                        },
                    }
                )
            return {"choices": [{"message": {"role": "assistant", "content": content}}]}

    client = FakeClient(
        OpenRouterConfig(
            api_key="test-key",
            timeout_seconds=10.0,
            model="openai/gpt-4o-mini",
            chat_mode="operation",
            provider_order=("openai",),
        )
    )
    response = client.structured_board_chat(
        BoardPayload.model_validate(DEFAULT_BOARD),
        "Rename card 'Align roadmap themes' to 'Aligned roadmap themes'.",
        [],
    )
    assert response.should_update_board is True
    assert response.board_update is not None
    assert any(
        card.title == "Aligned roadmap themes" for card in response.board_update.cards.values()
    )


def test_action_claim_detector() -> None:
    assert _looks_like_action_claim("I will move the card to Review.")
    assert _looks_like_action_claim("Deleted the card.")
    assert not _looks_like_action_claim("No board changes were made.")
