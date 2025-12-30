"""API routes."""

from fastapi import APIRouter

from src.core.config import settings
from src.api.routes.twilio import router as twilio_router
from src.api.routes.media_stream import router as media_stream_router
from src.api.routes.test_audio import router as test_audio_router

router = APIRouter(prefix=settings.API_V1_PREFIX)

# Include sub-routers
router.include_router(twilio_router)
router.include_router(media_stream_router)
router.include_router(test_audio_router)


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "QualifyBot API", "version": "0.1.0"}

