# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Kanban project management app with an AI sidebar chat. Single-user MVP (hardcoded `user`/`password`). Everything runs in Docker: Python FastAPI backend serves the built Next.js static files and all API routes.

## Commands

### Run the app
```bash
./scripts/start-linux.sh   # builds Docker image and starts at http://127.0.0.1:8000
./scripts/stop-linux.sh
```

### Backend tests (run inside Docker)
```bash
docker compose run --rm app uv run --with pytest --with httpx pytest
# Run a single test file:
docker compose run --rm app uv run --with pytest --with httpx pytest backend/tests/test_unit_routes.py
# Run a single test:
docker compose run --rm app uv run --with pytest --with httpx pytest -k test_health_route_returns_ok
```

### Frontend tests
```bash
npm --prefix frontend run test:unit          # vitest unit tests
npm --prefix frontend run test:unit:watch    # watch mode
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm --prefix frontend run test:e2e  # requires running app
```

### Frontend build/lint
```bash
npm --prefix frontend run build
npm --prefix frontend run lint
```

## Architecture

### Request flow
1. Browser hits `http://127.0.0.1:8000`
2. FastAPI serves the built Next.js static export from `backend/app/static/frontend/`
3. Auth is cookie-based session (in-memory dict on `app.state.sessions`)
4. Board data persists in SQLite at `data/pm.sqlite` (auto-created)

### Backend (`backend/app/`) — Router / Service / Repository pattern
- `main.py` — Slim app factory (`create_app()`). Attaches shared state, includes routers, mounts static files. `app = create_app()` is what uvicorn runs.
- `dependencies.py` — FastAPI `Depends()` functions and `Annotated` type aliases (`CurrentUser`, `DbPath`, `AIClient`, etc.) used by all routers.
- `routers/` — Thin route handlers grouped by domain: `health.py`, `auth.py`, `board.py`, `ai.py`. Each defines an `APIRouter` with a prefix and tags.
- `services/` — Business logic orchestration: `board_service.py` (read/write board), `ai_service.py` (read board + call LLM + persist update).
- `repositories/board_repo.py` — SQLite access with optimistic locking via version numbers. `BoardVersionConflict` raised on conflict → 409 response.
- `models/board.py` — Domain models (`CardPayload`, `ColumnPayload`, `BoardPayload`) with validation. Default board state.
- `models/api.py` — API request/response schemas (`LoginRequest`, `AIChatRequest`, `AIChatResponse`, etc.).
- `ai.py` — `OpenRouterClient` wraps OpenRouter API (via stdlib `urllib`). Two chat modes: `board_snapshot` and `operation`.
- `auth.py` — Session management, credential validation, rate limiting.
- `prompts.py` — LLM system prompt constants.

### AI chat modes
- **`operation`** (default, recommended): AI returns `{assistant_message, should_update_board, operation}` where `operation` describes a single mutation (intent + fields). Backend applies the operation to current board state. Retries up to 3 times.
- **`board_snapshot`**: AI returns `{assistant_message, should_update_board, board_update}` where `board_update` is the full board JSON. Maintained for compatibility but not recommended.

### Frontend (`frontend/src/`)
- Next.js 16 with React 19, Tailwind CSS v4, dnd-kit for drag-and-drop
- `src/lib/kanban.ts` — Pure board logic: `BoardData`/`Card`/`Column` types, `moveCard()`, `createId()`
- `src/components/` — `KanbanColumn`, `KanbanCard`, `KanbanCardPreview`, `NewCardForm`
- Unit tests: vitest + Testing Library in `src/lib/kanban.test.ts`
- E2E tests: Playwright

### Environment variables (`.env` at repo root)
```
OPENROUTER_API_KEY=          # required
OPENROUTER_TIMEOUT_SECONDS=15
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_CHAT_MODE=operation   # or "board_snapshot"
OPENROUTER_PROVIDER_REQUIRE_PARAMETERS=true
OPENROUTER_PROVIDER_ALLOW_FALLBACKS=true
OPENROUTER_PROVIDER_SORT=            # latency | throughput | price
OPENROUTER_PROVIDER_ORDER=           # comma-separated slugs, e.g. "openai,google"
```

## Coding standards

- Keep it simple — no over-engineering, no unnecessary defensive programming
- No emojis anywhere
- When hitting issues: identify root cause with evidence before fixing
- Use latest idiomatic approaches for Python 3.12+ and Next.js/React
