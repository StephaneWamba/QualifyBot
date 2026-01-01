"""Twilio webhook routes."""

import uuid
from fastapi import APIRouter, Form, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from src.core.config import settings
from src.core.logging import get_logger
from src.services.twilio_service import twilio_service
from src.services.tts_service import tts_service
from src.agent.orchestrator import support_orchestrator

logger = get_logger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])

_audio_cache: dict[str, bytes] = {}


def _build_base_url(request: Request) -> str:
    """Build base URL for audio and action endpoints."""
    host = request.headers.get("Host", "")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")

    if forwarded_proto == "https" or settings.ENVIRONMENT == "production":
        scheme = "https"
    else:
        scheme = request.url.scheme

    return f"{scheme}://{host}"


async def _validate_twilio_request(request: Request) -> bool:
    """Validate Twilio webhook signature."""
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    signature = request.headers.get("X-Twilio-Signature", "")

    if not signature:
        return settings.ENVIRONMENT == "development"

    host = request.headers.get("Host", "")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")

    if forwarded_proto == "https" or settings.ENVIRONMENT == "production":
        scheme = "https"
    else:
        scheme = request.url.scheme

    if host:
        validation_url = f"{scheme}://{host}{request.url.path}"
        if request.url.query:
            validation_url += f"?{request.url.query}"
    else:
        validation_url = str(request.url)
        if scheme == "https" and validation_url.startswith("http://"):
            validation_url = validation_url.replace("http://", "https://", 1)

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    is_valid = validator.validate(validation_url, params, signature)

    if not is_valid and settings.ENVIRONMENT == "development":
        logger.warning(
            "Invalid Twilio signature (allowing in dev)", url=validation_url)

    return is_valid or settings.ENVIRONMENT == "development"


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(...),
):
    """Handle Twilio webhook for incoming calls."""
    if not await _validate_twilio_request(request):
        return Response(content="Invalid signature", status_code=403)

    logger.info("Twilio webhook received", call_sid=CallSid, status=CallStatus)

    if CallStatus == "ringing":
        try:
            result = await support_orchestrator.start_support(
                call_sid=CallSid,
                from_number=From,
                to_number=To,
                tenant_id="default",  # Future: Extract from phone number routing or metadata
                session_id=CallSid,
            )
            greeting = result.get("greeting", "Hello! Thanks for calling.")

            response = VoiceResponse()
            base_url = _build_base_url(request)

            try:
                mp3_audio = tts_service.generate_audio(greeting)
                if not mp3_audio or len(mp3_audio) == 0:
                    raise ValueError("Generated audio is empty")

                audio_id = str(uuid.uuid4())
                _audio_cache[audio_id] = mp3_audio
                audio_url = f"{base_url}/api/v1/twilio/audio/{audio_id}"
                response.play(audio_url)
            except Exception as e:
                logger.error("ElevenLabs TTS failed, using fallback",
                             call_sid=CallSid, error=str(e))
                response.say(greeting, voice="alice", language="en-US")

            gather_action_url = f"{base_url}/api/v1/twilio/response"
            response.gather(
                input="speech",
                action=gather_action_url,
                method="POST",
                speech_timeout="auto",
                language="en-US",
            )

            return Response(content=str(response), media_type="application/xml")
        except Exception as e:
            logger.error("Failed to handle initial call",
                         call_sid=CallSid, error=str(e), exc_info=True)
            response = VoiceResponse()
            response.say("I'm sorry, I'm having technical difficulties. Please try again later.",
                         voice="alice", language="en-US")
            return Response(content=str(response), media_type="application/xml")

    elif CallStatus == "completed":
        twilio_service.handle_status_callback(CallSid, CallStatus)

    return Response(content="OK", status_code=200)


@router.post("/response")
async def handle_response(
    request: Request,
    CallSid: str = Form(...),
    SpeechResult: str = Form(None),
):
    """Handle user speech input and return agent response."""
    if not await _validate_twilio_request(request):
        return Response(content="Invalid signature", status_code=403)

    user_text = SpeechResult.strip() if SpeechResult else ""

    if not user_text:
        logger.warning("Empty speech result", call_sid=CallSid)
        response = VoiceResponse()
        response.say("I'm sorry, I didn't catch that. Could you please repeat?",
                     voice="alice", language="en-US")
        base_url = _build_base_url(request)
        response.gather(
            input="speech",
            action=f"{base_url}/api/v1/twilio/response",
            method="POST",
            speech_timeout="auto",
            language="en-US",
        )
        return Response(content=str(response), media_type="application/xml")

    try:
        result = await support_orchestrator.process_user_response(
            call_sid=CallSid,
            user_text=user_text,
            tenant_id="default",  # Future: Extract from phone number routing or metadata
            session_id=CallSid,
        )

        agent_response = result.get(
            "response", "I understand. Let me continue.")
        is_complete = result.get("is_complete", False)

        response = VoiceResponse()
        base_url = _build_base_url(request)

        try:
            mp3_audio = tts_service.generate_audio(agent_response)
            if not mp3_audio or len(mp3_audio) == 0:
                raise ValueError("Generated audio is empty")

            audio_id = str(uuid.uuid4())
            _audio_cache[audio_id] = mp3_audio
            audio_url = f"{base_url}/api/v1/twilio/audio/{audio_id}"
            response.play(audio_url)
        except Exception as e:
            logger.error("ElevenLabs TTS failed, using fallback",
                         call_sid=CallSid, error=str(e))
            response.say(agent_response, voice="alice", language="en-US")

        if is_complete:
            logger.info("Call completed", call_sid=CallSid)
            response.hangup()
        else:
            response.gather(
                input="speech",
                action=f"{base_url}/api/v1/twilio/response",
                method="POST",
                speech_timeout="auto",
                language="en-US",
            )

        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        logger.error("Failed to handle response",
                     call_sid=CallSid, error=str(e), exc_info=True)
        response = VoiceResponse()
        response.say("I'm sorry, I'm having technical difficulties. Please try again later.",
                     voice="alice", language="en-US")
        return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def handle_status_callback(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(None),
):
    """Handle Twilio status callbacks."""
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    signature = request.headers.get("X-Twilio-Signature", "")

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    if not validator.validate(str(request.url), params, signature):
        return Response(content="Invalid signature", status_code=403)

    duration = int(CallDuration) if CallDuration else None
    twilio_service.handle_status_callback(CallSid, CallStatus, duration)
    return {"status": "ok"}


@router.get("/audio/{audio_id}")
async def serve_audio(audio_id: str):
    """Serve cached audio files generated by ElevenLabs TTS."""
    if audio_id not in _audio_cache:
        logger.warning("Audio file not found", audio_id=audio_id)
        return Response(content="Audio not found", status_code=404)

    audio_bytes = _audio_cache[audio_id]
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="{audio_id}.mp3"',
            "Cache-Control": "no-cache",
        },
    )
