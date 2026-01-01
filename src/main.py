"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import configure_logging, get_logger
from src.api.routes import router
from src.database.connection import init_db, close_db
from src.agent.checkpoint import init_checkpointer, close_checkpointer

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting QualifyBot API")
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e), exc_info=True)
        # Don't fail startup - health check will show degraded status
    
    try:
        await init_checkpointer()
    except Exception as e:
        logger.error("Failed to initialize checkpointer", error=str(e), exc_info=True)
        # Don't fail startup - will fall back to memory checkpointer
    
    logger.info("QualifyBot API started")

    yield

    logger.info("Shutting down QualifyBot API")
    try:
        await close_checkpointer()
    except Exception as e:
        logger.error("Error closing checkpointer", error=str(e))
    
    try:
        await close_db()
    except Exception as e:
        logger.error("Error closing database", error=str(e))
    
    logger.info("QualifyBot API shut down")


app = FastAPI(
    title="QualifyBot API",
    description="IT Support Voice Assistant - Automated IT helpdesk via phone calls",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    response = await call_next(request)
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    This endpoint should be accessible even if database/Redis are not connected.
    Railway uses this to verify the service is running.
    """
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks if all required services (database, Redis) are connected.
    """
    from src.database.connection import engine
    from src.agent.checkpoint import get_checkpointer
    
    checks = {
        "status": "ready",
        "database": "unknown",
        "redis": "unknown",
    }
    
    # Check database connection
    try:
        # Test database connection by executing a simple query
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        checks["status"] = "degraded"
    
    # Check Redis/checkpointer
    try:
        checkpointer = get_checkpointer()
        if checkpointer:
            checks["redis"] = "connected"
        else:
            checks["redis"] = "not_connected"
            checks["status"] = "degraded"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        checks["status"] = "degraded"
    
    status_code = 200 if checks["status"] == "ready" else 503
    return checks


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

