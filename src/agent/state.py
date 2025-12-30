"""Qualification agent state schema for LangGraph."""

from typing import Annotated, TypedDict, Sequence
from langgraph.graph.message import AnyMessage, add_messages


class QualificationState(TypedDict):
    """State schema for the qualification graph."""

    messages: Annotated[Sequence[AnyMessage], add_messages]
    call_sid: str
    from_number: str
    to_number: str
    session_id: str
    qualification_data: dict  # Extracted qualification answers
    current_question: str | None  # Current question being asked
    question_index: int  # Index of current question (0-6)
    is_complete: bool  # Whether qualification is complete


