"""Service for retrieving caller history and personalization."""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.database.models import SupportTicket
from src.database.connection import AsyncSessionLocal
from src.core.logging import get_logger

logger = get_logger(__name__)


class CallerHistory:
    """Caller history information."""
    def __init__(
        self,
        total_calls: int = 0,
        recent_tickets: list[SupportTicket] = None,
        last_call_date: Optional[datetime] = None,
        resolved_issues: list[str] = None,
        common_issue_types: list[str] = None,
    ):
        self.total_calls = total_calls
        self.recent_tickets = recent_tickets or []
        self.last_call_date = last_call_date
        self.resolved_issues = resolved_issues or []
        self.common_issue_types = common_issue_types or []


class CallerHistoryService:
    """Service for retrieving and analyzing caller history."""

    async def get_caller_history(
        self,
        from_number: str,
        tenant_id: str = "default",
        days: int = 90,
    ) -> CallerHistory:
        """
        Get caller history for personalization.

        Args:
            from_number: Caller's phone number
            tenant_id: Tenant identifier
            days: Number of days to look back

        Returns:
            CallerHistory object with caller information
        """
        try:
            async with AsyncSessionLocal() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                stmt = select(SupportTicket).where(
                    and_(
                        SupportTicket.from_number == from_number,
                        SupportTicket.tenant_id == tenant_id,
                        SupportTicket.created_at >= cutoff_date
                    )
                ).order_by(SupportTicket.created_at.desc())
                
                result = await session.execute(stmt)
                tickets = list(result.scalars().all())

                if not tickets:
                    return CallerHistory()

                # Analyze tickets
                resolved_issues = []
                issue_types = {}
                
                for ticket in tickets:
                    if ticket.status == "resolved" and ticket.issue_description:
                        resolved_issues.append(ticket.issue_description[:100])
                    
                    issue_type = ticket.issue_type or "unknown"
                    issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

                # Get most common issue types
                common_issue_types = sorted(
                    issue_types.items(), key=lambda x: x[1], reverse=True
                )[:3]
                common_issue_types = [issue_type for issue_type, _ in common_issue_types]

                last_call_date = tickets[0].created_at if tickets else None

                return CallerHistory(
                    total_calls=len(tickets),
                    recent_tickets=tickets[:5],  # Last 5 tickets
                    last_call_date=last_call_date,
                    resolved_issues=resolved_issues[:3],  # Last 3 resolved issues
                    common_issue_types=common_issue_types,
                )
        except Exception as e:
            logger.error("Failed to get caller history",
                        from_number=from_number, error=str(e))
            return CallerHistory()

    async def get_personalization_context(
        self,
        from_number: str,
        tenant_id: str = "default",
    ) -> str:
        """
        Get personalization context string for LLM prompts.

        Args:
            from_number: Caller's phone number
            tenant_id: Tenant identifier

        Returns:
            Context string for personalization
        """
        history = await self.get_caller_history(from_number, tenant_id)
        
        if history.total_calls == 0:
            return ""

        context_parts = []
        
        if history.last_call_date:
            days_ago = (datetime.utcnow() - history.last_call_date).days
            if days_ago == 0:
                context_parts.append("This caller called earlier today.")
            elif days_ago == 1:
                context_parts.append("This caller called yesterday.")
            elif days_ago < 7:
                context_parts.append(f"This caller called {days_ago} days ago.")
            else:
                context_parts.append(f"This caller last called {days_ago} days ago.")

        if history.common_issue_types:
            context_parts.append(
                f"They commonly have issues with: {', '.join(history.common_issue_types)}."
            )

        if history.resolved_issues:
            context_parts.append(
                f"Previously resolved issues include: {', '.join(history.resolved_issues[:2])}."
            )

        if history.total_calls > 1:
            context_parts.append(
                f"This is their {history.total_calls} call to support."
            )

        return " ".join(context_parts) if context_parts else ""


caller_history_service = CallerHistoryService()

