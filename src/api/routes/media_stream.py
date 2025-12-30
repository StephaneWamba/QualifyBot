"""Twilio Media Streams WebSocket endpoint."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.logging import get_logger
from src.services.media_stream_service import MediaStreamHandler
from src.services.realtime_stt_service import realtime_stt_service
from src.agent.orchestrator import qualification_orchestrator
from src.services.tts_service import tts_service
from src.services.audio_converter import audio_converter

logger = get_logger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])


async def audio_stream_generator(handler: MediaStreamHandler):
    """Generator for audio chunks from Media Stream."""
    while handler.is_connected:
        chunk = await handler.get_audio_chunk()
        if chunk is None:
            break
        yield chunk


@router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """
    Handle Twilio Media Streams WebSocket connection.
    
    Note: Twilio sends call_sid in the 'start' message payload, not as a query parameter.
    """
    # Accept connection first
    await websocket.accept()
    logger.info("WebSocket connection accepted", client=websocket.client.host if websocket.client else None)
    
    call_sid: Optional[str] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    handler: Optional[MediaStreamHandler] = None
    stt_task: Optional[asyncio.Task] = None
    greeting_task: Optional[asyncio.Task] = None

    try:
        # Receive messages from Twilio
        # First message should be "connected", then "start" with call_sid
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event_type = data.get("event")
            
            # Extract call_sid and phone numbers from "start" event
            if event_type == "start" and not call_sid:
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                from_number = start_data.get("caller", "") or start_data.get("from", "")
                to_number = start_data.get("called", "") or start_data.get("to", "")
                
                if call_sid:
                    logger.info(
                        "Extracted call info from start event",
                        call_sid=call_sid,
                        from_number=from_number,
                        to_number=to_number,
                    )
                    # Create handler now that we have call_sid
                    handler = MediaStreamHandler(websocket, call_sid)
                    # Mark as connected since WebSocket is already connected
                    handler.is_connected = True
                    logger.info("Handler created and marked as connected", call_sid=call_sid)
                else:
                    logger.error("No callSid in start event", data=data)
            
            # Process message with handler if available
            if handler:
                await handler.handle_message(message)
                
                # Start STT and send greeting when stream starts
                # Wait for both stream_sid to be set AND handler to be connected
                if handler.stream_sid and handler.is_connected and stt_task is None:
                    logger.info(
                        "Starting STT transcription and sending greeting",
                        call_sid=call_sid,
                        stream_sid=handler.stream_sid,
                        is_connected=handler.is_connected,
                    )
                    
                    # Generate and send initial greeting through Media Stream
                    greeting_task = asyncio.create_task(
                        _send_initial_greeting(handler, call_sid, from_number or "", to_number or "")
                    )
                    # Add error handler for greeting task
                    def log_greeting_error(task):
                        if task.exception():
                            logger.error(
                                "Greeting task failed",
                                call_sid=call_sid,
                                error=str(task.exception()),
                                exc_info=task.exception(),
                            )
                    greeting_task.add_done_callback(log_greeting_error)
                    
                    # Start STT processing
                    stt_task = asyncio.create_task(
                        _process_audio_stream(handler, call_sid)
                    )
                    # Add error handler for STT task
                    def log_stt_error(task):
                        if task.exception():
                            logger.error(
                                "STT task failed",
                                call_sid=call_sid,
                                error=str(task.exception()),
                                exc_info=task.exception(),
                            )
                    stt_task.add_done_callback(log_stt_error)
            elif event_type != "connected":
                # Log messages before we have call_sid (except "connected" which is expected)
                logger.debug("Received message before call_sid extracted", event_type=event_type, data=data)

    except WebSocketDisconnect:
        logger.info("Media Stream WebSocket disconnected", call_sid=call_sid)
    except Exception as e:
        logger.error(
            "Media Stream error",
            call_sid=call_sid,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
    finally:
        # Cleanup - wait for tasks and log any exceptions
        if greeting_task:
            if not greeting_task.done():
                greeting_task.cancel()
            try:
                await greeting_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Greeting task exception during cleanup", call_sid=call_sid, error=str(e), exc_info=True)
        
        if stt_task:
            if not stt_task.done():
                stt_task.cancel()
            try:
                await stt_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("STT task exception during cleanup", call_sid=call_sid, error=str(e), exc_info=True)
        
        if handler:
            await handler.close()


async def _send_initial_greeting(handler: MediaStreamHandler, call_sid: str, from_number: str, to_number: str):
    """
    Generate and send initial greeting through Media Stream.
    
    This is where the greeting is generated (not in the webhook).
    The greeting is generated, converted to audio, and sent immediately.
    
    Args:
        handler: Media Stream handler
        call_sid: Twilio Call SID
        from_number: Caller's phone number
        to_number: Called phone number
    """
    try:
        # Verify handler is connected
        if not handler.is_connected:
            logger.error("Handler not connected, cannot send greeting", call_sid=call_sid)
            return
        
        # Generate greeting via orchestrator (this is the RIGHT place to do it)
        logger.info("Generating greeting", call_sid=call_sid)
        result = await qualification_orchestrator.start_qualification(
            call_sid=call_sid,
            from_number=from_number,
            to_number=to_number,
            session_id=call_sid,
        )
        
        greeting = result.get("greeting", "Hello! Thanks for calling.")
        logger.info("Greeting generated", call_sid=call_sid, greeting=greeting[:50])
        
        # Generate TTS audio for greeting
        mp3_audio = tts_service.generate_audio(greeting)
        logger.debug("TTS audio generated", call_sid=call_sid, mp3_size=len(mp3_audio))
        
        # Convert MP3 → PCMU for Twilio Media Streams
        pcmu_audio = audio_converter.mp3_to_pcmu(mp3_audio)
        logger.debug("Audio converted to PCMU", call_sid=call_sid, pcmu_size=len(pcmu_audio))
        
        # Send greeting audio through Media Stream in chunks
        chunk_size = 1600  # ~200ms of audio at 8kHz (PCMU is 1 byte per sample)
        total_chunks = (len(pcmu_audio) + chunk_size - 1) // chunk_size
        logger.info("Sending greeting in chunks", call_sid=call_sid, total_chunks=total_chunks)
        
        for i in range(0, len(pcmu_audio), chunk_size):
            chunk = pcmu_audio[i:i + chunk_size]
            if not handler.is_connected:
                logger.warning("Handler disconnected during greeting send", call_sid=call_sid)
                break
            await handler.send_audio(chunk)
            # Small delay between chunks for smooth playback
            await asyncio.sleep(0.02)  # 20ms delay
        
        logger.info(
            "Initial greeting sent via Media Streams",
            call_sid=call_sid,
            mp3_size=len(mp3_audio),
            pcmu_size=len(pcmu_audio),
        )
    except Exception as e:
        logger.error("Error sending initial greeting", call_sid=call_sid, error=str(e), exc_info=True)
        # Try to send error message to user via Media Stream
        try:
            if handler and handler.is_connected:
                error_message = "I'm sorry, I'm having technical difficulties. Please try again later."
                mp3_audio = tts_service.generate_audio(error_message)
                pcmu_audio = audio_converter.mp3_to_pcmu(mp3_audio)
                await handler.send_audio(pcmu_audio)
                logger.info("Error message sent to user", call_sid=call_sid)
        except Exception as send_error:
            logger.error("Failed to send error message to user", call_sid=call_sid, error=str(send_error))


async def _process_audio_stream(handler: MediaStreamHandler, call_sid: str):
    """
    Process audio stream with STT and generate responses.

    Args:
        handler: Media Stream handler
        call_sid: Twilio Call SID
    """
    try:
        # Transcribe audio stream (PCMU format from Twilio)
        # Whisper API can handle various formats, so we'll pass PCMU directly
        async for transcribed_text in realtime_stt_service.create_session(
            audio_stream_generator(handler),
            call_sid,
        ):
            if not transcribed_text.strip():
                continue

            logger.info(
                "User speech transcribed",
                call_sid=call_sid,
                text=transcribed_text[:50],
            )

            # Process user response with LangGraph
            try:
                result = await qualification_orchestrator.process_user_response(
                    call_sid=call_sid,
                    user_text=transcribed_text,
                    session_id=call_sid,
                )

                agent_response = result.get("response", "I understand. Let me continue.")
                is_complete = result.get("is_complete", False)

                # Generate TTS audio
                try:
                    # Generate MP3 audio from ElevenLabs
                    mp3_audio = tts_service.generate_audio(agent_response)
                    
                    # Convert MP3 → PCMU for Twilio Media Streams
                    pcmu_audio = audio_converter.mp3_to_pcmu(mp3_audio)
                    
                    # Send audio to Twilio Media Stream
                    await handler.send_audio(pcmu_audio)
                    
                    logger.info(
                        "TTS audio sent via Media Streams",
                        call_sid=call_sid,
                        mp3_size=len(mp3_audio),
                        pcmu_size=len(pcmu_audio),
                    )
                except Exception as e:
                    logger.error("TTS generation/conversion failed", call_sid=call_sid, error=str(e))

                if is_complete:
                    logger.info("Qualification complete", call_sid=call_sid)
                    break

            except Exception as e:
                logger.error(
                    "Error processing user response",
                    call_sid=call_sid,
                    error=str(e),
                )

    except asyncio.CancelledError:
        logger.debug("Audio processing cancelled", call_sid=call_sid)
    except Exception as e:
        logger.error("Audio processing error", call_sid=call_sid, error=str(e))

