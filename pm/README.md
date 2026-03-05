# Project Management MVP

## Local run

Set required environment variables in your shell or `.env` at repo root:

```bash
OPENROUTER_API_KEY=your_key_here
# Optional override (seconds)
OPENROUTER_TIMEOUT_SECONDS=15
# Optional override model (default: openai/gpt-4o-mini)
OPENROUTER_MODEL=openai/gpt-4o-mini
# Optional chat mode:
# - board_snapshot (model returns full board_update snapshot)
# - operation (model returns structured operation; backend applies update server-side)
OPENROUTER_CHAT_MODE=board_snapshot
# Optional provider routing controls (OpenRouter)
OPENROUTER_PROVIDER_REQUIRE_PARAMETERS=true
OPENROUTER_PROVIDER_ALLOW_FALLBACKS=true
# Optional: latency | throughput | price
OPENROUTER_PROVIDER_SORT=
# Optional: comma-separated provider slugs, e.g. "openai,google"
OPENROUTER_PROVIDER_ORDER=
```

Linux:

```bash
./scripts/start-linux.sh
./scripts/stop-linux.sh
```

macOS:

```bash
./scripts/start-mac.sh
./scripts/stop-mac.sh
```

When running:

- Open `http://127.0.0.1:8000` for sign in and board access.
- MVP credentials:
  - Username: `user`
  - Password: `password`
- Board changes persist through backend APIs after login.
- `/board` includes an AI sidebar chat that can optionally apply board updates from structured AI responses.
- AI chat supports a structured operation mode where natural-language assistant messages are preserved while board mutations are applied server-side.
- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/api/hello`
- `GET http://127.0.0.1:8000/api/board` (requires auth cookie)
- `PUT http://127.0.0.1:8000/api/board` (requires auth cookie)
- `GET http://127.0.0.1:8000/api/ai/connectivity` (requires auth cookie; runs live OpenRouter `2+2` check)
- `POST http://127.0.0.1:8000/api/ai/chat` (requires auth cookie; sends board + question + conversation history to AI and may return persisted board update)

## Tests

```bash
docker compose run --rm app uv run --with pytest --with httpx pytest
npm --prefix frontend run test:unit
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm --prefix frontend run test:e2e
```
