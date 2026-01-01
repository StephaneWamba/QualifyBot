"""Analytics API routes for conversation and ticket metrics."""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.services.analytics_service import analytics_service
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class MetricsResponse(BaseModel):
    """Response model for conversation metrics."""
    period_days: int
    total_tickets: int
    resolved: int
    escalated: int
    open: int
    resolution_rate: float
    escalation_rate: float
    issue_types: dict[str, int]
    severity_breakdown: dict[str, int]
    kb_articles_usage: dict[str, int]


class CommonIssue(BaseModel):
    """Common issue model."""
    issue: str
    count: int


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    days: int = Query(30, ge=1, le=365,
                      description="Number of days to look back"),
):
    """
    Get conversation and ticket analytics metrics.

    Returns:
        MetricsResponse with various analytics data
    """
    logger.info("Fetching analytics metrics", tenant_id=tenant_id, days=days)
    metrics = await analytics_service.get_conversation_metrics(
        tenant_id=tenant_id, days=days
    )
    return MetricsResponse(**metrics)


@router.get("/common-issues", response_model=list[CommonIssue])
async def get_common_issues(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    days: int = Query(30, ge=1, le=365,
                      description="Number of days to look back"),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of results"),
):
    """
    Get most common issues.

    Returns:
        List of common issues with counts
    """
    logger.info("Fetching common issues",
                tenant_id=tenant_id, days=days, limit=limit)
    issues = await analytics_service.get_common_issues(
        tenant_id=tenant_id, days=days, limit=limit
    )
    return [CommonIssue(**issue) for issue in issues]
