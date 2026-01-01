"""API routes."""

from fastapi import APIRouter
from src.core.config import settings
from src.api.routes.twilio import router as twilio_router
from src.api.routes.kb_admin import router as kb_admin_router
from src.api.routes.analytics import router as analytics_router

router = APIRouter(prefix=settings.API_V1_PREFIX)
router.include_router(twilio_router)
router.include_router(kb_admin_router)
router.include_router(analytics_router)


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "QualifyBot API", "version": "0.1.0"}

