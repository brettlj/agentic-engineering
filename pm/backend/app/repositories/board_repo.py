"""SQLite repository for Kanban board persistence.

This module manages the SQLite database lifecycle: schema creation,
user provisioning, and board CRUD. It uses optimistic concurrency via
a board_version column — callers pass an expected version, and the
update fails with BoardVersionConflict if someone else wrote first.

All functions accept a db_path (Path) rather than holding a persistent
connection, because SQLite performs best with short-lived connections
in a web server context.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.app.auth import VALID_USERNAME
from backend.app.models.board import DEFAULT_BOARD, BoardPayload

SCHEMA_VERSION = 1


class BoardVersionConflict(Exception):
    """Raised when a board write fails because the expected version
    does not match the current version in the database.

    The API layer converts this into an HTTP 409 Conflict response.
    """


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row-factory and foreign key support."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the users and kanban_boards tables if they don't exist."""
    connection.executescript(
        """
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
        """
    )


def _ensure_user(connection: sqlite3.Connection, username: str) -> int:
    """Insert the user if missing and return the user's integer ID."""
    connection.execute(
        """
        INSERT INTO users (username)
        VALUES (?)
        ON CONFLICT(username) DO NOTHING
        """,
        (username,),
    )
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Unable to resolve user: {username}")
    return int(row["id"])


def _ensure_user_board(connection: sqlite3.Connection, user_id: int) -> None:
    """Create a default board row for the user if one doesn't exist yet."""
    connection.execute(
        """
        INSERT INTO kanban_boards (user_id, board_json, board_version, schema_version)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, json.dumps(DEFAULT_BOARD), SCHEMA_VERSION),
    )


def initialize_database(db_path: Path) -> None:
    """Set up the database schema and seed the default user/board.

    Called once at application startup. Safe to call multiple times —
    all operations use IF NOT EXISTS / ON CONFLICT DO NOTHING.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as connection:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version == 0:
            _ensure_schema(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        else:
            _ensure_schema(connection)

        user_id = _ensure_user(connection, VALID_USERNAME)
        _ensure_user_board(connection, user_id)
        connection.commit()


def _resolve_user_id(connection: sqlite3.Connection, username: str) -> int:
    """Look up the integer ID for a username. Raises RuntimeError if not found."""
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Unknown username: {username}")
    return int(row["id"])


def read_board(db_path: Path, username: str) -> tuple[dict, int]:
    """Read the board JSON and version number for a user.

    Returns:
        A tuple of (board_dict, version_int). The board_dict is raw JSON
        that can be passed to BoardPayload.model_validate().
    """
    with _connect(db_path) as connection:
        user_id = _resolve_user_id(connection, username)
        _ensure_user_board(connection, user_id)
        row = connection.execute(
            """
            SELECT board_json, board_version
            FROM kanban_boards
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Board row missing after ensure step.")
        board = json.loads(row["board_json"])
        version = int(row["board_version"])
        return board, version


def write_board(
    db_path: Path,
    username: str,
    board: BoardPayload,
    expected_version: int | None,
) -> int:
    """Persist an updated board, enforcing optimistic concurrency.

    When expected_version is provided, the UPDATE uses an atomic
    WHERE board_version = ? clause. If no row is updated (rowcount == 0),
    another writer got there first and BoardVersionConflict is raised.

    Returns the new version number after a successful write.
    """
    with _connect(db_path) as connection:
        user_id = _resolve_user_id(connection, username)
        _ensure_user_board(connection, user_id)

        if expected_version is not None:
            cursor = connection.execute(
                """
                UPDATE kanban_boards
                SET board_json = ?, board_version = board_version + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND board_version = ?
                """,
                (board.model_dump_json(), user_id, expected_version),
            )
            if cursor.rowcount == 0:
                row = connection.execute(
                    "SELECT board_version FROM kanban_boards WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                current_version = int(row["board_version"]) if row else 0
                raise BoardVersionConflict(
                    f"Version mismatch. Expected {expected_version}, found {current_version}."
                )
            connection.commit()
            return expected_version + 1

        row = connection.execute(
            "SELECT board_version FROM kanban_boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Board row missing after ensure step.")
        next_version = int(row["board_version"]) + 1
        connection.execute(
            """
            UPDATE kanban_boards
            SET board_json = ?, board_version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (board.model_dump_json(), next_version, user_id),
        )
        connection.commit()
        return next_version
