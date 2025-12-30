"""OpenAI Realtime API service for Speech-to-Text."""

import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class STTService:
    """Service for OpenAI Realtime API Speech-to-Text."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def transcribe_audio_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe audio stream using OpenAI Realtime API.

        Args:
            audio_stream: Async generator of audio chunks
            session_id: Session identifier

        Yields:
            Transcribed text segments

        Note:
            Full implementation requires WebSocket connection to OpenAI Realtime API.
            This is a placeholder for the actual implementation.
        """
        try:
            # TODO: Implement OpenAI Realtime API WebSocket connection
            # For now, use Whisper API as fallback
            logger.warning(
                "Using fallback transcription - Realtime API not yet implemented",
                session_id=session_id,
            )

            # Collect audio chunks
            audio_data = b""
            async for chunk in audio_stream:
                audio_data += chunk

            # Transcribe using Whisper
            if audio_data:
                text = await self.transcribe_audio_file(audio_data, session_id)
                if text:
                    yield text

        except Exception as e:
            logger.error("STT transcription error", session_id=session_id, error=str(e))
            raise

    async def transcribe_audio_file(self, audio_file: bytes, session_id: str) -> str:
        """
        Transcribe audio file using OpenAI Whisper API.

        Args:
            audio_file: Audio file bytes
            session_id: Session identifier

        Returns:
            Transcribed text
        """
        try:
            import io

            # Create file-like object for Whisper API
            # Whisper API accepts various formats, but we'll use WAV
            audio_io = io.BytesIO(audio_file)
            # Set name attribute for file identification
            audio_io.name = "audio.wav"

            # Use Whisper API for file-based transcription
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", audio_io, "audio/wav"),
            )
            text = transcript.text
            logger.info("Transcribed audio file", session_id=session_id, text_length=len(text))
            return text
        except Exception as e:
            logger.error("Audio transcription error", session_id=session_id, error=str(e))
            raise


# Singleton instance
stt_service = STTService()

