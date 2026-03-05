# Code Review

Date: 2026-03-05

---

## Critical

### 1. API keys exposed in `.env`

**File:** `.env`, lines 1-6

The `.env` file contains real API keys for OpenAI, Google, Anthropic, Grok, Groq, and OpenRouter. While `.env` is in `.gitignore`, the file exists in the working directory and may have been committed in earlier history. All keys should be rotated and the git history scrubbed if they were ever committed.

### 2. Hardcoded credentials

**File:** `backend/app/auth.py`, lines 22-23

```python
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
```

Acknowledged as MVP design in CLAUDE.md but must be addressed before any deployment beyond local dev. Move to environment variables at minimum.

---

## High

### 3. Container runs as root

**File:** `Dockerfile`

No `USER` directive. The container runs all processes as root, which violates container security best practices. Add a non-root user.

### 4. No Docker health check

**File:** `Dockerfile`

No `HEALTHCHECK` instruction. The `/health` endpoint already exists -- wire it up:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 5. Insecure cookie configuration

**File:** `backend/app/routers/auth.py`, line 66

`secure=False` means the session cookie is sent over plain HTTP. Should be configurable per environment and default to `True` in production.

---

## Medium

### 6. No logging anywhere in the backend

**File:** entire `backend/app/` directory

No `logging` module usage. AI operation failures, auth events, board conflicts, and database errors are all silent. This makes production debugging nearly impossible.

### 7. No rate limiting on API endpoints (except login)

**Files:** `backend/app/routers/board.py`, `backend/app/routers/ai.py`

Authenticated users can call endpoints without limit. The AI chat endpoint is especially expensive since each call invokes an LLM. Add per-user rate limiting.

### 8. Silent AI operation failures

**File:** `backend/app/ai.py`, lines 601-658

When AI-generated board operations fail validation (missing title, bad column index, card not found), the code returns `None` silently. No feedback reaches the user or logs.

### 9. Prefix matching in card/column resolution is too permissive

**File:** `backend/app/ai.py`, lines 686-693, 718-725

If cards are titled "Design UI" and "Design API", a query for "Design" matches both. The prefix matching logic (intended to handle LLM formatting artifacts) can resolve the wrong card.

### 10. Missing field length constraints on Pydantic models

**File:** `backend/app/models/board.py`, lines 69-82

`CardPayload.title`, `CardPayload.details`, and `ColumnPayload.title` have no `max_length`. A client can send arbitrarily large payloads.

### 11. Missing environment variable validation at startup

**File:** `backend/app/main.py`, lines 53-55

`PM_DB_PATH` has a default fallback, but if set to an invalid path the error surfaces only on first DB access rather than at startup.

### 12. Global mutable state for message IDs

**File:** `frontend/src/components/AIChatSidebar.tsx`, line 5

```typescript
let nextMessageId = 0;
```

Module-level mutable counter persists across component unmounts/remounts and can cause duplicate keys. Use `Date.now()` + `Math.random()` like `createId()` in `kanban.ts`.

### 13. Missing accessibility: aria-live on chat messages

**File:** `frontend/src/components/AIChatSidebar.tsx`, lines 65-88

New chat messages are not announced to screen readers. Add `aria-live="polite"` to the messages container.

### 14. Missing form labels in NewCardForm

**File:** `frontend/src/components/NewCardForm.tsx`, lines 27-44

Input fields lack associated `<label>` elements with `htmlFor`. Screen readers cannot associate labels with inputs.

### 15. No CI/CD pipeline

No `.github/workflows/`, `.gitlab-ci.yml`, or equivalent found. No automated testing, linting, or security scanning on commits.

---

## Low

### 16. Synchronous blocking HTTP calls in async framework

**File:** `backend/app/routers/ai.py`, lines 8-12

AI routes use sync handlers with blocking `urllib` calls. FastAPI runs these in a thread pool, but each request blocks a thread for up to 15 seconds. Acknowledged as MVP limitation in comments.

### 17. Hardcoded retry counts

**File:** `backend/app/ai.py`, lines 198, 244

Board snapshot mode retries 2 times, operation mode 3 times. These are magic numbers -- extract to named constants.

### 18. Card ID collision ceiling

**File:** `backend/app/ai.py`, lines 745-751

Card ID generation tries up to 1000 suffixes before raising `RuntimeError`. Unlikely to hit but should fall back to UUID.

### 19. No `.env.example` file

New developers have no reference for required environment variables. Create one with all variables documented with safe placeholder values.

### 20. `.dockerignore` is incomplete

**File:** `.dockerignore`

Missing `data/`, `.env`, `frontend/.next/`, `frontend/out/`. Results in larger build context than necessary.

### 21. In-memory sessions lost on restart

**File:** `backend/app/main.py`, line 51

`app.state.sessions = {}` means all sessions are lost on container restart. Acceptable for MVP but should be documented as a known limitation.

### 22. Missing React.memo on KanbanColumn

**File:** `frontend/src/components/KanbanColumn.tsx`

Callback props are recreated every render, causing unnecessary child re-renders during drag operations. Wrap in `React.memo` and use `useCallback` for handlers.

### 23. Broad ValueError catch in AI router

**File:** `backend/app/routers/ai.py`, lines 49-58

Generic `ValueError` is caught and returned as 502. If a legitimate validation error occurs, it gets misclassified as a server error instead of 422.

### 24. No database connection timeout

**File:** `backend/app/repositories/board_repo.py`

SQLite connections have no explicit timeout. If the database is locked, the connection blocks until SQLite's internal timeout (default 5s).

### 25. Color-only message distinction in AI chat

**File:** `frontend/src/components/AIChatSidebar.tsx`, lines 74-78

User vs Assistant messages are distinguished by background color (blue vs purple). Partially mitigated by "You"/"Assistant" text labels, but could be improved for color-blind users.

---

## Test Coverage Gaps

- No test for session TTL expiry
- No test for board version conflict recovery flow
- No explicit SQL injection prevention tests (code uses parameterized queries, which is correct)
- No tests for AI operation edge cases: deleting non-existent cards, moving to non-existent columns, empty titles
- No unit tests for KanbanCard, KanbanColumn, NewCardForm, or AIChatSidebar components
- No accessibility tests (e.g., jest-axe)

---

## Positive Findings

- Clean Router/Service/Repository separation in the backend
- Parameterized SQL queries throughout (no injection risk)
- `hmac.compare_digest` for timing-safe credential comparison
- `httponly` flag on session cookies (prevents XSS cookie theft)
- Optimistic locking via version numbers on board updates
- No `dangerouslySetInnerHTML` or XSS vectors in the frontend
- Proper TypeScript strict mode with no `any` types
- Good E2E test coverage with Playwright
- Multi-stage Docker build separating frontend and backend
- Well-structured CLAUDE.md with clear architecture documentation
