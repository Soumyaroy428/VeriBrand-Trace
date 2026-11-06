"""API v1 router."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.brand_vault import router as brand_vault_router
from app.api.v1.submissions import router as submissions_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, prefix="/health", tags=["Health"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
api_v1_router.include_router(brand_vault_router, tags=["Brand Vault"])
api_v1_router.include_router(submissions_router, tags=["Submissions & Privacy Gate"])




