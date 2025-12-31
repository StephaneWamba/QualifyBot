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
    # Railway terminates SSL at the edge and forwards HTTP, but Twilio signs with HTTPS
    # We need to construct the HTTPS URL for validation using the Host header
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Get the host from headers (Railway sets this correctly)
    host = request.headers.get("Host", "")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    
    # Construct the validation URL - always use HTTPS if X-Forwarded-Proto indicates HTTPS
    # or if we're in production (Railway always uses HTTPS publicly)
    if forwarded_proto == "https" or settings.ENVIRONMENT == "production":
        # Use HTTPS for validation (Twilio signs with HTTPS)
        scheme = "https"
    else:
        # Development - use the actual request scheme
        scheme = request.url.scheme
    
    # Build the full URL for validation
    if host:
        # Use Host header to construct URL (most reliable behind proxies)
        validation_url = f"{scheme}://{host}{request.url.path}"
        if request.url.query:
            validation_url += f"?{request.url.query}"
    else:
        # Fallback to request URL, but force HTTPS if needed
        validation_url = str(request.url)
        if scheme == "https" and validation_url.startswith("http://"):
            validation_url = validation_url.replace("http://", "https://", 1)
    
    logger.debug(
        "Validating Twilio signature",
        original_url=str(request.url),
        validation_url=validation_url,
        has_signature=bool(signature),
        param_count=len(params),
        forwarded_proto=forwarded_proto,
        host=host,
    )
    
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    # Validate with the HTTPS URL (Twilio always signs with HTTPS)
    is_valid = validator.validate(validation_url, params, signature)
    
    if not is_valid:
        # Try with original URL as fallback (for local development)
        original_url = str(request.url)
        is_valid = validator.validate(original_url, params, signature)
        if is_valid:
            validation_url = original_url
            logger.debug("Signature valid with original URL")
    
    if not is_valid:
        # In development, log but don't block (for debugging)
        if settings.ENVIRONMENT == "development":
            logger.warning(
                "Invalid Twilio signature (allowing in dev)",
                original_url=str(request.url),
                validation_url=validation_url,
                has_signature=bool(signature),
                host=host,
                forwarded_proto=forwarded_proto,
            )
            # Continue processing in dev mode
        else:
            logger.error(
                "Invalid Twilio request signature",
                original_url=str(request.url),
                validation_url=validation_url,
                host=host,
                forwarded_proto=forwarded_proto,
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
            # Hardcoded for Railway production (WebSocket support confirmed)
            media_stream_url = "wss://qualifybot-production.up.railway.app/api/v1/twilio/media-stream?call_sid={CallSid}".format(CallSid=CallSid)
            
            logger.info("Starting Media Stream", call_sid=CallSid, url=media_stream_url)
            
            # Start Media Stream - all audio will flow through WebSocket
            response.start().stream(url=media_stream_url)
            
            twiml_xml = str(response)
            logger.info("Media Stream TwiML generated", call_sid=CallSid, twiml_length=len(twiml_xml), twiml=twiml_xml)
            
            return Response(content=twiml_xml, media_type="application/xml")
        except Exception as e:
            logger.error("Failed to start Media Stream", call_sid=CallSid, error=str(e), exc_info=True)
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

