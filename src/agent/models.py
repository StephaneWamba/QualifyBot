"""Pydantic models for IT ticket data extraction."""

from typing import Optional
from pydantic import BaseModel, Field


class TicketDataExtraction(BaseModel):
    """Structured IT ticket data extraction model for instructor."""
    issue_type: Optional[str] = Field(None, description="Type of issue (e.g., 'hardware', 'software', 'network', 'email', 'access')")
    severity: Optional[str] = Field(None, description="Severity level (e.g., 'critical', 'high', 'medium', 'low')")
    affected_systems: list[str] = Field(default_factory=list, description="List of affected systems or applications")
    error_messages: list[str] = Field(default_factory=list, description="Error messages or codes encountered")
    user_environment: Optional[str] = Field(None, description="User's environment (e.g., 'Windows 11', 'macOS', 'mobile', 'web browser')")
    steps_to_reproduce: Optional[str] = Field(None, description="Steps to reproduce the issue")
    issue_description: Optional[str] = Field(None, description="Detailed description of the issue")

