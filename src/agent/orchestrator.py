"""IT support orchestrator - main entry point for support calls."""

import uuid
from typing import Optional
from langchain_core.messages import HumanMessage

from src.agent.state import SupportTicketState
from src.agent.graph.graph import create_support_graph
from src.agent.checkpoint import get_checkpointer
from src.core.logging import get_logger
from src.services.conversation_logger import conversation_logger

logger = get_logger(__name__)


class SupportOrchestrator:
    """Orchestrator for managing IT support calls with LangGraph."""

    def __init__(self):
        self._graph = None

    def _get_graph(self):
        """Get or create graph with checkpointer."""
        if self._graph is None:
            checkpointer = get_checkpointer()
            self._graph = create_support_graph(checkpointer=checkpointer)
        return self._graph

    async def start_support(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        tenant_id: str = "default",
        session_id: Optional[str] = None,
    ) -> dict:
        """Start a new IT support call."""
        if not session_id:
            session_id = call_sid

        logger.info("Starting IT support call",
                    call_sid=call_sid, session_id=session_id, tenant_id=tenant_id)

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 100,
        }

        initial_state: SupportTicketState = {
            "messages": [],
            "call_sid": call_sid,
            "from_number": from_number,
            "to_number": to_number,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "ticket_data": {},
            "validated_ticket_data": {},
            "current_question": None,
            "troubleshooting_steps": [],
            "kb_context": None,
            "kb_articles_used": [],
            "escalation_reason": None,
            "is_resolved": False,
            "is_escalated": False,
            "is_complete": False,
        }

        try:
            graph = self._get_graph()
            result = await graph.ainvoke(initial_state, config=config)

            messages = result.get("messages", [])
            greeting_text = "Hello! How can I help you with your IT issue today?"
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    greeting_text = msg.content
                    break

            return {
                "greeting": greeting_text,
                "session_id": session_id,
            }
        except Exception as e:
            logger.error("Failed to start support call",
                         call_sid=call_sid, error=str(e), exc_info=True)
            raise

    async def process_user_response(
        self,
        call_sid: str,
        user_text: str,
        tenant_id: str = "default",
        session_id: Optional[str] = None,
    ) -> dict:
        """Process user response and get troubleshooting response."""
        if not session_id:
            session_id = call_sid

        logger.info("Processing user response",
                    call_sid=call_sid, user_text=user_text[:50], tenant_id=tenant_id)

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 100,
        }

        try:
            graph = self._get_graph()
            final_state = None

            async for chunk in graph.astream(
                {"messages": [HumanMessage(content=user_text)]},
                config=config,
            ):
                if isinstance(chunk, dict):
                    for node_name, node_output in chunk.items():
                        if isinstance(node_output, dict):
                            final_state = node_output

            if not final_state:
                logger.warning(
                    "astream didn't return state, falling back to ainvoke", call_sid=call_sid)
                final_state = await graph.ainvoke(
                    {"messages": [HumanMessage(content=user_text)]},
                    config=config,
                )

            result = final_state
            messages = result.get("messages", [])

            # Ensure user message is included in messages for logging
            has_user_message = any(
                (isinstance(msg, HumanMessage) and getattr(msg, "content", "") == user_text) or
                (isinstance(msg, dict) and msg.get("type") ==
                 "human" and msg.get("content") == user_text)
                for msg in messages
            )

            if not has_user_message and user_text:
                messages = [HumanMessage(content=user_text)] + list(messages)
                logger.debug("Added user message to log",
                             call_sid=call_sid, user_text=user_text[:50])

            response_text = "I understand. Let me help you with that."

            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    if hasattr(msg, "__class__") and "AIMessage" in str(type(msg)):
                        response_text = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get("type") == "ai":
                        response_text = msg.get("content", response_text)
                        break

            is_complete = result.get("is_complete", False)
            ticket_data = result.get("ticket_data", {})

            # Log conversation incrementally after each response (non-blocking)
            try:
                import asyncio
                asyncio.create_task(
                    asyncio.to_thread(
                        conversation_logger.log_conversation,
                        call_sid=call_sid,
                        messages=messages,
                        qualification_data=ticket_data,  # Reusing field name for compatibility
                        metadata={
                            "session_id": session_id,
                            "tenant_id": tenant_id,
                            "is_complete": is_complete,
                            "is_resolved": result.get("is_resolved", False),
                            "is_escalated": result.get("is_escalated", False),
                            "kb_articles_used": result.get("kb_articles_used", []),
                        }
                    )
                )
            except Exception as e:
                logger.warning("Failed to log incremental conversation",
                               call_sid=call_sid, error=str(e))

            return {
                "response": response_text,
                "session_id": session_id,
                "is_complete": is_complete,
                "ticket_data": ticket_data,
                "is_resolved": result.get("is_resolved", False),
                "is_escalated": result.get("is_escalated", False),
            }
        except Exception as e:
            logger.error("Error processing user response",
                         call_sid=call_sid, error=str(e), exc_info=True)
            raise


support_orchestrator = SupportOrchestrator()
