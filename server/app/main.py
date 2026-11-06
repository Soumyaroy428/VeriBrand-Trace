"""FastAPI main application entrypoint for VeriBrand Trace."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1 import api_v1_router
from app.api.v1.health import check_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for MongoDB connection initialization."""
    # Attempt connecting to MongoDB if URL is available
    try:
        if settings.MONGODB_URL:
            await init_db()
            print(f"[INFO] Connected to MongoDB database '{settings.MONGODB_DB_NAME}'.")
    except Exception as e:
        print(f"[WARN] MongoDB startup connection deferred (will connect once user supplies live URL): {e}")
    yield
    # Cleanup connection on shutdown
    try:
        await close_db()
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Explainable Pre-Publication Brand Governance & Human-in-the-Loop Diff Platform API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def root_health():
    """Root health check endpoint."""
    return await check_health()


# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """API root informational endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
