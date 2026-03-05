import json

import pytest

from backend.app.ai import (
    OpenRouterClient,
    OpenRouterConfig,
    OpenRouterClientError,
    _normalize_structured_response,
    build_board_chat_messages,
)
from backend.app.board import DEFAULT_BOARD


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
    monkeypatch.setenv("OPENROUTER_PROVIDER_SORT", "throughput")
    monkeypatch.setenv("OPENROUTER_PROVIDER_ALLOW_FALLBACKS", "false")
    monkeypatch.setenv("OPENROUTER_PROVIDER_REQUIRE_PARAMETERS", "true")
    monkeypatch.setenv("OPENROUTER_PROVIDER_ORDER", "openai,google")

    config = OpenRouterConfig.from_env()
    assert config.timeout_seconds == 12.0
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
    assert config.provider_allow_fallbacks is None
    assert config.provider_require_parameters is True
