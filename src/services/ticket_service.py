"""Service for managing support tickets in the database."""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import SupportTicket
from src.core.logging import get_logger

logger = get_logger(__name__)


class TicketService:
    """Service for managing support ticket records in the database."""

    async def create_or_update_ticket(
        self,
        session: AsyncSession,
        ticket_id: str,
        call_sid: str,
        session_id: str,
        tenant_id: str,
        from_number: str,
        to_number: str,
        ticket_data: dict,
        conversation_summary: Optional[str] = None,
        jira_ticket_key: Optional[str] = None,
        priority_score: Optional[int] = None,
        severity: Optional[str] = None,
        status: str = "open",
        resolution: Optional[str] = None,
        kb_articles_used: Optional[list[str]] = None,
    ) -> SupportTicket:
        """
        Create or update a support ticket record.

        Args:
            session: Database session
            ticket_id: Unique ticket identifier
            call_sid: Twilio Call SID
            session_id: Session ID
            tenant_id: Tenant identifier
            from_number: Caller's phone number
            to_number: Called phone number
            ticket_data: Ticket data dictionary
            conversation_summary: Optional conversation summary
            jira_ticket_key: Optional Jira ticket key
            priority_score: Optional priority score
            severity: Optional severity level
            status: Ticket status (default: "open")
            resolution: Optional resolution description
            kb_articles_used: Optional list of KB articles used

        Returns:
            SupportTicket
        """
        stmt = select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            # Update existing ticket
            record.issue_type = ticket_data.get("issue_type")
            record.severity = severity or ticket_data.get("severity")
            record.priority_score = priority_score
            record.affected_systems = ticket_data.get("affected_systems", [])
            record.error_messages = ticket_data.get("error_messages", [])
            record.user_environment = ticket_data.get("user_environment")
            record.steps_to_reproduce = ticket_data.get("steps_to_reproduce")
            record.issue_description = ticket_data.get("issue_description")
            record.status = status
            if resolution:
                record.resolution = resolution
                record.resolved_at = datetime.utcnow()
            if jira_ticket_key:
                record.jira_ticket_key = jira_ticket_key
            if conversation_summary:
                record.conversation_summary = conversation_summary
            if kb_articles_used:
                record.kb_articles_used = kb_articles_used
            record.updated_at = datetime.utcnow()
            logger.info("Updated support ticket", ticket_id=ticket_id, call_sid=call_sid)
        else:
            # Create new ticket
            record = SupportTicket(
                ticket_id=ticket_id,
                call_sid=call_sid,
                session_id=session_id,
                tenant_id=tenant_id,
                from_number=from_number,
                to_number=to_number,
                issue_type=ticket_data.get("issue_type"),
                severity=severity or ticket_data.get("severity"),
                priority_score=priority_score,
                affected_systems=ticket_data.get("affected_systems", []),
                error_messages=ticket_data.get("error_messages", []),
                user_environment=ticket_data.get("user_environment"),
                steps_to_reproduce=ticket_data.get("steps_to_reproduce"),
                issue_description=ticket_data.get("issue_description"),
                status=status,
                resolution=resolution,
                resolved_at=datetime.utcnow() if resolution else None,
                jira_ticket_key=jira_ticket_key,
                conversation_summary=conversation_summary,
                kb_articles_used=kb_articles_used or [],
            )
            session.add(record)
            logger.info("Created support ticket", ticket_id=ticket_id, call_sid=call_sid)

        await session.flush()
        return record

    async def get_ticket_by_ticket_id(
        self,
        session: AsyncSession,
        ticket_id: str,
    ) -> Optional[SupportTicket]:
        """
        Get support ticket by ticket ID.

        Args:
            session: Database session
            ticket_id: Ticket ID

        Returns:
            SupportTicket or None
        """
        stmt = select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tickets_by_call_sid(
        self,
        session: AsyncSession,
        call_sid: str,
    ) -> list[SupportTicket]:
        """
        Get all tickets for a call SID.

        Args:
            session: Database session
            call_sid: Call SID

        Returns:
            List of SupportTicket objects
        """
        stmt = select(SupportTicket).where(SupportTicket.call_sid == call_sid)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_tickets_by_phone(
        self,
        session: AsyncSession,
        from_number: str,
        tenant_id: Optional[str] = None,
    ) -> list[SupportTicket]:
        """
        Get all tickets for a phone number.

        Args:
            session: Database session
            from_number: Phone number
            tenant_id: Optional tenant filter

        Returns:
            List of SupportTicket objects
        """
        stmt = select(SupportTicket).where(SupportTicket.from_number == from_number)
        if tenant_id:
            stmt = stmt.where(SupportTicket.tenant_id == tenant_id)
        stmt = stmt.order_by(SupportTicket.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())


ticket_service = TicketService()

