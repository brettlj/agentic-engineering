"""Health check and greeting routes.

These lightweight endpoints require no authentication and are useful for
monitoring (e.g., Docker HEALTHCHECK, load balancer probes).
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check — returns {"status": "ok"} when the server is running."""
    return {"status": "ok"}


@router.get("/api/hello")
def hello() -> dict[str, str]:
    """Simple greeting endpoint for quick API verification."""
    return {"message": "Hello from FastAPI API"}
