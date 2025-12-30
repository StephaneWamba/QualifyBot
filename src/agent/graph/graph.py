"""LangGraph graph definition for qualification flow."""

from typing import Literal, Optional
from langgraph.graph import StateGraph, END

# Try to import Redis checkpointer, fallback to Any
try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
except ImportError:
    from typing import Any
    AsyncRedisSaver = Any  # type: ignore

from src.agent.state import QualificationState
from src.agent.graph.nodes import (
    greeting_node,
    question_node,
    extract_answer_node,
    summarize_node,
    create_lead_node,
)
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_qualification_graph(
    checkpointer: Optional[AsyncRedisSaver] = None,
):
    """Create the LangGraph qualification graph."""
    # Create graph
    graph = StateGraph(QualificationState)
    
    # Add nodes
    graph.add_node("greeting", greeting_node)
    graph.add_node("question", question_node)
    graph.add_node("extract_answer", extract_answer_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("create_lead", create_lead_node)
    
    # Set entry point
    graph.set_entry_point("greeting")
    
    # Define flow
    # greeting -> question
    graph.add_edge("greeting", "question")
    
    # question -> extract_answer if user message exists, else END
    def should_extract(state: QualificationState) -> Literal["extract_answer", "__end__"]:
        """Check if we should extract answer or wait for user input."""
        messages = state.get("messages", [])
        # Check if last message is from user
        if messages:
            last_msg = messages[-1]
            # Check if it's a HumanMessage
            if hasattr(last_msg, "__class__"):
                if "HumanMessage" in str(type(last_msg)):
                    return "extract_answer"
            elif isinstance(last_msg, dict) and last_msg.get("type") == "human":
                return "extract_answer"
        # No user message, wait (END)
        return "__end__"
    
    graph.add_conditional_edges(
        "question",
        should_extract,
        {
            "extract_answer": "extract_answer",
            "__end__": END,
        },
    )
    
    # extract_answer -> question (next question) or summarize (if complete)
    def next_after_extract(state: QualificationState) -> Literal["question", "summarize"]:
        """Determine next step after extracting answer."""
        question_index = state.get("question_index", 0)
        if question_index >= 6:  # All questions answered
            return "summarize"
        return "question"
    
    graph.add_conditional_edges(
        "extract_answer",
        next_after_extract,
        {
            "question": "question",
            "summarize": "summarize",
        },
    )
    
    # summarize -> create_lead
    graph.add_edge("summarize", "create_lead")
    
    # create_lead -> END
    graph.add_edge("create_lead", END)
    
    # Compile graph with checkpointer if provided
    if checkpointer:
        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        compiled_graph = graph.compile()
    
    logger.info("Qualification graph created")
    
    return compiled_graph

