"""SQLAlchemy database models."""

from datetime import datetime

from sqlalchemy import JSON, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class SupportTicket(Base):
    """IT support ticket record."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True)
    call_sid: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)

    # Ticket data
    issue_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True)
    severity: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True)
    priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    affected_systems: Mapped[list[str]] = mapped_column(
        JSON, nullable=True, default=list)
    error_messages: Mapped[list[str]] = mapped_column(
        JSON, nullable=True, default=list)
    user_environment: Mapped[str | None] = mapped_column(
        String(200), nullable=True)
    steps_to_reproduce: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolution
    status: Mapped[str] = mapped_column(
        String(50), default="open", nullable=False, index=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    kb_articles_used: Mapped[list[str]] = mapped_column(
        JSON, nullable=True, default=list)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)

    # External integration
    jira_ticket_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True)
    conversation_summary: Mapped[str |
                                 None] = mapped_column(Text, nullable=True)

    # Renamed from 'metadata' (SQLAlchemy reserved)
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class CallHistory(Base):
    """Call history record."""

    __tablename__ = "call_history"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    call_sid: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Renamed from 'metadata' (SQLAlchemy reserved)
    extra_data: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
