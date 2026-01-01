"""Simple LLM-powered IT support agent - no heuristics, no over-engineering."""

from typing import Any
import uuid
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agent.state import SupportTicketState
from src.agent.company_config import agent_persona, company_config
from src.core.config import settings
from src.core.logging import get_logger
from src.services.kb_retrieval import kb_retrieval_service
from src.services.jira_service import jira_service
from src.services.ticket_service import ticket_service
from src.services.conversation_logger import conversation_logger
from src.services.caller_history_service import caller_history_service
from src.database.connection import AsyncSessionLocal

logger = get_logger(__name__)


def _get_system_prompt(kb_context: str | None = None, caller_history: str | None = None) -> str:
    """Generate optimized system prompt with context (minimal tokens for low latency)."""
    # Truncate KB context if too long (keep first 500 chars for speed)
    kb_section = ""
    if kb_context:
        kb_truncated = kb_context[:500] + \
            "..." if len(kb_context) > 500 else kb_context
        kb_section = f"\n\nKB:\n{kb_truncated}"

    history_section = f"\n\nHISTORY:\n{caller_history}" if caller_history else ""

    return f"""You are {agent_persona.name}, IT support.

Rules: ONE step at a time. Wait for confirmation. Conversational, not robotic. Answer naturally. Escalate if: user requests, security breach, hardware damage, or multiple attempts fail.

Style: Warm, helpful, patient.{history_section}{kb_section}

Respond: One step per message. Wait for confirmation."""


async def troubleshooting_node(state: SupportTicketState) -> dict[str, Any]:
    """Simple LLM-powered troubleshooting node - handles everything with LLM."""
    call_sid = state["call_sid"]
    tenant_id = state.get("tenant_id", "default")
    from_number = state.get("from_number", "")
    messages = state.get("messages", [])
    ticket_data = state.get("ticket_data", {})

    # Get last user message
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = getattr(msg, "content", str(msg))
            break

    # First message - send greeting
    if not messages:
        greeting = f"Hi there! This is {agent_persona.name} from {company_config.department}. How can I help you with your IT issue today?"
        return {
            "messages": [AIMessage(content=greeting)],
            "ticket_data": {},
            "kb_articles_used": [],
            "is_resolved": False,
            "is_escalated": False,
            "is_complete": False,
        }

    if not last_user_message:
        logger.warning("No user message found", call_sid=call_sid)
        return {}

    # Check for call ending
    user_message_lower = last_user_message.lower()
    if any(phrase in user_message_lower for phrase in ["goodbye", "bye", "that's all", "nothing else", "no thanks", "i'm done"]):
        closing_message = "Thanks for calling IT Support! Have a great day!"
        return {
            "messages": messages + [AIMessage(content=closing_message)],
            "is_complete": True,
        }

    # Get caller history for personalization
    caller_history_context = ""
    try:
        if from_number:
            caller_history_context = await caller_history_service.get_personalization_context(
                from_number, tenant_id
            )
    except Exception as e:
        logger.debug("Could not get caller history",
                     call_sid=call_sid, error=str(e))

    # Get KB context if user mentions a technical issue
    kb_context = None
    kb_articles_used = state.get("kb_articles_used", [])

    # Simple heuristic: only get KB if user mentions technical keywords
    technical_keywords = ["printer", "email", "wifi", "vpn", "network", "computer", "laptop",
                          "not working", "issue", "problem", "error", "broken", "can't", "unable"]
    if any(keyword in user_message_lower for keyword in technical_keywords):
        try:
            kb_chunks = await kb_retrieval_service.retrieve_relevant_context(
                tenant_id=tenant_id,
                query=last_user_message,
            )
            if kb_chunks:
                kb_context = await kb_retrieval_service.format_context_for_prompt(kb_chunks)
                for chunk in kb_chunks:
                    doc_name = chunk.get("metadata", {}).get(
                        "document_name", "Unknown")
                    if doc_name not in kb_articles_used:
                        kb_articles_used.append(doc_name)
        except Exception as e:
            logger.warning("KB retrieval failed",
                           call_sid=call_sid, error=str(e))

    # Build optimized conversation history (last 6 messages for lower latency)
    conversation_history = []
    for msg in messages[-6:]:  # Reduced from 10 to 6 for lower latency
        if isinstance(msg, HumanMessage):
            conversation_history.append(
                f"U: {getattr(msg, 'content', str(msg))}")
        elif isinstance(msg, AIMessage):
            conversation_history.append(
                f"A: {getattr(msg, 'content', str(msg))}")

    # Let LLM handle everything (optimized for low latency)
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
        timeout=10.0,  # Reduced from 15s to 10s
        max_tokens=200,  # Limit response length for faster generation
    )

    system_prompt = _get_system_prompt(
        kb_context=kb_context, caller_history=caller_history_context)

    # Build optimized prompt with conversation context
    prompt = f"""Chat:
{chr(10).join(conversation_history)}

User: {last_user_message}

Respond: One step if technical issue. Answer if question. Next step if confirmed. Friendly closing if goodbye."""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])

        agent_response = response.content.strip(
        ) if response and response.content else "I understand. How can I help you?"

        # Clean response
        for prefix in ["Assistant:", "Assistant ", f"{agent_persona.name}:", "Jordan:"]:
            if agent_response.startswith(prefix):
                agent_response = agent_response.replace(prefix, "", 1).strip()

        # Check if LLM wants to escalate (simple keyword check in response)
        should_escalate = any(phrase in agent_response.lower() for phrase in [
            "escalat", "human support", "speak to someone", "connect you with"
        ])

        # Check if resolved
        is_resolved = any(phrase in user_message_lower for phrase in [
            "resolved", "fixed", "working", "it works", "all good", "solved"
        ])

        # Extract ticket data if technical issue
        if any(keyword in user_message_lower for keyword in technical_keywords):
            # Simple extraction - just store what user said
            if not ticket_data.get("issue_description"):
                ticket_data["issue_description"] = last_user_message
            if not ticket_data.get("issue_type"):
                # Simple type detection
                if "printer" in user_message_lower:
                    ticket_data["issue_type"] = "hardware"
                elif "email" in user_message_lower:
                    ticket_data["issue_type"] = "email"
                elif "wifi" in user_message_lower or "network" in user_message_lower:
                    ticket_data["issue_type"] = "network"
                else:
                    ticket_data["issue_type"] = "general"

        # Handle escalation
        if should_escalate:
            try:
                session_id = state.get("session_id", call_sid)
                from_number = state.get("from_number", "")
                to_number = state.get("to_number", "")

                # Create Jira ticket
                jira_ticket_key = None
                try:
                    jira_ticket_key = await jira_service.create_ticket(
                        summary=f"IT Support: {ticket_data.get('issue_type', 'General')} Issue",
                        description=ticket_data.get(
                            "issue_description", "User requested escalation"),
                        issue_type="Task",
                        priority="Medium",
                        labels=["voice-support", "escalated"],
                    )
                except Exception as e:
                    logger.error("Failed to create Jira ticket",
                                 call_sid=call_sid, error=str(e))

                # Save to database
                try:
                    ticket_id = f"TICKET-{call_sid[:8]}-{uuid.uuid4().hex[:8]}"
                    async with AsyncSessionLocal() as db_session:
                        await ticket_service.create_or_update_ticket(
                            session=db_session,
                            ticket_id=ticket_id,
                            call_sid=call_sid,
                            session_id=session_id,
                            tenant_id=tenant_id,
                            from_number=from_number,
                            to_number=to_number,
                            ticket_data=ticket_data,
                            conversation_summary=f"Issue: {ticket_data.get('issue_description', 'Unknown')}",
                            jira_ticket_key=jira_ticket_key,
                            status="escalated",
                            kb_articles_used=kb_articles_used,
                        )
                        await db_session.commit()
                except Exception as e:
                    logger.error("Failed to save ticket",
                                 call_sid=call_sid, error=str(e))
            except Exception as e:
                logger.error("Escalation handling failed",
                             call_sid=call_sid, error=str(e))

        # Handle resolution
        if is_resolved:
            try:
                session_id = state.get("session_id", call_sid)
                from_number = state.get("from_number", "")
                to_number = state.get("to_number", "")

                ticket_id = f"TICKET-{call_sid[:8]}-{uuid.uuid4().hex[:8]}"
                async with AsyncSessionLocal() as db_session:
                    await ticket_service.create_or_update_ticket(
                        session=db_session,
                        ticket_id=ticket_id,
                        call_sid=call_sid,
                        session_id=session_id,
                        tenant_id=tenant_id,
                        from_number=from_number,
                        to_number=to_number,
                        ticket_data=ticket_data,
                        conversation_summary=f"Issue resolved: {ticket_data.get('issue_description', 'Unknown')}",
                        status="resolved",
                        resolution="Issue resolved through automated troubleshooting",
                        kb_articles_used=kb_articles_used,
                    )
                    await db_session.commit()
            except Exception as e:
                logger.error("Failed to save resolved ticket",
                             call_sid=call_sid, error=str(e))

        # Log conversation
        try:
            import asyncio
            asyncio.create_task(
                asyncio.to_thread(
                    conversation_logger.log_conversation,
                    call_sid=call_sid,
                    messages=messages + [AIMessage(content=agent_response)],
                    qualification_data=ticket_data,
                    metadata={
                        "session_id": state.get("session_id", call_sid),
                        "is_resolved": is_resolved,
                        "is_escalated": should_escalate,
                        "kb_articles_used": kb_articles_used,
                    }
                )
            )
        except Exception as e:
            logger.warning("Failed to log conversation",
                           call_sid=call_sid, error=str(e))

        return {
            "messages": messages + [AIMessage(content=agent_response)],
            "ticket_data": ticket_data,
            "kb_articles_used": kb_articles_used,
            "is_resolved": is_resolved,
            "is_escalated": should_escalate,
            "is_complete": False,
        }

    except Exception as e:
        logger.error("LLM call failed", call_sid=call_sid,
                     error=str(e), exc_info=True)
        # Fallback response
        return {
            "messages": messages + [AIMessage(content="I'm sorry, I'm having technical difficulties. Please try again.")],
            "ticket_data": ticket_data,
            "is_resolved": False,
            "is_escalated": False,
            "is_complete": False,
        }
