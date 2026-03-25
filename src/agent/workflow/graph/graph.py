from langgraph.graph import StateGraph, START, END
from agent.workflow.state.state import SwarmState
import logging

logger = logging.getLogger(__name__)
from agent.workflow.nodes.nodes import (
    architect_node, 
    security_node, 
    optimizer_node,
    blast_radius_node,
    synthesizer_node,
    bouncer_node,
    dispatcher_node,
    route_dispatch,
    conversational_node,
    summarize_node
)
from agent.workflow.nodes.file_reviewer import file_reviewer_node

# Initialize the state graph
builder = StateGraph(SwarmState)

# Add all nodes
builder.add_node("bouncer", bouncer_node)
builder.add_node("dispatcher", dispatcher_node)
builder.add_node("file_reviewer", file_reviewer_node)
builder.add_node("architect", architect_node)
builder.add_node("security", security_node)
builder.add_node("optimizer", optimizer_node)
builder.add_node("blast_radius", blast_radius_node)
builder.add_node("synthesizer", synthesizer_node)
builder.add_node("conversational", conversational_node)
builder.add_node("archivist", summarize_node)

# --- Routing Logic ---

# 1. Start with the Bouncer
builder.add_edge(START, "bouncer")

# 2. Conditional Routing from Bouncer
def route_from_bouncer(state: SwarmState):
    if state.get("status") == "REJECT":
        return "synthesizer"
    
    if state.get("is_conversational"):
        logger.info("Graph Router: Routing to CONVERSATIONAL path (archivist -> conversational)")
        return "archivist"
        
    logger.info("Graph Router: Routing to INITIAL review path (specialists fan-out)")
    # Fan-out: Return a list of nodes to execute in parallel
    return ["architect", "security", "optimizer", "blast_radius", "dispatcher"]

builder.add_conditional_edges("bouncer", route_from_bouncer)

# 3. Add dynamic Send routing for the File Reviewer subgraphs
builder.add_conditional_edges("dispatcher", route_dispatch, ["file_reviewer"])

# 4. Converge PR-Wide Specialists and File Reviewer Subgraphs to Synthesizer
builder.add_edge("architect", "synthesizer")
builder.add_edge("security", "synthesizer")
builder.add_edge("optimizer", "synthesizer")
builder.add_edge("blast_radius", "synthesizer")
builder.add_edge("file_reviewer", "synthesizer")

# Finish (Synthesizer -> End)
builder.add_edge("synthesizer", END)
builder.add_edge("archivist", "conversational")
builder.add_edge("conversational", END)

# NEW: Persistent Global Store for Thread Weaver App
_active_swarm_app = builder.compile()

def get_swarm_app():
    """Thread Weaver Interface: returns the most up-to-date compiled graph."""
    return _active_swarm_app

async def get_compiled_swarm_with_checkpointer(pool):
    """
    Returns the swarm graph compiled with a persistent PostgreSQL checkpointer.
    The pool should be an asyncpg pool initialized in the FastAPI startup.
    """
    global _active_swarm_app
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    checkpointer = AsyncPostgresSaver(pool)
    # Ensure tables exist (setup)
    await checkpointer.setup()
    _active_swarm_app = builder.compile(checkpointer=checkpointer)
    return _active_swarm_app
