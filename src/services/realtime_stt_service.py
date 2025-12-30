"""OpenAI Realtime API service for real-time Speech-to-Text."""

import asyncio
import json
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class RealtimeSTTService:
    """Service for OpenAI Realtime API Speech-to-Text."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def create_session(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe audio stream using Whisper API (Realtime API placeholder).

        Args:
            audio_stream: Async generator of audio chunks (PCM format)
            session_id: Session identifier

        Yields:
            Transcribed text segments

        Note:
            OpenAI Realtime API is not yet available in the Python SDK.
            Using Whisper API with buffering for now.
        """
        try:
            import io
            import wave

            # Buffer audio chunks
            audio_buffer = io.BytesIO()
            chunk_count = 0
            buffer_duration = 0  # Track approximate duration
            min_duration_for_transcription = 1.0  # Transcribe every ~1 second

            async for audio_chunk in audio_stream:
                if audio_chunk is None:
                    break

                # Write chunk to buffer
                audio_buffer.write(audio_chunk)
                chunk_count += 1
                # Approximate: 8000 Hz, 1 byte per sample = 0.000125 seconds per byte
                buffer_duration += len(audio_chunk) * 0.000125

                # Transcribe when buffer has enough audio
                if buffer_duration >= min_duration_for_transcription:
                    # Reset buffer position
                    audio_buffer.seek(0)
                    audio_data = audio_buffer.read()

                    if len(audio_data) > 0:
                        # Convert PCMU (μ-law) to PCM16, then to WAV format for Whisper
                        pcm16_data = self.convert_pcmu_to_pcm16(audio_data)
                        
                        wav_buffer = io.BytesIO()
                        with wave.open(wav_buffer, "wb") as wav_file:
                            wav_file.setnchannels(1)  # Mono
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(8000)  # 8kHz (PCMU standard)
                            wav_file.writeframes(pcm16_data)

                        wav_buffer.seek(0)
                        wav_buffer.name = "audio.wav"

                        # Transcribe using Whisper
                        try:
                            transcript = await self.client.audio.transcriptions.create(
                                model="whisper-1",
                                file=("audio.wav", wav_buffer, "audio/wav"),
                            )
                            text = transcript.text.strip()
                            if text:
                                logger.info(
                                    "Audio transcribed",
                                    session_id=session_id,
                                    text=text[:50],
                                )
                                yield text
                        except Exception as e:
                            logger.warning("Whisper transcription error", session_id=session_id, error=str(e))

                    # Reset buffer
                    audio_buffer = io.BytesIO()
                    buffer_duration = 0

            # Transcribe remaining audio
            audio_buffer.seek(0)
            remaining_audio = audio_buffer.read()
            if len(remaining_audio) > 0:
                # Convert PCMU to PCM16
                pcm16_data = self.convert_pcmu_to_pcm16(remaining_audio)
                
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(8000)
                    wav_file.writeframes(pcm16_data)

                wav_buffer.seek(0)
                wav_buffer.name = "audio.wav"

                try:
                    transcript = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("audio.wav", wav_buffer, "audio/wav"),
                    )
                    text = transcript.text.strip()
                    if text:
                        logger.info("Final transcription", session_id=session_id, text=text[:50])
                        yield text
                except Exception as e:
                    logger.warning("Final Whisper transcription error", session_id=session_id, error=str(e))

        except Exception as e:
            logger.error("Audio transcription error", session_id=session_id, error=str(e))
            raise


    def convert_pcmu_to_pcm16(self, pcmu_bytes: bytes) -> bytes:
        """
        Convert PCMU (G.711 μ-law) to PCM16 format.

        Args:
            pcmu_bytes: PCMU audio bytes

        Returns:
            PCM16 audio bytes
        """
        # Use audio converter for proper conversion
        from src.services.audio_converter import audio_converter
        return audio_converter.pcmu_to_pcm16(pcmu_bytes)


# Singleton instance
realtime_stt_service = RealtimeSTTService()

