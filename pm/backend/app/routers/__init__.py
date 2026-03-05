"""API route handlers (routers).

Each module in this package defines a FastAPI APIRouter for a group of
related endpoints. Routers are intentionally thin — they parse the
incoming request, delegate to a service function, and return the response.

This follows the "Bigger Applications" pattern from the FastAPI docs:
https://fastapi.tiangolo.com/tutorial/bigger-applications/

Key conventions:
- Each router sets a prefix (e.g., "/api/board") and tags for grouping.
- Authentication is handled via shared dependencies, not repeated per route.
- Business logic lives in the services/ package, not in route handlers.
"""
