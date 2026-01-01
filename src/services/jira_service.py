"""Jira service for creating and managing IT support tickets."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from jira import JIRA
from jira.exceptions import JIRAError

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=5)


class JiraService:
    """Service for Jira operations with async support."""

    def __init__(self):
        self.client = None
        self._initialized = False

    async def _ensure_connected(self):
        """Ensure Jira connection is established."""
        if not self._initialized:
            if not all([
                settings.JIRA_SERVER,
                settings.JIRA_EMAIL,
                settings.JIRA_API_TOKEN,
            ]):
                logger.warning(
                    "Jira credentials not configured",
                    has_server=bool(settings.JIRA_SERVER),
                    has_email=bool(settings.JIRA_EMAIL),
                    has_token=bool(settings.JIRA_API_TOKEN),
                )
                return False

            try:
                # Remove trailing slash from server URL if present
                server_url = settings.JIRA_SERVER.rstrip("/")

                loop = asyncio.get_event_loop()
                self.client = await loop.run_in_executor(
                    _executor,
                    lambda: JIRA(
                        server=server_url,
                        basic_auth=(settings.JIRA_EMAIL,
                                    settings.JIRA_API_TOKEN),
                    ),
                )
                self._initialized = True
                logger.info("Jira connection established",
                            server=settings.JIRA_SERVER)
                return True
            except Exception as e:
                logger.error("Failed to connect to Jira", error=str(
                    e), error_type=type(e).__name__, exc_info=True)
                self._initialized = False
                return False
        return True

    async def create_ticket(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Create a Jira ticket.

        Args:
            summary: Ticket summary/title
            description: Detailed description
            issue_type: Jira issue type (Task, Bug, Story, etc.)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: Optional list of labels
            custom_fields: Optional custom field values

        Returns:
            Jira ticket key (e.g., "IT-123") or None if failed
        """
        connected = await self._ensure_connected()
        if not connected:
            error_msg = "Jira not connected. Check credentials and connection logs."
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            issue_dict = {
                "project": {"key": settings.JIRA_PROJECT_KEY},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }

            if priority:
                issue_dict["priority"] = {"name": priority}

            if labels:
                issue_dict["labels"] = labels

            if custom_fields:
                issue_dict.update(custom_fields)

            loop = asyncio.get_event_loop()
            issue = await loop.run_in_executor(
                _executor,
                lambda: self.client.create_issue(fields=issue_dict),
            )

            ticket_key = issue.key
            logger.info("Jira ticket created",
                        ticket_key=ticket_key, summary=summary[:50])
            return ticket_key

        except JIRAError as e:
            logger.error("Jira API error", error=str(
                e), error_code=e.status_code, exc_info=True)
            raise
        except Exception as e:
            logger.error("Failed to create Jira ticket", error=str(
                e), error_type=type(e).__name__, exc_info=True)
            raise

    async def update_ticket(
        self,
        ticket_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> bool:
        """
        Update a Jira ticket.

        Args:
            ticket_key: Jira ticket key (e.g., "IT-123")
            summary: Optional new summary
            description: Optional new description
            status: Optional new status
            priority: Optional new priority
            resolution: Optional resolution

        Returns:
            True if successful
        """
        connected = await self._ensure_connected()
        if not connected:
            raise ValueError("Jira not connected")

        try:
            issue = self.client.issue(ticket_key)
            update_fields = {}

            if summary:
                update_fields["summary"] = summary
            if description:
                update_fields["description"] = description
            if priority:
                update_fields["priority"] = {"name": priority}

            if update_fields:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: issue.update(fields=update_fields),
                )

            if status:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: self.client.transition_issue(issue, status),
                )

            if resolution:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: issue.update(
                        fields={"resolution": {"name": resolution}}),
                )

            logger.info("Jira ticket updated", ticket_key=ticket_key)
            return True

        except JIRAError as e:
            logger.error("Jira API error", ticket_key=ticket_key,
                         error=str(e), error_code=e.status_code)
            raise
        except Exception as e:
            logger.error("Failed to update Jira ticket",
                         ticket_key=ticket_key, error=str(e))
            raise

    async def get_ticket(self, ticket_key: str) -> Optional[dict]:
        """
        Get ticket details from Jira.

        Args:
            ticket_key: Jira ticket key

        Returns:
            Ticket details dictionary or None
        """
        connected = await self._ensure_connected()
        if not connected:
            return None

        try:
            loop = asyncio.get_event_loop()
            issue = await loop.run_in_executor(
                _executor,
                lambda: self.client.issue(ticket_key),
            )

            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
            }

        except Exception as e:
            logger.error("Failed to get Jira ticket",
                         ticket_key=ticket_key, error=str(e))
            return None


jira_service = JiraService()
