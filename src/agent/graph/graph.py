"""LangGraph graph definition for IT support ticket flow."""

from typing import Optional
from langgraph.graph import StateGraph, START, END

try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
except ImportError:
    from typing import Any
    AsyncRedisSaver = Any

from src.agent.state import SupportTicketState
from src.agent.graph.nodes import troubleshooting_node
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_support_graph(checkpointer: Optional[AsyncRedisSaver] = None):
    """Create IT support LangGraph - single node handles troubleshooting flow."""
    graph = StateGraph(SupportTicketState)

    # Single node that handles greeting, troubleshooting, and resolution
    graph.add_node("troubleshooting", troubleshooting_node)

    # Always start at troubleshooting node
    graph.add_edge(START, "troubleshooting")

    # Always end after troubleshooting node (will resume from checkpoint on next input)
    graph.add_edge("troubleshooting", END)

    if checkpointer:
        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        compiled_graph = graph.compile()

    return compiled_graph
