"""Test endpoints for audio processing pipeline."""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src.core.logging import get_logger
from src.agent.orchestrator import qualification_orchestrator
from src.services.tts_service import tts_service
from src.services.audio_converter import audio_converter

logger = get_logger(__name__)

router = APIRouter(prefix="/test-audio", tags=["test-audio"])


class TestAudioRequest(BaseModel):
    """Request model for testing audio processing."""
    user_text: str
    call_sid: str = "TEST-CALL-SID"


class TestAudioResponse(BaseModel):
    """Response model for audio processing test."""
    user_text: str
    agent_response: str
    mp3_audio_size: int
    pcmu_audio_size: int


@router.post("/process", response_model=TestAudioResponse)
async def test_audio_processing(
    request: TestAudioRequest,
    background_tasks: BackgroundTasks,
):
    """
    Test the full audio processing pipeline.

    This endpoint simulates:
    1. User speech transcription (input text)
    2. LangGraph processing
    3. TTS generation
    4. Audio format conversion (MP3 → PCMU)
    """
    logger.info("Testing audio processing pipeline", user_text=request.user_text[:50])

    # Step 1: Process user response with LangGraph (simulates STT transcription)
    result = await qualification_orchestrator.process_user_response(
        call_sid=request.call_sid,
        user_text=request.user_text,
        session_id=request.call_sid,
    )

    agent_response = result.get("response", "I understand.")
    is_complete = result.get("is_complete", False)

    logger.info(
        "LangGraph processing complete",
        agent_response=agent_response[:50],
        is_complete=is_complete,
    )

    # Step 2: Generate TTS audio
    mp3_audio = tts_service.generate_audio(agent_response)

    # Step 3: Convert MP3 → PCMU for Twilio Media Streams
    pcmu_audio = audio_converter.mp3_to_pcmu(mp3_audio)

    logger.info(
        "Audio conversion complete",
        mp3_size=len(mp3_audio),
        pcmu_size=len(pcmu_audio),
    )

    return TestAudioResponse(
        user_text=request.user_text,
        agent_response=agent_response,
        mp3_audio_size=len(mp3_audio),
        pcmu_audio_size=len(pcmu_audio),
    )


@router.post("/simple-test")
async def simple_audio_test():
    """Simple test to verify audio conversion works."""
    logger.info("Running simple audio test")

    # Generate a short TTS audio
    mp3_audio = tts_service.generate_audio("Hello, this is a test.")

    # Convert to PCMU
    pcmu_audio = audio_converter.mp3_to_pcmu(mp3_audio)

    return {
        "status": "success",
        "mp3_size": len(mp3_audio),
        "pcmu_size": len(pcmu_audio),
        "message": "Audio conversion pipeline working correctly",
    }

