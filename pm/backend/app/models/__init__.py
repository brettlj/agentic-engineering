"""Pydantic models for the PM application.

This package organizes all data models into two modules:

- board: Domain models for the Kanban board (cards, columns, full board structure).
- api: Request and response schemas for the REST API endpoints.

Pydantic models serve double duty in FastAPI: they validate incoming data
automatically and generate the OpenAPI (Swagger) documentation.
"""
