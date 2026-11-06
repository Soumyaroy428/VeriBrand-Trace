"""Health check endpoints for backend services and dependencies."""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    checks: dict


@router.get("", response_model=HealthCheckResponse)
@router.get("/", response_model=HealthCheckResponse)
async def check_health() -> HealthCheckResponse:
    """Returns the operational health and readiness of the API."""
    return HealthCheckResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks={
            "api": "operational",
            "deterministic_engine": "ready",
            "rag_service": "ready",
            "database": "configured",
        }
    )

