"""LangGraph node implementations for qualification flow."""

from typing import Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agent.state import QualificationState
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Qualification questions
QUALIFICATION_QUESTIONS = [
    "What's the size of your company? (number of employees)",
    "What's your budget range for this solution?",
    "What's your timeline for implementation?",
    "Who are the key decision makers in this process?",
    "What's your current solution or process for this?",
    "What's the primary use case you're looking to solve?",
]


def _get_system_prompt() -> str:
    """Generate system prompt for qualification agent."""
    return """You are a sales qualification assistant conducting a phone call to qualify leads.

Your role:
1. Ask clear, concise questions to gather qualification information
2. Extract structured data from the prospect's responses
3. Be friendly, professional, and conversational
4. Handle interruptions gracefully
5. Move to the next question once you have a clear answer

Qualification Questions:
1. Company size (number of employees)
2. Budget range
3. Timeline for implementation
4. Decision makers
5. Current solution
6. Primary use case

Guidelines:
- Keep questions short and natural
- Extract specific information (numbers, names, dates)
- If the answer is unclear, ask a clarifying follow-up
- Once you have an answer, acknowledge it and move to the next question
- Be conversational, not robotic
"""


async def greeting_node(state: QualificationState) -> dict[str, Any]:
    """Greeting node - initial welcome message."""
    logger.info("Greeting node", call_sid=state["call_sid"])
    
    greeting_text = (
        "Hello! Thanks for calling. I'll ask you a few quick questions "
        "to understand your needs better. Sound good?"
    )
    
    return {
        "messages": [AIMessage(content=greeting_text)],
        "current_question": None,
        "question_index": 0,
        "is_complete": False,
    }


async def question_node(state: QualificationState) -> dict[str, Any]:
    """Ask the current qualification question."""
    question_index = state.get("question_index", 0)
    
    if question_index >= len(QUALIFICATION_QUESTIONS):
        # All questions answered, move to summarize
        return {
            "messages": [],
            "is_complete": True,
        }
    
    question = QUALIFICATION_QUESTIONS[question_index]
    logger.info(
        "Asking question",
        call_sid=state["call_sid"],
        question_index=question_index,
        question=question,
    )
    
    # Get conversation context
    messages = state.get("messages", [])
    
    # Use LLM to generate natural question
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
    )
    
    # Build context
    system_prompt = _get_system_prompt()
    conversation_context = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {getattr(msg, 'content', str(msg))}"
        for msg in messages[-5:]  # Last 5 messages for context
    ])
    
    prompt = f"""Based on the conversation so far:
{conversation_context}

Ask the next qualification question naturally: "{question}"

Make it conversational and friendly. Keep it short."""
    
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ])
    
    question_text = response.content
    
    return {
        "messages": [AIMessage(content=question_text)],
        "current_question": question,
        "question_index": question_index,
    }


async def extract_answer_node(state: QualificationState) -> dict[str, Any]:
    """Extract structured answer from user response."""
    question_index = state.get("question_index", 0)
    current_question = state.get("current_question")
    messages = state.get("messages", [])
    
    if not current_question or question_index >= len(QUALIFICATION_QUESTIONS):
        return {}
    
    # Get last user message
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = getattr(msg, "content", str(msg))
            break
        elif hasattr(msg, "__class__") and "HumanMessage" in str(type(msg)):
            last_user_message = getattr(msg, "content", str(msg))
            break
    
    if not last_user_message:
        logger.warning("No user message found for extraction", call_sid=state["call_sid"])
        return {}
    
    logger.info(
        "Extracting answer",
        call_sid=state["call_sid"],
        question_index=question_index,
        user_response=last_user_message[:50],
    )
    
    # Use LLM to extract structured data
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,  # Lower temperature for extraction
        api_key=settings.OPENAI_API_KEY,
    )
    
    extraction_prompt = f"""Extract the answer to this qualification question:

Question: {current_question}
User Response: {last_user_message}

Extract the key information as JSON:
- For company size: extract the number (e.g., {{"company_size": 50}})
- For budget: extract min and max if mentioned (e.g., {{"budget_min": 10000, "budget_max": 50000}})
- For timeline: extract the timeline description (e.g., {{"timeline": "Q2 2024"}})
- For decision makers: extract list of names/roles (e.g., {{"decision_makers": ["John Doe", "Jane Smith"]}})
- For current solution: extract the solution name/description (e.g., {{"current_solution": "Manual process"}})
- For use case: extract the primary use case (e.g., {{"use_case": "Customer support automation"}})

Return only valid JSON, no other text."""
    
    response = await llm.ainvoke([
        SystemMessage(content="You are a data extraction assistant. Extract structured data from text."),
        HumanMessage(content=extraction_prompt),
    ])
    
    # Parse JSON response
    import json
    try:
        extracted_data = json.loads(response.content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[^}]+\}', response.content)
        if json_match:
            extracted_data = json.loads(json_match.group())
        else:
            extracted_data = {}
    
    # Update qualification data
    qualification_data = state.get("qualification_data", {})
    qualification_data.update(extracted_data)
    
    logger.info(
        "Answer extracted",
        call_sid=state["call_sid"],
        extracted_data=extracted_data,
    )
    
    return {
        "qualification_data": qualification_data,
        "question_index": question_index + 1,  # Move to next question
    }


async def summarize_node(state: QualificationState) -> dict[str, Any]:
    """Summarize the qualification conversation."""
    logger.info("Summarizing conversation", call_sid=state["call_sid"])
    
    qualification_data = state.get("qualification_data", {})
    messages = state.get("messages", [])
    
    # Generate summary using LLM
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.5,
        api_key=settings.OPENAI_API_KEY,
    )
    
    conversation_text = "\n".join([
        f"{'Prospect' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
        for msg in messages
    ])
    
    summary_prompt = f"""Summarize this qualification call:

Conversation:
{conversation_text}

Qualification Data:
{qualification_data}

Create a concise summary highlighting:
1. Key qualification information
2. Prospect's needs and pain points
3. Next steps or recommendations

Keep it professional and actionable."""
    
    response = await llm.ainvoke([
        SystemMessage(content="You are a sales assistant summarizing qualification calls."),
        HumanMessage(content=summary_prompt),
    ])
    
    summary = response.content
    
    return {
        "messages": [AIMessage(content=f"Thank you! I've gathered all the information. Here's a summary: {summary}")],
    }


async def create_lead_node(state: QualificationState) -> dict[str, Any]:
    """Create lead in Salesforce."""
    from src.services.salesforce_service import salesforce_service
    
    logger.info("Creating Salesforce lead", call_sid=state["call_sid"])
    
    qualification_data = state.get("qualification_data", {})
    from_number = state.get("from_number", "")
    
    try:
        # Create lead in Salesforce
        lead_data = {
            "FirstName": qualification_data.get("first_name", "Unknown"),
            "LastName": qualification_data.get("last_name", "Unknown"),
            "Phone": from_number,
            "Company": qualification_data.get("company", "Unknown"),
            "Company_Size__c": qualification_data.get("company_size"),
            "Budget_Min__c": qualification_data.get("budget_min"),
            "Budget_Max__c": qualification_data.get("budget_max"),
            "Timeline__c": qualification_data.get("timeline"),
            "Current_Solution__c": qualification_data.get("current_solution"),
            "Use_Case__c": qualification_data.get("use_case"),
            "LeadSource": "Phone Call",
        }
        
        lead_id = await salesforce_service.create_lead(lead_data)
        
        logger.info("Lead created", call_sid=state["call_sid"], lead_id=lead_id)
        
        return {
            "messages": [AIMessage(content=f"Perfect! I've saved your information. Our team will reach out soon. Have a great day!")],
        }
    except Exception as e:
        logger.error("Failed to create lead", call_sid=state["call_sid"], error=str(e))
        return {
            "messages": [AIMessage(content="Thank you for your time! Our team will be in touch soon.")],
        }

