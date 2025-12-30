"""Qualification orchestrator - main entry point for qualification calls."""

import uuid
from typing import Optional
from langchain_core.messages import HumanMessage

from src.agent.state import QualificationState
from src.agent.graph.graph import create_qualification_graph
from src.agent.checkpoint import get_checkpointer
from src.core.logging import get_logger

logger = get_logger(__name__)


class QualificationOrchestrator:
    """Orchestrator for managing qualification calls with LangGraph."""

    def __init__(self):
        """Initialize the orchestrator."""
        self._graph = None

    def _get_graph(self):
        """Get or create graph with checkpointer."""
        if self._graph is None:
            checkpointer = get_checkpointer()
            self._graph = create_qualification_graph(checkpointer=checkpointer)
        return self._graph

    async def start_qualification(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Start a new qualification call.

        Args:
            call_sid: Twilio Call SID
            from_number: Caller's phone number
            to_number: Called phone number
            session_id: Optional session ID (defaults to call_sid)

        Returns:
            Initial greeting message
        """
        if not session_id:
            session_id = call_sid

        logger.info("Starting qualification",
                    call_sid=call_sid, session_id=session_id)

        # Create config for this conversation thread
        config = {
            "configurable": {
                "thread_id": session_id,
            },
            "recursion_limit": 100,  # Allow for full qualification flow
        }

        # Create initial state
        initial_state: QualificationState = {
            "messages": [],  # Empty - greeting node will add first message
            "call_sid": call_sid,
            "from_number": from_number,
            "to_number": to_number,
            "session_id": session_id,
            "qualification_data": {},
            "current_question": None,
            "question_index": 0,
            "is_complete": False,
        }

        try:
            # Get graph
            graph = self._get_graph()

            # Invoke graph to get greeting and first question
            # Graph will run: greeting -> question -> END
            result = await graph.ainvoke(initial_state, config=config)

            # Extract greeting message
            messages = result.get("messages", [])
            greeting_text = "Hello! Thanks for calling."
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    greeting_text = msg.content
                    break

            logger.info("Qualification started", call_sid=call_sid,
                        greeting=greeting_text[:50])

            return {
                "greeting": greeting_text,
                "session_id": session_id,
            }
        except Exception as e:
            logger.error("Failed to start qualification",
                         call_sid=call_sid, error=str(e))
            raise

    async def process_user_response(
        self,
        call_sid: str,
        user_text: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Process user response and get next question/action.

        Args:
            call_sid: Twilio Call SID
            user_text: Transcribed user response
            session_id: Session ID (defaults to call_sid)

        Returns:
            Next message/action from agent
        """
        if not session_id:
            session_id = call_sid

        logger.info(
            "Processing user response",
            call_sid=call_sid,
            session_id=session_id,
            user_text=user_text[:50],
        )

        # Create config for this conversation thread
        config = {
            "configurable": {
                "thread_id": session_id,
            },
            "recursion_limit": 100,
        }

        try:
            # Get graph
            graph = self._get_graph()

            # Simply invoke with the user message
            # The checkpointer will automatically restore previous state and merge
            # The graph will detect the user message and route to extract_answer
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_text)]},
                config=config,
            )

            # Extract response
            messages = result.get("messages", [])
            response_text = "I understand. Let me continue."

            # Get last AI message
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    # Check if it's an AI message
                    if hasattr(msg, "__class__") and "AIMessage" in str(type(msg)):
                        response_text = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get("type") == "ai":
                        response_text = msg.get("content", response_text)
                        break

            # Check if complete
            is_complete = result.get("is_complete", False)
            qualification_data = result.get("qualification_data", {})

            logger.info(
                "User response processed",
                call_sid=call_sid,
                response_length=len(response_text),
                is_complete=is_complete,
            )

            return {
                "response": response_text,
                "session_id": session_id,
                "is_complete": is_complete,
                "qualification_data": qualification_data,
            }
        except Exception as checkpoint_error:
            # Handle corrupted checkpoint state
            error_str = str(checkpoint_error)
            if "tool_call_id" in error_str and "did not have response" in error_str:
                logger.warning(
                    f"Corrupted checkpoint state detected for session {session_id}. Creating new session."
                )
                # Retry with new session
                session_id = str(uuid.uuid4())
                config = {
                    "configurable": {"thread_id": session_id},
                    "recursion_limit": 100,
                }
                result = await graph.ainvoke(initial_state, config=config)
                # Extract response as above
                messages = result.get("messages", [])
                response_text = "I understand. Let me continue."
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        response_text = msg.content
                        break
                return {
                    "response": response_text,
                    "session_id": session_id,
                    "is_complete": result.get("is_complete", False),
                }
            else:
                logger.error("Error processing user response",
                             call_sid=call_sid, error=str(checkpoint_error))
                raise


# Singleton instance
qualification_orchestrator = QualificationOrchestrator()
