# Database approach (Part 5)

## Scope

This document proposes the SQLite schema and persistence model for the MVP kanban backend.

Goals:

- Support multiple users in the database model.
- Keep exactly one board per user in MVP.
- Persist full board state as JSON text blobs.
- Keep implementation simple and migration-friendly.

## Storage model

- Database engine: SQLite.
- Board persistence style: full-board JSON text blob per user.
- Auth credentials remain hardcoded in code for MVP (`user` / `password`), but DB keeps user records for future expansion.

## Proposed schema

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kanban_boards (
  user_id INTEGER PRIMARY KEY,
  board_json TEXT NOT NULL CHECK (json_valid(board_json)),
  board_version INTEGER NOT NULL DEFAULT 1,
  schema_version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kanban_boards_updated_at
  ON kanban_boards(updated_at);
```

One-board-per-user is enforced by `kanban_boards.user_id` being the primary key.

## JSON blob format

`board_json` stores the full board snapshot as JSON matching the frontend board shape:

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"] },
    { "id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"] }
  ],
  "cards": {
    "card-1": {
      "id": "card-1",
      "title": "Align roadmap themes",
      "details": "Draft quarterly themes with impact statements and metrics."
    },
    "card-2": {
      "id": "card-2",
      "title": "Gather customer signals",
      "details": "Review support tags, sales notes, and churn feedback."
    },
    "card-3": {
      "id": "card-3",
      "title": "Prototype analytics view",
      "details": "Sketch initial dashboard layout and key drill-downs."
    }
  }
}
```

## Read/update model

- Read flow:
  - Resolve `user_id` from authenticated username.
  - `SELECT board_json, board_version FROM kanban_boards WHERE user_id = ?`.
  - Deserialize JSON and return to client.
- Update flow:
  - Validate incoming board payload shape in API layer.
  - Serialize full board JSON.
  - Optional optimistic check: compare caller `expected_version` to `board_version`.
  - `UPDATE kanban_boards SET board_json = ?, board_version = board_version + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?`.
- No patch-level updates in SQL for MVP; full snapshot replaces previous snapshot.

## API contract (Part 6 implementation)

- `GET /api/board`
  - Returns `{ "board": <board_json>, "version": <int> }`.
- `PUT /api/board`
  - Accepts `{ "board": <board_json>, "expected_version": <int|null> }`.
  - If `expected_version` is provided and does not match current `board_version`, returns `409`.
  - On success, persists board and returns updated version.

## Initialization and migration strategy

### Database file creation

- Use a configurable DB path (`PM_DB_PATH`) with a sane default (for example `./data/pm.sqlite` locally and `/app/data/pm.sqlite` in container).
- On startup:
  - Ensure parent directory exists.
  - Open sqlite connection.
  - Enable foreign keys (`PRAGMA foreign_keys = ON`).

### Schema bootstrap

- Use `PRAGMA user_version` for schema versioning.
- If `user_version = 0`:
  - Create `users` and `kanban_boards` tables.
  - Insert initial MVP user row if missing (`username = 'user'`).
  - Insert initial board JSON row for that user if missing.
  - Set `PRAGMA user_version = 1`.

### Future migrations

- Add incremental migration steps keyed by `user_version` (1 -> 2 -> 3 ...).
- Apply migrations inside a transaction during startup.
- Keep each migration small, explicit, and reversible where practical.

## Indexing choices and tradeoffs

### Index choices

- `users.username` unique index (implicit via `UNIQUE`) for auth-to-user lookup.
- `kanban_boards.user_id` primary key index for direct per-user board access.
- `idx_kanban_boards_updated_at` for future admin/debug queries by recency.

### Tradeoffs

Pros:

- Very simple read/write logic.
- Flexible board shape evolution without table redesign.
- Fast enough for MVP scale (one board per user, local SQLite).

Cons:

- No efficient SQL-level partial updates within cards/columns.
- Limited queryability for analytics/reporting inside board content.
- Validation responsibility is pushed to application layer.

These tradeoffs are acceptable for MVP simplicity and can be revisited later.
