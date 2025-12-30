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
    await init_db()
    await init_checkpointer()
    logger.info("QualifyBot API started")

    yield

    # Shutdown
    logger.info("Shutting down QualifyBot API")
    await close_checkpointer()
    await close_db()
    logger.info("QualifyBot API shut down")


app = FastAPI(
    title="QualifyBot API",
    description="Sales Qualification Voice Bot",
    version="0.1.0",
    lifespan=lifespan,
)


# Add request logging middleware (skip WebSocket connections)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    # Skip WebSocket upgrade requests
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)
    
    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    response = await call_next(request)
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
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
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

