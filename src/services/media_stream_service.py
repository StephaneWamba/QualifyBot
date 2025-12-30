"""Twilio Media Streams service for real-time audio streaming."""

import asyncio
import base64
import json
from typing import Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


class MediaStreamHandler:
    """Handler for Twilio Media Streams WebSocket connection."""

    def __init__(self, websocket, call_sid: str):
        """
        Initialize media stream handler.

        Args:
            websocket: WebSocket connection
            call_sid: Twilio Call SID
        """
        self.websocket = websocket
        self.call_sid = call_sid
        self.is_connected = False
        self.stream_sid: Optional[str] = None
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self._audio_task: Optional[asyncio.Task] = None

    async def handle_message(self, message: str) -> None:
        """
        Handle incoming message from Twilio Media Streams.

        Args:
            message: JSON message from Twilio
        """
        try:
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "connected":
                await self._handle_connected(data)
            elif event_type == "start":
                await self._handle_start(data)
            elif event_type == "media":
                await self._handle_media(data)
            elif event_type == "stop":
                await self._handle_stop(data)
            else:
                logger.debug("Unknown event type", event_type=event_type, call_sid=self.call_sid)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Media Stream message", error=str(e), call_sid=self.call_sid)
        except Exception as e:
            logger.error("Error handling Media Stream message", error=str(e), call_sid=self.call_sid)

    async def _handle_connected(self, data: dict) -> None:
        """Handle connected event."""
        logger.info("Media Stream connected", call_sid=self.call_sid, data=data)
        self.is_connected = True

    async def _handle_start(self, data: dict) -> None:
        """Handle start event."""
        self.stream_sid = data.get("streamSid")
        logger.info(
            "Media Stream started",
            call_sid=self.call_sid,
            stream_sid=self.stream_sid,
        )

    async def _handle_media(self, data: dict) -> None:
        """Handle media event (audio chunk)."""
        # Extract base64 audio payload
        payload = data.get("media", {}).get("payload")
        if payload:
            # Decode base64 audio
            audio_bytes = base64.b64decode(payload)
            # Put audio in queue for processing
            await self.audio_queue.put(audio_bytes)

    async def _handle_stop(self, data: dict) -> None:
        """Handle stop event."""
        logger.info("Media Stream stopped", call_sid=self.call_sid)
        self.is_connected = False
        # Signal end of stream
        await self.audio_queue.put(None)

    async def send_audio(self, audio_bytes: bytes) -> None:
        """
        Send audio to Twilio Media Stream.

        Args:
            audio_bytes: Audio bytes to send (PCMU format)
        """
        if not self.is_connected:
            logger.warning("Cannot send audio - stream not connected", call_sid=self.call_sid)
            return

        try:
            # Encode audio as base64
            payload = base64.b64encode(audio_bytes).decode("utf-8")

            # Create Media Stream message
            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": payload,
                },
            }

            await self.websocket.send_text(json.dumps(message))

        except Exception as e:
            logger.error("Error sending audio to Media Stream", error=str(e), call_sid=self.call_sid)

    async def get_audio_chunk(self) -> Optional[bytes]:
        """
        Get next audio chunk from the stream.

        Returns:
            Audio bytes or None if stream ended
        """
        return await self.audio_queue.get()

    async def close(self) -> None:
        """Close the media stream handler."""
        self.is_connected = False
        # Cancel audio task if running
        if self._audio_task and not self._audio_task.done():
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass


