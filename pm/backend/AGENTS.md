## Backend overview

The backend is a FastAPI service scaffold for the Project Management MVP.

Current Part 7 scope:

- Serves statically exported Next.js frontend assets at `/` when available.
- Falls back to a static hello-world HTML page at `/` if the frontend export is not present.
- Provides API routes:
  - `GET /health`
  - `GET /api/hello`
  - `GET /api/auth/session`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/board`
  - `PUT /api/board`
  - `GET /api/ai/connectivity` (authenticated; live OpenRouter `2+2` check)
  - `POST /api/ai/chat` (authenticated; structured AI response with optional full-board update)
- Uses cookie-based MVP session auth (`pm_session`) with credentials `user` / `password`.
- Protects the board route (`/board`) server-side and redirects unauthenticated users to `/`.
- Initializes SQLite DB on startup and creates tables if the DB file is missing.
- Stores kanban board state per user as JSON text blobs.
- Uses board version checks to support optimistic concurrency on updates.
- Initializes OpenRouter client on startup and fails fast when `OPENROUTER_API_KEY` is not set.
- AI chat requests always include current board JSON, user question, and conversation history.
- AI responses are schema-validated before any board persistence occurs.
- Frontend now consumes board APIs for persisted kanban interactions.
- Runs in a single Docker container.
- Uses multi-stage Docker builds (Node build stage + Python runtime stage).
- Uses `uv` in the Python runtime image for package management.
- Includes test coverage in `backend/tests` for unit, integration, regression, and e2e smoke checks.