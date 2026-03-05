# High level steps for project

After completing each part, pause, provide review and verification instructions, and get explicit user approval before moving to the next part. When approval is given to move to the next part, take a snapshot of the repository in git using git add and git commit with a message indicating the commit is at the end of the current plan part (e.g. 'Part 8 complete')

## Agreed implementation constraints

- Runtime target: local Docker development using a single container.
- Backend stack: FastAPI + SQLite.
- Persistence model: SQLite with JSON text blobs for kanban payloads.
- Auth model: backend session/cookie endpoints with dummy credentials (`user` / `password`) for MVP.
- Scripts target for this phase: Linux and macOS start/stop scripts.
- Testing expectations across implementation parts: unit, integration, regression, and e2e coverage (scope adjusted per part).

## Implemented design decisions (through post-Part 10 hardening)

- Container build strategy:
  - Single runtime container with multi-stage build (Node build stage + Python runtime stage).
  - Next.js static export is copied into FastAPI static assets and served by backend.
- Routing/auth UX:
  - `/` is the login experience.
  - `/board` is the protected kanban route.
  - Unauthenticated access to `/board` redirects to `/`.
  - Authenticated access to `/` redirects to `/board` when board page is available.
- Session/auth details:
  - Session cookie name: `pm_session`.
  - Session store is in-memory for MVP runtime scope.
- Database/bootstrap details:
  - DB path is configurable via `PM_DB_PATH`, defaulting to `data/pm.sqlite`.
  - Startup initialization creates DB/tables and seeds MVP user + initial board if missing.
- Board API contract and concurrency:
  - `GET /api/board` returns `{ board, version }`.
  - `PUT /api/board` accepts `{ board, expected_version }`.
  - `board_version` is used for optimistic concurrency; stale writes return `409`.
- Frontend persistence behavior:
  - Board loads from backend on authenticated page load.
  - UI applies optimistic local updates, queues saves, and serializes save requests.
  - On version conflict, UI reloads latest board and surfaces a clear status message.
- AI connectivity and failure behavior:
  - Backend OpenRouter client is initialized at startup and fails fast when required env vars are missing.
  - AI connectivity endpoint (`GET /api/ai/connectivity`) is authenticated and reports model + simple output.
  - AI request timeout and transport failures are surfaced as backend `502` errors without crashing the app.
- AI structured chat contract:
  - `POST /api/ai/chat` always includes board JSON, user question, and conversation history.
  - Assistant message is always user-facing natural language; board updates are applied only on validated structured outputs.
  - Invalid/malformed AI outputs are treated as no-update and never persisted.
- Sidebar AI UX behavior:
  - Sidebar chat is integrated into `/board` with loading/error states.
  - Chat submissions are serialized while AI operations are in flight to prevent race-condition writes.
  - Valid AI board changes are persisted and immediately reflected in UI state.
- Model/provider/runtime configuration:
- Model is env-configurable via `OPENROUTER_MODEL` (current default: `openai/gpt-4o-mini`).
  - Provider routing is env-configurable (`OPENROUTER_PROVIDER_*`) and used for reliability tuning.
  - Chat strategy is env-configurable via `OPENROUTER_CHAT_MODE`:
    - `board_snapshot`: model returns full board snapshot.
    - `operation`: model returns structured operation, backend applies mutation server-side.
- Structured operation mode hardening:
  - Operation-mode schema was adjusted for OpenAI `response_format` strict requirements.
  - Added light contradiction guard: if assistant text claims an action but returns `should_update_board=false` for an action request, backend retries once more.

### Current recommended runtime config

```bash
# Required
OPENROUTER_API_KEY=your_key_here

# Recommended for current reliability profile
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_CHAT_MODE=operation
OPENROUTER_PROVIDER_ORDER=openai
OPENROUTER_PROVIDER_ALLOW_FALLBACKS=false
OPENROUTER_PROVIDER_REQUIRE_PARAMETERS=true

# Optional
OPENROUTER_TIMEOUT_SECONDS=15
OPENROUTER_PROVIDER_SORT=
```

## Part 1: Plan

### Original

Enrich this document to plan out each of these parts in detail, with substeps listed out as a checklist to be checked off by the agent, and with tests and success critieria for each. Also create an AGENTS.md file inside the frontend directory that describes the existing code there. Ensure the user checks and approves the plan.

### Checklist

- [x] Rewrite `docs/PLAN.md` in place with detailed execution checklists for Parts 1-10.
- [x] Preserve the original part text under an `Original` subsection for each part.
- [x] Include tests and success criteria per part.
- [x] Create `frontend/AGENTS.md` with a high-level architecture summary of the existing frontend.
- [x] Share review instructions and request user approval to proceed to Part 2.

### Tests

- Unit: not applicable for doc-only work.
- Integration: not applicable for doc-only work.
- Regression: verify this plan still includes all original parts and intent.
- E2E: not applicable for doc-only work.

### Success criteria

- `docs/PLAN.md` contains detailed steps for Parts 1-10.
- Every part has `Original`, checklist, tests, and success criteria.
- `frontend/AGENTS.md` exists and accurately captures current architecture at a high level.
- User approves the plan before moving to Part 2.

## Part 2: Scaffolding

### Original

Set up the Docker infrastructure, the backend in backend/ with FastAPI, and write the start and stop scripts in the scripts/ directory. This should serve example static HTML to confirm that a 'hello world' example works running locally and also make an API call.

### Checklist

- [x] Create `backend/` FastAPI scaffold with minimal app and health route.
- [x] Add Dockerfile and docker-related config for a single-container workflow.
- [x] Use `uv` as Python dependency/package manager inside container.
- [x] Add Linux scripts: `scripts/start-linux.sh`, `scripts/stop-linux.sh`.
- [x] Add macOS scripts: `scripts/start-mac.sh`, `scripts/stop-mac.sh`.
- [x] Serve a minimal static HTML hello world page from backend to prove web serving path.
- [x] Add one simple API route (for example `/api/hello`) and verify HTML page can call it.
- [x] Document local run and stop instructions.

### Tests

- Unit:
  - FastAPI route tests for `/health` and `/api/hello`.
- Integration:
  - Container boots and serves HTML + API in one process.
  - Browser or curl check that HTML can fetch API response successfully.
- Regression:
  - Existing frontend directory remains untouched by scaffolding.
  - Start/stop scripts are idempotent (safe to rerun).
- E2E:
  - Smoke test that `GET /` renders hello world and API call result text.

### Success criteria

- Single Docker container starts successfully and serves both static page and API.
- Linux and macOS scripts start/stop reliably.
- Tests for unit/integration/regression/e2e pass for this phase.
- User validates behavior before Part 3.

## Part 3: Add in Frontend

### Original

Now update so that the frontend is statically built and served, so that the app has the demo Kanban board displayed at /. Comprehensive unit and integration tests.

### Checklist

- [x] Build Next.js frontend artifacts in container build process.
- [x] Serve built frontend from FastAPI at `/`.
- [x] Keep static asset routing correct (`/_next/*`, public assets).
- [x] Ensure kanban demo appears exactly at root path.
- [x] Align Docker workflow for rebuilds and local development iteration.

### Tests

- Unit:
  - Existing frontend unit tests still pass.
- Integration:
  - Backend serves built frontend routes and assets without 404s.
- Regression:
  - Existing kanban interactions from demo remain functional after integration.
  - No behavior regression in FastAPI hello/health endpoints unless intentionally replaced.
- E2E:
  - Load `/` and assert kanban heading, five columns, add card flow, drag/drop flow.

### Success criteria

- Root URL shows the existing kanban UI from built frontend.
- Backend static serving is stable in containerized environment.
- Full test suite for this phase passes.
- User approves before Part 4.

## Part 4: Add in a fake user sign in experience

### Original

Now update so that on first hitting /, you need to log in with dummy credentials ("user", "password") in order to see the Kanban, and you can log out. Comprehensive tests.

### Checklist

- [x] Add backend session login endpoint (credential check for `user` / `password`).
- [x] Add backend logout endpoint that clears session cookie.
- [x] Add backend session status endpoint for frontend auth bootstrap.
- [x] Protect kanban-serving path using session state.
- [x] Add frontend login UI and authenticated app shell transitions.
- [x] Add logout control and post-logout redirect.
- [x] Handle invalid credentials with clear error message.

### Tests

- Unit:
  - Auth service tests for credential validation and session helpers.
- Integration:
  - Login sets cookie, session status reflects authenticated state, logout clears state.
  - Protected resource access denied without valid session.
- Regression:
  - Existing kanban behavior remains unchanged after successful login.
  - Session behavior remains stable across page refresh.
- E2E:
  - Unauthenticated user sees login.
  - Valid login reaches kanban.
  - Invalid login stays on login with error.
  - Logout returns to login and blocks protected access.

### Success criteria

- Kanban is inaccessible without login.
- Backend session/cookie auth works end to end.
- Tests pass across all four categories.
- User approves before Part 5.

## Part 5: Database modeling

### Original

Now propose a database schema for the Kanban, saving it as JSON. Document the database approach in docs/ and get user sign off.

### Checklist

- [x] Propose SQLite schema using JSON text blobs for kanban board state.
- [x] Include users table and one-board-per-user constraint for MVP.
- [x] Define migration/init strategy that creates DB and tables if missing.
- [x] Document update/read model, indexing choices, and tradeoffs in `docs/`.
- [x] Include examples of serialized board JSON payloads.
- [x] Request explicit user sign-off before implementation-heavy API wiring.

### Tests

- Unit:
  - Serialization/deserialization helpers for board JSON.
- Integration:
  - DB initialization creates required tables on clean environment.
- Regression:
  - Existing login/session flow unaffected by DB initialization.
- E2E:
  - Not required beyond smoke checks for this design-only/sign-off phase.

### Success criteria

- Schema and JSON blob strategy are documented and approved.
- DB bootstrap plan is concrete and implementable.
- User sign-off obtained before Part 6.

## Part 6: Backend

### Original

Now add API routes to allow the backend to read and change the Kanban for a given user; test this thoroughly with backend unit tests. The database should be created if it doesn't exist.

### Checklist

- [x] Implement DB bootstrap on startup (create file/tables if missing).
- [x] Add authenticated API endpoints to fetch board JSON for logged-in user.
- [x] Add authenticated API endpoints to update board JSON for logged-in user.
- [x] Validate request payload shape and reject malformed board updates.
- [x] Add optimistic update safeguards (e.g., updated timestamp/version check if needed).
- [x] Ensure one-board-per-user behavior is enforced.

### Tests

- Unit:
  - Route/service tests for validation, persistence, and auth checks.
- Integration:
  - Endpoints read/write board data in SQLite JSON text blobs correctly.
  - New DB file creation path works in clean environment.
- Regression:
  - Auth endpoints and session cookie behavior unchanged.
  - Existing static serving still works.
- E2E:
  - Authenticated user edits board through API and sees persisted state on refresh/reload.

### Success criteria

- Board data persists per user via backend APIs.
- DB file/table auto-creation works reliably.
- Test coverage across all four categories passes.
- User approves before Part 7.

## Part 7: Frontend + Backend

### Original

Now have the frontend actually use the backend API, so that the app is a proper persistent Kanban board. Test very throughly.

### Checklist

- [x] Replace in-memory-only board state bootstrap with backend fetch on authenticated load.
- [x] Persist board edits (rename, add, delete, move) through backend update API.
- [x] Add loading, saving, and error UI states that remain simple and clear.
- [x] Ensure local UI state remains responsive with safe reconciliation after save.
- [x] Preserve existing look and feel while shifting data source to backend.

### Tests

- Unit:
  - Frontend state and data transformation tests around API-driven board updates.
- Integration:
  - Frontend API client + backend endpoints verified together.
- Regression:
  - Existing core kanban interactions still behave as before.
  - Authenticated routing and session checks remain correct.
- E2E:
  - Login, board load, card edit/add/move/delete, refresh, and persisted state verification.

### Success criteria

- Kanban is fully persistent through backend API.
- Core UX remains stable and predictable.
- Tests pass across all required categories.
- User approves before Part 8.

## Part 8: AI connectivity

### Original

Now allow the backend to make an AI call via OpenRouter. Test connectivity with a simple "2+2" test and ensure the AI call is working.

### Checklist

- [x] Add backend OpenRouter client using `OPENROUTER_API_KEY` from environment.
- [x] Configure model `openai/gpt-4o-mini` as current default.
- [x] Add simple internal test path or command to run a `2+2` connectivity check.
- [x] Add timeout/error handling for API failures without crashing backend.
- [x] Document required env vars and local test instructions.

### Tests

- Unit:
  - AI client request builder and response parser tests.
- Integration:
  - Live or mocked OpenRouter call path validates request/response handling.
- Regression:
  - Existing board API behavior unaffected when AI feature is idle.
- E2E:
  - Trigger connectivity check and verify expected assistant output includes `4`.

### Success criteria

- Backend can call OpenRouter successfully with configured model.
- Connectivity check is reproducible locally.
- Required tests pass.
- User approves before Part 9.

## Part 9: Structured output with board context

### Original

Now extend the backend call so that it always calls the AI with the JSON of the Kanban board, plus the user's question (and conversation history). The AI should respond with Structured Outputs that includes the response to the user and optionaly an update to the Kanban. Test thoroughly.

### Checklist

- [x] Define and implement structured response schema for AI output.
- [x] Include current board JSON, user question, and prior conversation turns in prompt payload.
- [x] Validate AI response against schema before using it.
- [x] Support optional board update payload and preserve no-update responses.
- [x] Persist board changes only when structured update is valid.
- [x] Add guardrails for malformed or partial AI responses.

### Proposed structured output schema (initial proposal)

```json
{
  "assistant_message": "string",
  "should_update_board": true,
  "board_update": {
    "columns": [
      { "id": "string", "title": "string", "cardIds": ["string"] }
    ],
    "cards": {
      "card-id": { "id": "string", "title": "string", "details": "string" }
    }
  }
}
```

Notes:

- `assistant_message` is always required.
- `should_update_board` is always required.
- `board_update` is required only when `should_update_board` is `true`; otherwise it is `null`.
- `board_update` must represent a full valid board snapshot, not a patch, to simplify validation and persistence.

### Tests

- Unit:
  - Schema validation tests for valid/invalid AI payloads.
  - Prompt composition tests ensure board + history + question are included.
- Integration:
  - End-to-end backend AI flow with mocked model responses for both update and no-update paths.
- Regression:
  - Invalid AI output does not corrupt persisted board.
  - Normal board APIs still function independently of AI.
- E2E:
  - User sends AI request, receives message, and board updates only when schema indicates update.

### Success criteria

- AI structured responses are validated and safely applied.
- Conversation context and board context are always included.
- No malformed AI response can break board persistence.
- User approves before Part 10.

## Part 10: Sidebar AI chat UX

### Original

Now add a beautiful sidebar widget to the UI supporting full AI chat, and allowing the LLM (as it determines) to update the Kanban based on its Structured Outputs. If the AI updates the Kanban, then the UI should refresh automatically.

### Checklist

- [x] Add sidebar chat UI consistent with existing color system and visual style.
- [x] Add chat input/history panel and loading/error states.
- [x] Wire chat submit to backend AI endpoint.
- [x] Render assistant messages from structured output.
- [x] Apply board updates from structured output and refresh UI state automatically.
- [x] Prevent submitting a new chat message while a prior AI-triggered board update is still in progress (single in-flight action to avoid race conditions).
- [x] Keep UX responsive during AI request and persistence operations.

### Tests

- Unit:
  - Chat UI state transitions and message rendering tests.
- Integration:
  - Frontend chat client + backend structured AI endpoint behavior.
  - In-flight update gating blocks additional submits until board update completes.
- Regression:
  - Existing kanban interactions remain stable with chat mounted.
  - Non-AI board edits continue to persist correctly.
- E2E:
  - Login, open sidebar, send prompt, receive message, optional board change reflected immediately and persisted on refresh.
  - Attempting to submit a second prompt during board update is prevented until update settles.

### Success criteria

- Sidebar chat is functional, polished, and integrated with existing UI.
- AI-driven board updates are applied safely and automatically reflected.
- Chat submission is serialized during board updates, preventing race-condition writes.
- Full test matrix passes.
- User signs off on completed MVP.