"""LangGraph checkpoint configuration using Redis."""

try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
except ImportError:
    # Fallback to memory checkpointer if Redis checkpoint not available
    AsyncRedisSaver = None

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Global checkpointer instance (initialized at startup)
_checkpointer_cm = None
_checkpointer = None


async def init_checkpointer():
    """Initialize the checkpointer at application startup."""
    global _checkpointer_cm, _checkpointer
    
    try:
        if AsyncRedisSaver:
            # AsyncRedisSaver.from_conn_string() returns a context manager
            # Enter it and keep it alive for the application lifetime
            _checkpointer_cm = AsyncRedisSaver.from_conn_string(settings.redis_url)
            _checkpointer = await _checkpointer_cm.__aenter__()
            
            # Setup if method exists
            if hasattr(_checkpointer, "asetup"):
                try:
                    await _checkpointer.asetup()
                except Exception as setup_error:
                    logger.warning("Checkpointer setup failed (may not be needed)", error=str(setup_error))
            
            logger.info("Redis checkpointer initialized", redis_url=settings.redis_url)
        else:
            # Fallback to memory checkpointer
            from langgraph.checkpoint.memory import MemorySaver
            _checkpointer = MemorySaver()
            logger.warning("Using memory checkpointer (Redis checkpoint not available)")
    except Exception as e:
        logger.error("Failed to initialize checkpointer", error=str(e), exc_info=True)
        # Fallback to memory
        from langgraph.checkpoint.memory import MemorySaver
        _checkpointer = MemorySaver()
        logger.warning("Falling back to memory checkpointer")


async def close_checkpointer():
    """Close the checkpointer at application shutdown."""
    global _checkpointer_cm, _checkpointer
    
    if _checkpointer_cm is not None:
        try:
            await _checkpointer_cm.__aexit__(None, None, None)
            logger.info("Checkpointer closed")
        except Exception as e:
            logger.error("Error closing checkpointer", error=str(e))
        finally:
            _checkpointer_cm = None
            _checkpointer = None


def get_checkpointer():
    """Get the initialized checkpointer instance."""
    global _checkpointer
    
    if _checkpointer is None:
        # Fallback to memory if not initialized
        from langgraph.checkpoint.memory import MemorySaver
        logger.warning("Checkpointer not initialized, using memory fallback")
        return MemorySaver()
    
    return _checkpointer

