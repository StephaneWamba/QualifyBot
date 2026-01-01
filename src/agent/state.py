"""IT support agent state schema for LangGraph."""

from typing import Annotated, TypedDict, Sequence
from langgraph.graph.message import AnyMessage, add_messages


class SupportTicketState(TypedDict):
    """State schema for the IT support ticket graph."""

    messages: Annotated[Sequence[AnyMessage], add_messages]
    call_sid: str
    from_number: str
    to_number: str
    session_id: str
    tenant_id: str  # Multi-tenant support
    ticket_data: dict  # All extracted ticket data (may include invalid)
    validated_ticket_data: dict  # Only validated, meaningful ticket data
    current_question: str | None  # Current question being asked
    troubleshooting_steps: list[str]  # Steps attempted so far
    current_instruction_step: int  # Current step number in instruction sequence (0 = first step)
    instruction_sequence: list[str]  # List of all instructions to give one at a time
    kb_context: str | None  # Retrieved KB context for current issue
    # KB articles referenced during troubleshooting
    kb_articles_used: list[str]
    escalation_reason: str | None  # Reason for escalation if needed
    is_resolved: bool  # Whether issue is resolved
    is_escalated: bool  # Whether ticket was escalated to human
    is_complete: bool  # Whether conversation is complete
