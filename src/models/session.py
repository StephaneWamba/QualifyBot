"""Session data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """Session state machine states."""

    INIT = "init"
    GREETING = "greeting"
    QUESTION_1 = "question_1"  # Company size
    QUESTION_2 = "question_2"  # Budget range
    QUESTION_3 = "question_3"  # Timeline
    QUESTION_4 = "question_4"  # Decision makers
    QUESTION_5 = "question_5"  # Current solution
    QUESTION_6 = "question_6"  # Primary use case
    SUMMARIZING = "summarizing"
    CREATING_LEAD = "creating_lead"
    COMPLETE = "complete"
    ERROR = "error"


class QualificationData(BaseModel):
    """Extracted qualification data."""

    company_size: int | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    timeline: str | None = None
    decision_makers: list[str] = Field(default_factory=list)
    current_solution: str | None = None
    use_case: str | None = None


class SessionData(BaseModel):
    """Session data model."""

    session_id: str
    call_sid: str
    from_number: str
    to_number: str
    state: SessionState = SessionState.INIT
    qualification_data: QualificationData = Field(default_factory=QualificationData)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "session_id": self.session_id,
            "call_sid": self.call_sid,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "state": self.state.value,
            "qualification_data": self.qualification_data.model_dump(),
            "conversation_history": self.conversation_history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create from dictionary."""
        data["state"] = SessionState(data["state"])
        data["qualification_data"] = QualificationData(**data["qualification_data"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


