# Code Review Report

Comprehensive review of the PM MVP Kanban application. Findings are grouped by priority.

## TODO

### Critical
- [ ] **S1.** Rotate exposed API keys in `.env`; confirm file is not git-tracked

### High
- [x] **B1.** Align default `OPENROUTER_CHAT_MODE` to `operation` in docker-compose.yml, README.md, and CLAUDE.md
- [x] **B2.** Add Docker volume mount for SQLite persistence (`./data:/app/data`)
- [x] **D4.** Add `data/` to `.gitignore`

### Medium — Security
- [x] **S2.** Use `hmac.compare_digest()` for credential comparison in `auth.py`
- [x] **S3.** Add rate limiting on `/api/auth/login`
- [x] **S4.** Add session expiry (TTL) and cap maximum active sessions

### Medium — Backend
- [x] **B4.** Document or fix blocking I/O in AI routes (sync `urllib` in FastAPI handlers)
- [x] **B5.** Fix TOCTOU race in `write_board` — use atomic `UPDATE ... WHERE board_version = ?`
- [x] **B6.** Add empty `backend/tests/__init__.py`
- [x] **Q2.** Extract duplicated test server helpers into shared module
- [x] **D1.** Fix `pyproject.toml` — align dev deps with actual test command; add explicit `pydantic` dep
- [x] **D2.** Add ruff linting/formatting config

### Medium — Frontend
- [x] **F1.** Fix AI chat data loss when pending local saves overlap with AI board updates
- [x] **F2.** Add auto-scroll to latest message in chat sidebar
- [x] **F3.** Fix non-unique React keys in chat message list
- [x] **F4.** Add delete confirmation (or undo) for card removal
- [x] **F6.** Expand frontend test coverage (moveCard edge cases, conflict recovery, network errors)

### Low
- [x] **Q1.** Extract system prompts from inline strings to separate module
- [x] **Q3.** Tighten `board_snapshot` schema (or document why it's permissive)
- [x] **Q4.** Deduplicate identical Linux/macOS start/stop scripts
- [x] **Q5.** Add max-iteration guard to `_generate_card_id`
- [x] **Q6.** Document or remove `board_snapshot` mode in favor of `operation`
- [ ] **F5.** Consolidate `KanbanBoard` state into `useReducer` (deferred — current useState approach is clear at this scale)
- [x] **F7.** Show connection error when login session check fails
- [x] **B3.** Remove redundant `{**payload}` spread in `_post_chat_completions`
- [x] **D3.** Fix Playwright default port from 3000 to 8000
- [x] **DOC1.** Update README/CLAUDE.md to reflect `operation` as default chat mode
- [ ] **DOC2.** Commit or discard uncommitted AGENTS.md changes
- [x] **DOC3.** Add API error response documentation (401, 409, 502)

---

## Priority 1: Security Issues

### S1. API keys committed to version control

**File:** `.env`

The `.env` file contains live API keys for OpenRouter, OpenAI, Google, Anthropic, Grok, and Groq. While `.env` is in `.gitignore`, the file currently exists in the working tree and contains real secrets. If this repo is ever shared, copied, or pushed to a remote with `.env` accidentally included, all keys are exposed.

**Action:** Rotate all keys in `.env`. Confirm `.env` is not tracked by git (`git ls-files .env` should return empty). Consider using a secrets manager or documenting that `.env` must never be committed.

### S2. Credential comparison is not constant-time

**File:** `backend/app/auth.py:17`

```python
return username == VALID_USERNAME and password == VALID_PASSWORD
```

String equality in Python short-circuits, making this vulnerable to timing attacks. For MVP with hardcoded credentials this is low risk, but it's a bad pattern to carry forward.

**Action:** Use `hmac.compare_digest()` for the password comparison if this auth model persists beyond MVP.

### S3. No rate limiting on login endpoint

**File:** `backend/app/main.py:79-97`

The `/api/auth/login` endpoint has no rate limiting. An attacker can brute-force credentials at full speed. Combined with the hardcoded weak password (`password`), this is trivially exploitable.

**Action:** Add basic rate limiting (e.g., per-IP throttle) or at minimum document this as an MVP limitation to fix before any non-local deployment.

### S4. Session tokens never expire

**File:** `backend/app/auth.py`

Sessions are stored in an in-memory dict with no TTL. Once created, a session token is valid forever (until server restart). No maximum session count is enforced either, allowing unbounded memory growth via repeated logins.

**Action:** Add session expiry (e.g., 24h TTL) and cap maximum active sessions.

---

## Priority 2: Bugs and Correctness Issues

### B1. Default chat mode inconsistency across config surfaces

The default chat mode is inconsistent:
- `backend/app/ai.py:17` defaults to `"operation"`
- `docker-compose.yml:11` defaults to `"board_snapshot"`
- `README.md:16` documents `board_snapshot`
- `CLAUDE.md:70` documents `board_snapshot`
- `docs/PLAN.md:68` recommends `operation`

This means running via Docker gives different behavior than running the backend directly.

**Action:** Align all defaults to `"operation"` (the recommended mode per PLAN.md). Update docker-compose.yml, README.md, and CLAUDE.md.

### B2. Database not persisted across Docker container restarts

**File:** `docker-compose.yml`

No volumes are defined. The SQLite database at `data/pm.sqlite` lives inside the container filesystem and is lost when the container is removed (`docker compose down`). This contradicts the persistence promise.

**Action:** Add a volume mount: `volumes: ["./data:/app/data"]` to `docker-compose.yml`.

### B3. `_post_chat_completions` has a redundant spread

**File:** `backend/app/ai.py:296-298`

```python
def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
    payload = {
        **payload,
    }
```

This creates a shallow copy for no reason. No additional keys are merged.

**Action:** Remove the no-op spread or add a comment if this was intentional for future extension.

### B4. Blocking HTTP calls in sync FastAPI handlers

**File:** `backend/app/ai.py:310-311`, `backend/app/main.py:148-162`

The OpenRouter client uses `urllib.request.urlopen` (blocking I/O) inside synchronous route handlers. FastAPI runs sync handlers in a thread pool, but each AI request blocks a thread for up to 15 seconds. Under concurrent load, this exhausts the thread pool and blocks all other sync routes (including `/health`).

**Action:** Either convert AI routes to `async def` with an async HTTP client (e.g., `aiohttp`), or use `asyncio.to_thread()` to explicitly offload. For MVP this is acceptable but should be documented as a scaling limitation.

### B5. `write_board` has a TOCTOU race condition

**File:** `backend/app/db.py:129-155`

The version check (SELECT) and update (UPDATE) are separate statements. Two concurrent requests could both read the same version, both pass the check, and both write, with one silently overwriting the other. SQLite's default locking mitigates this somewhat, but it's not guaranteed under WAL mode.

**Action:** Use a single atomic `UPDATE ... WHERE board_version = ?` and check `cursor.rowcount` instead of a separate SELECT + UPDATE.

### B6. Missing `__init__.py` in `backend/tests/`

**File:** `backend/tests/`

The tests directory has no `__init__.py`. While pytest discovers tests without it, this can cause import issues with namespace packages and confuse some tools.

**Action:** Add an empty `backend/tests/__init__.py`.

---

## Priority 3: Code Quality and Maintainability

### Q1. System prompt in `board_snapshot` mode is 2500+ characters of inline string

**File:** `backend/app/ai.py:368-445`

The system prompt for `build_board_chat_messages` is a massive multi-line string concatenation with dozens of rules. This is hard to read, test, and modify.

**Action:** Move system prompts to a separate file or constant module (e.g., `backend/app/prompts.py`). Consider using a template approach.

### Q2. Duplicated server setup code across E2E/live test files

**Files:** `backend/tests/test_e2e_smoke.py`, `backend/tests/test_e2e_ai_chat.py`, `backend/tests/test_live_llm_operations.py`

All three files independently implement `_free_port()`, `_wait_for_ready()`, `_build_frontend_export()`, `_write_test_app_module()`, and server-start logic. This is ~100 lines duplicated three times.

**Action:** Extract shared test infrastructure into a helper module (e.g., `backend/tests/server_helpers.py`) and import from there.

### Q3. `board_snapshot` schema is permissive

**File:** `backend/app/ai.py:536-546`

```python
"board_update": {"type": ["object", "null"]},
```

The `board_update` field accepts any object with no property constraints. This means the LLM can return arbitrary JSON that won't match `BoardPayload`. The validation happens later in `_normalize_structured_response`, but a stricter schema would catch more issues at the API level.

**Action:** If OpenAI strict mode allows it, add basic property constraints to the schema. Otherwise, document why it's left permissive.

### Q4. Start scripts for Linux and macOS are identical

**Files:** `scripts/start-linux.sh`, `scripts/start-mac.sh`

These files have identical content. Same for the stop scripts.

**Action:** Either use a single `start.sh` or have the platform-specific scripts source a common file.

### Q5. `_generate_card_id` could theoretically loop forever

**File:** `backend/app/ai.py:821-827`

```python
while True:
    candidate = f"card-{base}-{suffix}"
    ...
    suffix += 1
```

If a board somehow had an enormous number of cards with the same base prefix, this loops unboundedly. Extremely unlikely but worth a safety cap.

**Action:** Add a max iteration guard (e.g., bail after 1000 attempts).

### Q6. No Pydantic model for the AI-returned board in `board_snapshot` mode validation

The `structured_ai_response_schema()` leaves `board_update` as `{"type": ["object", "null"]}`, giving the LLM zero structural guidance for the board shape. In contrast, the `operation` mode schema is fully specified. This inconsistency means `board_snapshot` mode is significantly more fragile.

**Action:** If `board_snapshot` mode is to be maintained, add board structure to the schema. If it's deprecated in favor of `operation` mode, document that and consider removing it.

---

## Priority 4: Configuration and DevOps

### D1. `pyproject.toml` test dependencies are optional

**File:** `pyproject.toml:12-15`

```toml
[project.optional-dependencies]
dev = [
  "httpx>=0.28.0",
  "pytest>=8.3.0",
]
```

The Docker test command uses `--with pytest --with httpx` instead of installing the `dev` extras. This means `pyproject.toml` dev dependencies are never actually used. The Pydantic dependency is also missing from `pyproject.toml` — it works because FastAPI pulls it in transitively.

**Action:** Either use the dev extras in the test command or remove the unused optional dependencies. Add `pydantic` as an explicit dependency since the code imports it directly.

### D2. No linting or formatting configured for backend Python code

There is no ruff, black, flake8, mypy, or any other linting/formatting tool configured. The `pyproject.toml` has no `[tool.ruff]` or similar sections.

**Action:** Add ruff configuration for linting and formatting. This is low-effort and high-value for consistency.

### D3. Frontend Playwright config defaults to port 3000

**File:** `frontend/playwright.config.ts:3`

```typescript
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
```

The app runs on port 8000 in Docker. Running E2E tests without setting `PLAYWRIGHT_BASE_URL` would target the wrong port (or a non-running dev server).

**Action:** Change the default to 8000 to match the Docker deployment, or document the required env var more prominently.

### D4. `data/` directory not in `.gitignore`

The SQLite database lives in `data/pm.sqlite`. While `.gitignore` has `db.sqlite3`, it doesn't have `data/` or `*.sqlite`. Running the backend locally outside Docker would create `data/pm.sqlite` which could be accidentally committed.

**Action:** Add `data/` to `.gitignore`.

---

## Priority 4b: Frontend Issues

### F1. AI chat + pending save can cause data loss

**File:** `frontend/src/components/KanbanBoard.tsx`

When the AI returns a board update, `pendingBoardRef.current` is cleared unconditionally. If the user made local changes while the AI was responding, those changes are silently discarded.

**Action:** Merge local pending changes with AI result, or warn the user that their changes were overwritten.

### F2. Chat sidebar does not auto-scroll to latest message

**File:** `frontend/src/components/AIChatSidebar.tsx`

Messages render in a `overflow-y-auto` container but there is no auto-scroll behavior. After several messages, the user must manually scroll to see the AI's latest response.

**Action:** Add a `useEffect` with `scrollIntoView` on the last message element.

### F3. Non-unique React keys in chat messages

**File:** `frontend/src/components/AIChatSidebar.tsx:61`

```tsx
key={`${message.role}-${index}`}
```

Index-based keys cause React to reuse DOM nodes incorrectly when the message list changes. This can produce rendering glitches as the conversation grows.

**Action:** Generate a unique ID for each message when it's created.

### F4. No delete confirmation for cards

**File:** `frontend/src/components/KanbanCard.tsx`

Clicking "Remove" immediately deletes a card with no confirmation. One mis-click permanently destroys data.

**Action:** Add a confirmation prompt or an undo mechanism.

### F5. KanbanBoard has 9 `useState` calls with complex interactions

**File:** `frontend/src/components/KanbanBoard.tsx`

The board component manages columns, cards, versions, loading, errors, save status, and AI state all as independent `useState` calls. State interactions are hard to reason about and prone to getting out of sync.

**Action:** Consider consolidating into a `useReducer` for related state transitions.

### F6. Frontend test coverage is thin

**Files:** `frontend/src/lib/kanban.test.ts`, `frontend/src/components/KanbanBoard.test.tsx`

- `kanban.test.ts` has only 3 tests for `moveCard` — no edge cases, no tests for `createId`
- `KanbanBoard.test.tsx` doesn't test 409 conflict recovery, drag-and-drop, or network failures
- `page.test.tsx` doesn't test session redirect or loading state

**Action:** Expand unit tests for edge cases and error paths.

### F7. Silent error handling in login page

**File:** `frontend/src/app/page.tsx`

Catch blocks in the session check silently swallow errors. If the session check fails due to network issues, the user sees the login form with no indication that something went wrong.

**Action:** Show a connection error message when session check fails.

---

## Priority 5: Documentation Drift

### DOC1. README and CLAUDE.md document `board_snapshot` as default

As noted in B1, the actual backend default is now `operation`, but README and CLAUDE.md still say `board_snapshot`.

### DOC2. AGENTS.md has uncommitted changes

Git status shows `AGENTS.md` is modified but not committed. This may contain important context that could be lost.

### DOC3. No API error response documentation

The README lists endpoints but doesn't document error responses (401, 409, 502). Consumers need to know what error shapes to expect.

---

## Summary of Prioritized Actions

| # | Priority | Item | Effort |
|---|----------|------|--------|
| S1 | Critical | Rotate exposed API keys | Low |
| B1 | High | Align default chat mode across all config | Low |
| B2 | High | Add Docker volume for SQLite persistence | Low |
| D4 | High | Add `data/` to `.gitignore` | Low |
| S2 | Medium | Use constant-time credential comparison | Low |
| S3 | Medium | Add login rate limiting | Medium |
| S4 | Medium | Add session expiry | Medium |
| B4 | Medium | Document or fix blocking I/O in AI routes | Medium |
| B5 | Medium | Fix TOCTOU race in `write_board` | Low |
| B6 | Medium | Add missing `__init__.py` | Low |
| Q2 | Medium | Extract shared test server helpers | Medium |
| D1 | Medium | Fix pyproject.toml dependencies | Low |
| D2 | Medium | Add ruff linting config | Low |
| F1 | Medium | Fix AI chat data loss with pending saves | Medium |
| F2 | Medium | Add auto-scroll to chat sidebar | Low |
| F3 | Medium | Fix non-unique React keys in chat | Low |
| F4 | Medium | Add card delete confirmation | Low |
| F6 | Medium | Expand frontend test coverage | Medium |
| Q1 | Low | Extract system prompts to separate module | Medium |
| Q3 | Low | Tighten board_snapshot schema | Medium |
| Q4 | Low | Deduplicate start/stop scripts | Low |
| Q5 | Low | Add safety cap to card ID generation | Low |
| Q6 | Low | Document or remove board_snapshot mode | Low |
| F5 | Low | Consolidate KanbanBoard state management | Medium |
| F7 | Low | Show error on session check failure | Low |
| B3 | Low | Remove redundant dict spread | Low |
| D3 | Low | Fix Playwright default port | Low |
| DOC1-3 | Low | Fix documentation drift | Low |
