"""Redis-based session state management."""

import json
from typing import Any

import redis.asyncio as redis

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages session state in Redis."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client: redis.Redis | None = None
        self.default_ttl = 3600  # 1 hour

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis", url=settings.redis_url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary or None if not found
        """
        await self.connect()
        try:
            data = await self.redis_client.get(f"session:{session_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error("Failed to get session", session_id=session_id, error=str(e))
            return None

    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """
        Set session data.

        Args:
            session_id: Session identifier
            data: Session data dictionary
            ttl: Time to live in seconds (defaults to default_ttl)
        """
        await self.connect()
        try:
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(data),
            )
            logger.debug("Session updated", session_id=session_id, ttl=ttl)
        except Exception as e:
            logger.error("Failed to set session", session_id=session_id, error=str(e))
            raise

    async def update_session(
        self,
        session_id: str,
        updates: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """
        Update session data (merge with existing).

        Args:
            session_id: Session identifier
            updates: Dictionary of updates to merge
            ttl: Time to live in seconds
        """
        current = await self.get_session(session_id) or {}
        current.update(updates)
        await self.set_session(session_id, current, ttl)

    async def delete_session(self, session_id: str) -> None:
        """
        Delete session.

        Args:
            session_id: Session identifier
        """
        await self.connect()
        try:
            await self.redis_client.delete(f"session:{session_id}")
            logger.debug("Session deleted", session_id=session_id)
        except Exception as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))

    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        await self.connect()
        try:
            return await self.redis_client.exists(f"session:{session_id}") > 0
        except Exception as e:
            logger.error("Failed to check session", session_id=session_id, error=str(e))
            return False


# Singleton instance
session_manager = SessionManager()



