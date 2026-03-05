from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.app.auth import VALID_USERNAME
from backend.app.board import DEFAULT_BOARD, BoardPayload

SCHEMA_VERSION = 1


class BoardVersionConflict(Exception):
    pass


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
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
    connection.execute(
        """
        INSERT INTO kanban_boards (user_id, board_json, board_version, schema_version)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, json.dumps(DEFAULT_BOARD), SCHEMA_VERSION),
    )


def initialize_database(db_path: Path) -> None:
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
    row = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Unknown username: {username}")
    return int(row["id"])


def read_board(db_path: Path, username: str) -> tuple[dict, int]:
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
    with _connect(db_path) as connection:
        user_id = _resolve_user_id(connection, username)
        _ensure_user_board(connection, user_id)
        row = connection.execute(
            "SELECT board_version FROM kanban_boards WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Board row missing after ensure step.")

        current_version = int(row["board_version"])
        if expected_version is not None and expected_version != current_version:
            raise BoardVersionConflict(
                f"Version mismatch. Expected {expected_version}, found {current_version}."
            )

        next_version = current_version + 1
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
