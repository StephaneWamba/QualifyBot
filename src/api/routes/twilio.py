"""Twilio webhook routes."""

from fastapi import APIRouter, Form, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from src.core.config import settings
from src.core.logging import get_logger
from src.services.twilio_service import twilio_service

logger = get_logger(__name__)

router = APIRouter(prefix="/twilio", tags=["twilio"])


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(...),
):
    """
    Handle Twilio webhook for incoming calls.

    This endpoint receives webhooks from Twilio when:
    - A call is initiated
    - Call status changes
    - Call ends
    """
    # Validate Twilio request
    # Twilio signs requests with the HTTPS URL, but FastAPI might see HTTP behind proxy
    # Check X-Forwarded-Proto header or use HTTPS if behind cloudflared
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto == "https" or request.url.scheme == "https":
        # Already HTTPS
        url = str(request.url)
    else:
        # Behind proxy (cloudflared) - Twilio signed with HTTPS URL
        url = str(request.url).replace("http://", "https://")
    
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    
    logger.debug(
        "Validating Twilio signature",
        url=url,
        has_signature=bool(signature),
        param_count=len(params),
    )
    
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    # Log signature validation details
    logger.info(
        "Validating Twilio signature",
        url=url,
        has_signature=bool(signature),
        signature_length=len(signature) if signature else 0,
        param_count=len(params),
        params_keys=list(params.keys())[:5],  # First 5 keys for debugging
    )
    
    # Try validation with HTTPS URL first (Twilio signs with HTTPS)
    validation_url = url.replace("http://", "https://") if url.startswith("http://") else url
    is_valid = validator.validate(validation_url, params, signature)
    
    if not is_valid:
        # Try with original URL as fallback
        is_valid = validator.validate(url, params, signature)
        if is_valid:
            validation_url = url
            logger.debug("Signature valid with original URL")
    
    if not is_valid:
        # In development, log but don't block (for debugging)
        if settings.ENVIRONMENT == "development":
            logger.warning(
                "Invalid Twilio signature (allowing in dev)",
                url=url,
                validation_url=validation_url,
                has_signature=bool(signature),
            )
            # Continue processing in dev mode
        else:
            logger.error(
                "Invalid Twilio request signature",
                url=url,
                validation_url=validation_url,
            )
            return Response(content="Invalid signature", status_code=403)

    logger.info(
        "Twilio webhook received",
        call_sid=CallSid,
        from_number=From,
        to_number=To,
        status=CallStatus,
    )

    # Handle different webhook types
    if CallStatus == "ringing":
        # Initial call - return TwiML to start Media Stream
        # The greeting will be generated and sent by the Media Stream handler
        try:
            response = VoiceResponse()
            
            # Start Media Stream
            # Media Streams requires WebSocket URL (wss://)
            # Use the incoming request's host to build the URL dynamically
            # This handles cloudflared URL changes automatically
            host = request.headers.get("Host", "")
            if not host:
                # Fallback to TWILIO_WEBHOOK_URL if Host header is missing
                base_url = settings.TWILIO_WEBHOOK_URL.replace("/webhook", "")
                if base_url.startswith("https://"):
                    host = base_url.replace("https://", "").split("/")[0]
                elif base_url.startswith("http://"):
                    host = base_url.replace("http://", "").split("/")[0]
                else:
                    host = base_url.split("/")[0]
            
            # Determine protocol (wss for HTTPS, ws for HTTP)
            # Behind cloudflared, we should always use wss
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "https")
            scheme = "wss" if forwarded_proto == "https" or request.url.scheme == "https" else "ws"
            
            # Build Media Stream WebSocket URL
            media_stream_url = f"{scheme}://{host}/api/v1/twilio/media-stream?call_sid={CallSid}"
            
            # Start Media Stream - all audio will flow through WebSocket
            response.start().stream(url=media_stream_url)
            
            logger.info("Media Stream started", call_sid=CallSid, url=media_stream_url, host=host)
            
            return Response(content=str(response), media_type="application/xml")
        except Exception as e:
            logger.error("Failed to start Media Stream", call_sid=CallSid, error=str(e))
            response = VoiceResponse()
            response.say(
                "I'm sorry, I'm having technical difficulties. Please try again later.",
                voice="alice",
                language="en-US",
            )
            return Response(content=str(response), media_type="application/xml")

    elif CallStatus == "in-progress":
        # Call is active
        return Response(content="OK", status_code=200)

    elif CallStatus == "completed":
        # Call ended
        twilio_service.handle_status_callback(CallSid, CallStatus)
        return Response(content="OK", status_code=200)

    # Default response for other statuses
    return Response(content="OK", status_code=200)




@router.post("/status")
async def handle_status_callback(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: str = Form(None),
):
    """Handle Twilio status callbacks."""
    # Validate request
    url = str(request.url)
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    if not validator.validate(url, params, signature):
        logger.warning("Invalid Twilio status callback signature", url=url)
        return Response(content="Invalid signature", status_code=403)

    duration = int(CallDuration) if CallDuration else None
    twilio_service.handle_status_callback(CallSid, CallStatus, duration)

    return {"status": "ok"}

