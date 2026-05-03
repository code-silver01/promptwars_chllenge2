"""
health.py — Health Check Endpoint
===================================
Provides a lightweight health-check route for Cloud Run readiness
probes and monitoring dashboards.
"""

from fastapi import APIRouter

# ── Router instance with OpenAPI metadata ────────────────────
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns the service health status and version.",
    response_description="JSON object with status and version fields.",
)
async def health_check() -> dict:
    """
    Lightweight health-check endpoint.

    Used by:
      • Cloud Run readiness/liveness probes
      • Monitoring dashboards (UptimeRobot, etc.)
      • CI/CD smoke tests
    """
    return {
        "status": "ok",
        "version": "1.0.0",
    }
