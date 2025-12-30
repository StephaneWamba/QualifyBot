"""Twilio Voice service for handling phone calls."""

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class TwilioService:
    """Service for Twilio Voice operations."""

    def __init__(self):
        """Initialize Twilio client."""
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    def create_voice_response(self, text: str, voice_url: str | None = None) -> str:
        """
        Create TwiML response for voice call.

        Args:
            text: Text to say (if voice_url not provided)
            voice_url: Optional URL to audio file (ElevenLabs TTS)

        Returns:
            TwiML XML string
        """
        response = VoiceResponse()

        if voice_url:
            # Play audio from URL (ElevenLabs TTS)
            response.play(voice_url)
        else:
            # Fallback: use Twilio TTS
            response.say(text, voice="alice", language="en-US")

        return str(response)

    def handle_incoming_call(self, call_sid: str, from_number: str, to_number: str) -> str:
        """
        Handle incoming call webhook.

        Args:
            call_sid: Twilio Call SID
            from_number: Caller's phone number
            to_number: Called phone number

        Returns:
            TwiML response
        """
        logger.info(
            "Incoming call",
            call_sid=call_sid,
            from_number=from_number,
            to_number=to_number,
        )

        # Create initial greeting response
        response = VoiceResponse()
        response.say(
            "Hello! Thanks for calling. I'll ask you a few quick questions to get started. Sound good?",
            voice="alice",
            language="en-US",
        )

        # Start gathering input (will be handled by streaming endpoint)
        # For now, return simple response
        return str(response)

    def handle_status_callback(
        self,
        call_sid: str,
        call_status: str,
        duration: int | None = None,
    ) -> None:
        """
        Handle call status callback.

        Args:
            call_sid: Twilio Call SID
            call_status: Call status (ringing, in-progress, completed, etc.)
            duration: Call duration in seconds (if completed)
        """
        logger.info(
            "Call status update",
            call_sid=call_sid,
            status=call_status,
            duration=duration,
        )

    def get_call_info(self, call_sid: str) -> dict:
        """
        Get call information from Twilio.

        Args:
            call_sid: Twilio Call SID

        Returns:
            Call information dictionary
        """
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                "sid": call.sid,
                "status": call.status,
                "from": call.from_,
                "to": call.to,
                "duration": call.duration,
                "start_time": call.start_time.isoformat() if call.start_time else None,
                "end_time": call.end_time.isoformat() if call.end_time else None,
            }
        except Exception as e:
            logger.error("Failed to fetch call info", call_sid=call_sid, error=str(e))
            raise


# Singleton instance
twilio_service = TwilioService()


