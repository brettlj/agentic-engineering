"""Data access layer (repositories).

Repositories handle direct database communication — SQL queries,
connection management, and schema setup. They return raw data (dicts,
tuples) rather than HTTP responses.

Business rules and orchestration logic belong in the services layer,
not here. This separation makes it easy to swap out the storage backend
(e.g., replace SQLite with PostgreSQL) without touching business logic.
"""
