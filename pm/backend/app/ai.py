from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from pydantic import BaseModel, Field, ValidationError

from backend.app.board import BoardPayload

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 15.0


class OpenRouterClientError(Exception):
    pass


class StructuredAIResponse(BaseModel):
    assistant_message: str = Field(min_length=1)
    should_update_board: bool
    board_update: BoardPayload | None = None


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    timeout_seconds: float
    model: str = OPENROUTER_MODEL
    provider_sort: str | None = None
    provider_allow_fallbacks: bool | None = False
    provider_require_parameters: bool = True
    provider_order: tuple[str, ...] = ("siliconflow", "novita", "google")

    @classmethod
    def from_env(cls) -> "OpenRouterConfig":
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required. Set it before starting the backend."
            )

        raw_timeout = os.environ.get("OPENROUTER_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise RuntimeError("OPENROUTER_TIMEOUT_SECONDS must be a positive number.") from exc

        if timeout_seconds <= 0:
            raise RuntimeError("OPENROUTER_TIMEOUT_SECONDS must be a positive number.")

        provider_sort = os.environ.get("OPENROUTER_PROVIDER_SORT", "").strip() or None
        if provider_sort not in {None, "latency", "throughput", "price"}:
            raise RuntimeError(
                "OPENROUTER_PROVIDER_SORT must be one of: latency, throughput, price."
            )

        provider_allow_fallbacks_env = _parse_bool_env("OPENROUTER_PROVIDER_ALLOW_FALLBACKS")
        provider_allow_fallbacks = (
            False if provider_allow_fallbacks_env is None else provider_allow_fallbacks_env
        )

        provider_require_parameters_env = _parse_bool_env(
            "OPENROUTER_PROVIDER_REQUIRE_PARAMETERS"
        )
        provider_require_parameters = (
            True if provider_require_parameters_env is None else provider_require_parameters_env
        )

        provider_order_raw = os.environ.get("OPENROUTER_PROVIDER_ORDER", "").strip()
        if provider_order_raw:
            provider_order = tuple(
                item.strip() for item in provider_order_raw.split(",") if item.strip()
            )
        else:
            provider_order = ("siliconflow", "novita", "google")

        return cls(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            provider_sort=provider_sort,
            provider_allow_fallbacks=provider_allow_fallbacks,
            provider_require_parameters=provider_require_parameters,
            provider_order=provider_order,
        )


class OpenRouterClient:
    def __init__(self, config: OpenRouterConfig) -> None:
        self._config = config

    @classmethod
    def from_env(cls) -> "OpenRouterClient":
        return cls(OpenRouterConfig.from_env())

    @property
    def model(self) -> str:
        return self._config.model

    def _provider_preferences(self) -> dict[str, Any]:
        preferences: dict[str, Any] = {}
        if self._config.provider_sort is not None:
            preferences["sort"] = self._config.provider_sort
        if self._config.provider_allow_fallbacks is not None:
            preferences["allow_fallbacks"] = self._config.provider_allow_fallbacks
        if self._config.provider_require_parameters:
            preferences["require_parameters"] = True
        if self._config.provider_order:
            preferences["order"] = list(self._config.provider_order)
        return preferences

    def connectivity_check(self) -> str:
        return self.chat("What is 2+2? Reply with only the answer.")

    def chat(self, prompt: str) -> str:
        payload = {
            "model": self._config.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = self._post_chat_completions(payload)
        content = _extract_assistant_content(data)
        if not content:
            raise OpenRouterClientError("OpenRouter response did not include assistant content.")
        return content

    def structured_board_chat(
        self,
        board: BoardPayload,
        question: str,
        conversation_history: list[dict[str, str]],
    ) -> StructuredAIResponse:
        messages = build_board_chat_messages(
            board.model_dump(),
            question,
            conversation_history,
        )
        last_issue = "unknown error"
        for _ in range(2):
            payload = {
                "model": self._config.model,
                "messages": messages,
                "provider": self._provider_preferences(),
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "kanban_chat_response",
                        "strict": True,
                        "schema": structured_ai_response_schema(),
                    },
                },
            }
            data = self._post_chat_completions(payload)
            content = _extract_assistant_content(data)
            if not content:
                last_issue = "OpenRouter response did not include assistant content."
                continue

            try:
                structured_payload = _parse_structured_content(content)
                return _normalize_structured_response(structured_payload)
            except OpenRouterClientError as exc:
                last_issue = str(exc)
                continue

        raise OpenRouterClientError(
            "AI returned invalid structured output after retries. "
            "No board changes were applied. Please retry. "
            f"Last issue: {last_issue}"
        )

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **payload,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            OPENROUTER_CHAT_COMPLETIONS_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenRouterClientError(
                f"OpenRouter request failed with status {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise OpenRouterClientError(f"OpenRouter request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise OpenRouterClientError("OpenRouter request timed out.") from exc

        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise OpenRouterClientError("OpenRouter response was not valid JSON.") from exc

        return data


def _extract_assistant_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts).strip()

    return ""


def build_board_chat_messages(
    board: dict[str, Any],
    question: str,
    conversation_history: list[dict[str, str]],
) -> list[dict[str, str]]:
    context_payload = {
        "board": board,
        "conversation_history": conversation_history,
        "user_question": question,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are an assistant for a kanban board application. "
                "Return ONLY valid JSON with exactly these keys: assistant_message, "
                "should_update_board, and board_update. Do not output markdown, code fences, "
                "or any keys outside this schema. "
                "First classify intent internally as one of: create_card, update_card_title, "
                "update_card_details, move_card, reorder_card_within_column, delete_card, "
                "or no_change. "
                "For any non-no_change intent, if the request is unambiguous, set "
                "should_update_board=true and return board_update as a full valid board snapshot. "
                "For no_change or ambiguous requests, set should_update_board=false and "
                "board_update=null, and use assistant_message to ask a precise clarification. "
                "Your output root MUST be a single JSON object (not a string, not an array). "
                "The response MUST start with '{' and end with '}'. "
                "assistant_message must be plain text without markdown or control characters. "
                "Entity resolution order: exact title match, then case-insensitive title match, "
                "then conversation-history references like 'it' or 'that card'. If multiple "
                "entities still match, ask for clarification instead of guessing. "
                "For new cards, generate compact IDs only. Use format card-<suffix> where suffix "
                "is short lowercase alphanumeric (for example card-9 or card-new-1). "
                "Card IDs must be <= 32 characters and never include long random strings. "
                "When building board_update, preserve all unchanged data and enforce invariants: "
                "every cardIds entry exists in cards, no orphaned cards, no duplicate card id in a "
                "column, and every card includes id/title/details. "
                "Operation rules: create appends to target column unless user specifies position; "
                "move removes from source and inserts in target; reorder changes order within target "
                "scope only; update_title/details edits only requested fields; delete removes card "
                "from cards and from every column.cardIds list. "
                "For these unambiguous instruction patterns, you should update the board (set "
                "should_update_board=true): "
                "\"Create a new card titled 'X' in Y with details 'Z'\", "
                "\"Rename card 'X' to 'Y'\", "
                "\"Update details for card 'X' to 'Y'\", "
                "\"Move card 'X' to Y\", "
                "\"In Y, place 'X' before 'Z'\", "
                "\"Delete card 'X'\". "
                "If a referenced card/column is missing, do not update the board and ask for "
                "clarification in assistant_message. "
                "JSON response template: "
                "{\"assistant_message\":\"...\",\"should_update_board\":true,\"board_update\":{...full board...}} "
                "or "
                "{\"assistant_message\":\"...\",\"should_update_board\":false,\"board_update\":null}."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(context_payload, ensure_ascii=True),
        },
    ]


def structured_ai_response_schema() -> dict[str, Any]:
    board_schema = BoardPayload.model_json_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assistant_message": {"type": "string"},
            "should_update_board": {"type": "boolean"},
            "board_update": {"type": ["object", "null"]},
        },
        "required": ["assistant_message", "should_update_board", "board_update"],
        "allOf": [
            {
                "if": {
                    "properties": {"should_update_board": {"const": True}},
                    "required": ["should_update_board"],
                },
                "then": {
                    "properties": {"board_update": board_schema},
                    "required": ["board_update"],
                },
            },
            {
                "if": {
                    "properties": {"should_update_board": {"const": False}},
                    "required": ["should_update_board"],
                },
                "then": {"properties": {"board_update": {"type": "null"}}},
            },
        ],
    }


def _parse_structured_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = _parse_first_json_object(cleaned)

    if not isinstance(parsed, dict):
        raise OpenRouterClientError("OpenRouter structured response must be a JSON object.")
    return parsed


def _parse_first_json_object(content: str) -> dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise OpenRouterClientError("OpenRouter structured response was not valid JSON.")

    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError as exc:
        raise OpenRouterClientError("OpenRouter structured response was not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise OpenRouterClientError("OpenRouter structured response must be a JSON object.")
    return parsed


def _normalize_structured_response(payload: dict[str, Any]) -> StructuredAIResponse:
    assistant_message = payload.get("assistant_message")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise OpenRouterClientError("OpenRouter structured response missing assistant_message.")

    should_update = payload.get("should_update_board")
    if not isinstance(should_update, bool):
        should_update = False

    if not should_update:
        return StructuredAIResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            board_update=None,
        )

    raw_board_update = payload.get("board_update")
    if raw_board_update is None:
        return StructuredAIResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            board_update=None,
        )

    try:
        board_update = BoardPayload.model_validate(raw_board_update)
    except ValidationError:
        # Guardrail: malformed model updates are ignored to avoid blocking chat UX.
        return StructuredAIResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            board_update=None,
        )

    return StructuredAIResponse(
        assistant_message=assistant_message.strip(),
        should_update_board=True,
        board_update=board_update,
    )


def _parse_bool_env(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None

    normalized = raw.strip().lower()
    if normalized == "":
        return None
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(f"{name} must be a boolean value.")
