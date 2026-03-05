from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib import error, request

from pydantic import BaseModel, Field, ValidationError

from backend.app.board import BoardPayload, CardPayload
from backend.app.prompts import BOARD_SNAPSHOT_SYSTEM_PROMPT, OPERATION_SYSTEM_PROMPT

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_CHAT_MODE = "operation"


class OpenRouterClientError(Exception):
    pass


class StructuredAIResponse(BaseModel):
    assistant_message: str = Field(min_length=1)
    should_update_board: bool
    board_update: BoardPayload | None = None


class StructuredOperation(BaseModel):
    intent: Literal[
        "create_card",
        "update_card_title",
        "update_card_details",
        "move_card",
        "reorder_card_within_column",
        "delete_card",
        "no_change",
    ]
    card_title: str | None = None
    new_title: str | None = None
    new_details: str | None = None
    target_column_title: str | None = None
    before_card_title: str | None = None
    create_title: str | None = None
    create_details: str | None = None


class StructuredOperationResponse(BaseModel):
    assistant_message: str = Field(min_length=1)
    should_update_board: bool
    operation: StructuredOperation | None = None


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    timeout_seconds: float
    model: str = OPENROUTER_MODEL
    chat_mode: str = DEFAULT_CHAT_MODE
    provider_sort: str | None = None
    provider_allow_fallbacks: bool | None = False
    provider_require_parameters: bool = True
    provider_order: tuple[str, ...] = ("openai",)

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

        model = os.environ.get("OPENROUTER_MODEL", OPENROUTER_MODEL).strip() or OPENROUTER_MODEL
        chat_mode = os.environ.get("OPENROUTER_CHAT_MODE", DEFAULT_CHAT_MODE).strip() or DEFAULT_CHAT_MODE
        if chat_mode not in {"board_snapshot", "operation"}:
            raise RuntimeError("OPENROUTER_CHAT_MODE must be 'board_snapshot' or 'operation'.")

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
            provider_order = ("openai",)

        return cls(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            model=model,
            chat_mode=chat_mode,
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
        if self._config.chat_mode == "operation":
            return self._structured_operation_chat(board, question, conversation_history)

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

    def _structured_operation_chat(
        self,
        board: BoardPayload,
        question: str,
        conversation_history: list[dict[str, str]],
    ) -> StructuredAIResponse:
        messages = build_board_operation_messages(
            board.model_dump(),
            question,
            conversation_history,
        )
        last_issue = "unknown error"
        for _ in range(3):
            payload = {
                "model": self._config.model,
                "messages": messages,
                "provider": self._provider_preferences(),
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "kanban_operation_response",
                        "strict": True,
                        "schema": structured_ai_operation_schema(),
                    },
                },
            }
            data = self._post_chat_completions(payload)
            content = _extract_assistant_content(data)
            if not content:
                last_issue = "OpenRouter response did not include assistant content."
                continue

            try:
                operation_payload = _parse_structured_content(content)
                operation_response = _normalize_operation_response(operation_payload)
            except OpenRouterClientError as exc:
                last_issue = str(exc)
                continue

            if not operation_response.should_update_board:
                if _question_requests_action(question) and _looks_like_action_claim(
                    operation_response.assistant_message
                ):
                    last_issue = (
                        "Assistant claimed an action but returned should_update_board=false."
                    )
                    continue
                return StructuredAIResponse(
                    assistant_message=operation_response.assistant_message,
                    should_update_board=False,
                    board_update=None,
                )

            operation = operation_response.operation
            if operation is None:
                return StructuredAIResponse(
                    assistant_message=operation_response.assistant_message,
                    should_update_board=False,
                    board_update=None,
                )

            updated_board = _apply_operation_to_board(board, operation)
            if updated_board is None:
                return StructuredAIResponse(
                    assistant_message=operation_response.assistant_message,
                    should_update_board=False,
                    board_update=None,
                )

            return StructuredAIResponse(
                assistant_message=operation_response.assistant_message,
                should_update_board=True,
                board_update=updated_board,
            )

        raise OpenRouterClientError(
            "AI returned invalid structured output after retries. "
            "No board changes were applied. Please retry. "
            f"Last issue: {last_issue}"
        )

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        {"role": "system", "content": BOARD_SNAPSHOT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context_payload, ensure_ascii=True)},
    ]


def build_board_operation_messages(
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
        {"role": "system", "content": OPERATION_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context_payload, ensure_ascii=True)},
    ]


def structured_ai_operation_schema() -> dict[str, Any]:
    operation_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "intent",
            "card_title",
            "new_title",
            "new_details",
            "target_column_title",
            "before_card_title",
            "create_title",
            "create_details",
        ],
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "create_card",
                    "update_card_title",
                    "update_card_details",
                    "move_card",
                    "reorder_card_within_column",
                    "delete_card",
                    "no_change",
                ],
            },
            "card_title": {"type": ["string", "null"]},
            "new_title": {"type": ["string", "null"]},
            "new_details": {"type": ["string", "null"]},
            "target_column_title": {"type": ["string", "null"]},
            "before_card_title": {"type": ["string", "null"]},
            "create_title": {"type": ["string", "null"]},
            "create_details": {"type": ["string", "null"]},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assistant_message": {"type": "string"},
            "should_update_board": {"type": "boolean"},
            "operation": {"anyOf": [operation_schema, {"type": "null"}]},
        },
        "required": ["assistant_message", "should_update_board", "operation"],
    }


def structured_ai_response_schema() -> dict[str, Any]:
    # board_update is intentionally permissive (any object or null) because
    # OpenRouter strict mode rejects deeply nested schemas with dynamic keys
    # like the cards dict. Validation happens post-hoc in _normalize_structured_response.
    # Prefer the "operation" chat mode (structured_ai_operation_schema) which has
    # a fully specified schema. board_snapshot mode is maintained for compatibility
    # but is not the recommended default.
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assistant_message": {"type": "string"},
            "should_update_board": {"type": "boolean"},
            "board_update": {"type": ["object", "null"]},
        },
        "required": ["assistant_message", "should_update_board", "board_update"],
    }


def _normalize_operation_response(payload: dict[str, Any]) -> StructuredOperationResponse:
    assistant_message = payload.get("assistant_message")
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        raise OpenRouterClientError("OpenRouter structured response missing assistant_message.")

    should_update = payload.get("should_update_board")
    if not isinstance(should_update, bool):
        should_update = False

    raw_operation = payload.get("operation")
    if not should_update:
        return StructuredOperationResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            operation=None,
        )

    if raw_operation is None:
        return StructuredOperationResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            operation=None,
        )

    try:
        operation = StructuredOperation.model_validate(raw_operation)
    except ValidationError:
        return StructuredOperationResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            operation=None,
        )

    if operation.intent == "no_change":
        return StructuredOperationResponse(
            assistant_message=assistant_message.strip(),
            should_update_board=False,
            operation=None,
        )

    return StructuredOperationResponse(
        assistant_message=assistant_message.strip(),
        should_update_board=True,
        operation=operation,
    )


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


def _apply_operation_to_board(
    board: BoardPayload,
    operation: StructuredOperation,
) -> BoardPayload | None:
    working = board.model_copy(deep=True)
    card_id = _resolve_card_id_by_title(working, operation.card_title)
    target_column_index = _resolve_column_index(working, operation.target_column_title)
    before_card_id = _resolve_card_id_by_title(working, operation.before_card_title)

    if operation.intent == "create_card":
        create_title = (operation.create_title or "").strip()
        if not create_title or target_column_index is None:
            return None

        new_card_id = _generate_card_id(working, create_title)
        working.cards[new_card_id] = CardPayload(
            id=new_card_id,
            title=create_title,
            details=(operation.create_details or "").strip(),
        )
        _insert_card_id(working.columns[target_column_index].cardIds, new_card_id, before_card_id)

    elif operation.intent == "update_card_title":
        new_title = (operation.new_title or "").strip()
        if card_id is None or not new_title:
            return None
        card = working.cards.get(card_id)
        if card is None:
            return None
        card.title = new_title

    elif operation.intent == "update_card_details":
        new_details = operation.new_details
        if card_id is None or new_details is None:
            return None
        card = working.cards.get(card_id)
        if card is None:
            return None
        card.details = new_details

    elif operation.intent == "move_card":
        if card_id is None or target_column_index is None:
            return None
        for column in working.columns:
            column.cardIds = [existing_id for existing_id in column.cardIds if existing_id != card_id]
        _insert_card_id(working.columns[target_column_index].cardIds, card_id, before_card_id)

    elif operation.intent == "reorder_card_within_column":
        if card_id is None or target_column_index is None:
            return None
        target_column = working.columns[target_column_index]
        if card_id not in target_column.cardIds:
            return None
        target_column.cardIds = [
            existing_id for existing_id in target_column.cardIds if existing_id != card_id
        ]
        _insert_card_id(target_column.cardIds, card_id, before_card_id)

    elif operation.intent == "delete_card":
        if card_id is None:
            return None
        working.cards.pop(card_id, None)
        for column in working.columns:
            column.cardIds = [existing_id for existing_id in column.cardIds if existing_id != card_id]

    else:
        return None

    try:
        return BoardPayload.model_validate(working.model_dump())
    except ValidationError:
        return None


def _resolve_card_id_by_title(board: BoardPayload, title: str | None) -> str | None:
    if title is None:
        return None
    needle = title.strip()
    if not needle:
        return None

    exact_matches = [card_id for card_id, card in board.cards.items() if card.title == needle]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return None

    lowered = needle.lower()
    casefold_matches = [
        card_id for card_id, card in board.cards.items() if card.title.lower() == lowered
    ]
    if len(casefold_matches) == 1:
        return casefold_matches[0]

    # LLMs sometimes append JSON artifacts to string fields; try prefix matching.
    prefix_matches = [
        card_id
        for card_id, card in board.cards.items()
        if lowered.startswith(card.title.lower()) and len(card.title) >= 2
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    return None


def _resolve_column_index(board: BoardPayload, title: str | None) -> int | None:
    if title is None:
        return None
    needle = title.strip()
    if not needle:
        return None

    exact_matches = [idx for idx, column in enumerate(board.columns) if column.title == needle]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return None

    lowered = needle.lower()
    casefold_matches = [
        idx for idx, column in enumerate(board.columns) if column.title.lower() == lowered
    ]
    if len(casefold_matches) == 1:
        return casefold_matches[0]

    # LLMs sometimes append JSON artifacts to string fields; try prefix matching.
    prefix_matches = [
        idx
        for idx, column in enumerate(board.columns)
        if lowered.startswith(column.title.lower()) and len(column.title) >= 2
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    return None


def _insert_card_id(card_ids: list[str], card_id: str, before_card_id: str | None) -> None:
    if before_card_id is not None and before_card_id in card_ids:
        insert_index = card_ids.index(before_card_id)
        card_ids.insert(insert_index, card_id)
    else:
        card_ids.append(card_id)


def _generate_card_id(board: BoardPayload, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not base:
        base = "new"
    base = base[:20]

    suffix = 1
    for _ in range(1000):
        candidate = f"card-{base}-{suffix}"
        candidate = candidate[:32]
        if candidate not in board.cards:
            return candidate
        suffix += 1
    raise RuntimeError(f"Unable to generate unique card ID for base '{base}' after 1000 attempts.")


def _question_requests_action(question: str) -> bool:
    lowered = question.lower()
    keywords = ("create", "add", "rename", "update", "move", "reorder", "delete")
    return any(keyword in lowered for keyword in keywords)


def _looks_like_action_claim(message: str) -> bool:
    lowered = message.lower()
    patterns = (
        "i will create",
        "i will add",
        "i will rename",
        "i will update",
        "i will move",
        "i will reorder",
        "i will delete",
        "created ",
        "renamed ",
        "updated ",
        "moved ",
        "reordered ",
        "deleted ",
    )
    return any(pattern in lowered for pattern in patterns)


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
