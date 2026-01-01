"""Analytics service for tracking conversation and ticket metrics."""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.database.models import SupportTicket
from src.database.connection import AsyncSessionLocal
from src.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing conversation metrics."""

    async def get_conversation_metrics(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30,
    ) -> dict:
        """
        Get conversation analytics metrics.

        Args:
            tenant_id: Optional tenant filter
            days: Number of days to look back

        Returns:
            Dictionary with metrics
        """
        try:
            async with AsyncSessionLocal() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                stmt = select(SupportTicket).where(
                    SupportTicket.created_at >= cutoff_date
                )
                if tenant_id:
                    stmt = stmt.where(SupportTicket.tenant_id == tenant_id)

                result = await session.execute(stmt)
                tickets = list(result.scalars().all())

                total_tickets = len(tickets)
                resolved = sum(1 for t in tickets if t.status == "resolved")
                escalated = sum(1 for t in tickets if t.status == "escalated")
                open_tickets = sum(1 for t in tickets if t.status == "open")

                # Issue type breakdown
                issue_types = {}
                for ticket in tickets:
                    issue_type = ticket.issue_type or "unknown"
                    issue_types[issue_type] = issue_types.get(
                        issue_type, 0) + 1

                # Severity breakdown
                severity_counts = {}
                for ticket in tickets:
                    severity = ticket.severity or "unknown"
                    severity_counts[severity] = severity_counts.get(
                        severity, 0) + 1

                # KB articles usage
                kb_articles_used = {}
                for ticket in tickets:
                    for article in ticket.kb_articles_used or []:
                        kb_articles_used[article] = kb_articles_used.get(
                            article, 0) + 1

                resolution_rate = (resolved / total_tickets *
                                   100) if total_tickets > 0 else 0
                escalation_rate = (escalated / total_tickets *
                                   100) if total_tickets > 0 else 0

                return {
                    "period_days": days,
                    "total_tickets": total_tickets,
                    "resolved": resolved,
                    "escalated": escalated,
                    "open": open_tickets,
                    "resolution_rate": round(resolution_rate, 2),
                    "escalation_rate": round(escalation_rate, 2),
                    "issue_types": issue_types,
                    "severity_breakdown": severity_counts,
                    "kb_articles_usage": dict(sorted(kb_articles_used.items(), key=lambda x: x[1], reverse=True)[:10]),
                }
        except Exception as e:
            logger.error("Failed to get conversation metrics", error=str(e))
            return {
                "period_days": days,
                "total_tickets": 0,
                "resolved": 0,
                "escalated": 0,
                "open": 0,
                "resolution_rate": 0,
                "escalation_rate": 0,
                "issue_types": {},
                "severity_breakdown": {},
                "kb_articles_usage": {},
            }

    async def get_common_issues(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get most common issues.

        Args:
            tenant_id: Optional tenant filter
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of issue dictionaries with counts
        """
        try:
            async with AsyncSessionLocal() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                stmt = select(SupportTicket).where(
                    SupportTicket.created_at >= cutoff_date
                )
                if tenant_id:
                    stmt = stmt.where(SupportTicket.tenant_id == tenant_id)

                result = await session.execute(stmt)
                tickets = list(result.scalars().all())

                issue_counts = {}
                for ticket in tickets:
                    issue_type = ticket.issue_type or "unknown"
                    issue_desc = ticket.issue_description or ""

                    key = f"{issue_type}: {issue_desc[:50]}" if issue_desc else issue_type
                    issue_counts[key] = issue_counts.get(key, 0) + 1

                sorted_issues = sorted(
                    issue_counts.items(), key=lambda x: x[1], reverse=True
                )[:limit]

                return [
                    {"issue": issue, "count": count}
                    for issue, count in sorted_issues
                ]
        except Exception as e:
            logger.error("Failed to get common issues", error=str(e))
            return []


analytics_service = AnalyticsService()
