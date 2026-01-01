"""ElevenLabs TTS service for text-to-speech conversion."""

from elevenlabs.client import ElevenLabs

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class TTSService:
    """Service for ElevenLabs Text-to-Speech."""

    def __init__(self):
        """Initialize ElevenLabs client."""
        if not settings.ELEVENLABS_API_KEY:
            logger.warning("ELEVENLABS_API_KEY is not set - TTS will fail")
        self.client = ElevenLabs(
            api_key=settings.ELEVENLABS_API_KEY) if settings.ELEVENLABS_API_KEY else None
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        logger.info("TTS Service initialized", voice_id=self.voice_id,
                    has_api_key=bool(settings.ELEVENLABS_API_KEY))

    def generate_audio(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Generate audio from text using ElevenLabs.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (defaults to configured voice)

        Returns:
            Audio bytes (MP3 format)
        """
        try:
            if not self.client:
                raise ValueError(
                    "ElevenLabs client not initialized - ELEVENLABS_API_KEY is missing")

            # Always read from settings to get latest voice ID (in case it changed)
            voice = voice_id or settings.ELEVENLABS_VOICE_ID
            logger.info("Generating TTS audio", text_length=len(
                text), voice_id=voice, using_config_voice=voice_id is None)

            # Try new API first (text_to_speech.convert)
            try:
                audio_generator = self.client.text_to_speech.convert(
                    voice_id=voice,
                    text=text,
                    model_id="eleven_multilingual_v2",
                )
                audio_bytes = b"".join(audio_generator)
            except AttributeError:
                # Fallback to older API (generate function)
                from elevenlabs import generate
                audio_generator = generate(
                    text=text,
                    voice=voice,
                    model="eleven_multilingual_v2",
                )
                audio_bytes = b"".join(audio_generator)

            logger.info("TTS audio generated", text_length=len(
                text), audio_size=len(audio_bytes))
            return audio_bytes

        except Exception as e:
            logger.error("TTS generation error", error=str(e), text=text[:50])
            raise

    def generate_audio_stream(self, text: str, voice_id: str | None = None):
        """
        Generate streaming audio from text.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID

        Yields:
            Audio chunks (bytes)
        """
        try:
            voice = voice_id or self.voice_id
            logger.debug("Generating streaming TTS",
                         text_length=len(text), voice_id=voice)

            # Try new API first
            try:
                audio_stream = self.client.text_to_speech.convert_as_stream(
                    voice_id=voice,
                    text=text,
                    model_id="eleven_multilingual_v2",
                )
            except AttributeError:
                # Fallback to older API
                from elevenlabs import generate
                audio_stream = generate(
                    text=text,
                    voice=voice,
                    model="eleven_multilingual_v2",
                    stream=True,
                )

            for chunk in audio_stream:
                yield chunk

        except Exception as e:
            logger.error("Streaming TTS error", error=str(e), text=text[:50])
            raise

    def get_available_voices(self) -> list[dict]:
        """
        Get list of available voices.

        Returns:
            List of voice dictionaries
        """
        try:
            voices_response = self.client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": getattr(voice, "category", None),
                }
                for voice in voices_response.voices
            ]
        except Exception as e:
            logger.error("Failed to fetch voices", error=str(e))
            return []


# Singleton instance
tts_service = TTSService()
