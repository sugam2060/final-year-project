from langgraph.graph import StateGraph, START, END
from agent.workflow.state.state import SwarmState
from agent.workflow.nodes.nodes import (
    architect_node, 
    security_node, 
    optimizer_node,
    blast_radius_node,
    synthesizer_node,
    bouncer_node,
    dispatcher_node,
    route_dispatch,
    conversational_node
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

# --- Routing Logic ---

# 1. Start with the Bouncer
builder.add_edge(START, "bouncer")

# 2. Conditional Routing from Bouncer
def route_from_bouncer(state: SwarmState):
    if state.get("status") == "REJECT":
        return ["synthesizer"]
    
    if state.get("is_conversational"):
        # Bypass all specialists and hit the independent conversational LLM directly
        return ["conversational"]
        
    # Fan-out: PR-wide specialists + Dispatcher (which fans out into File Reviewer Subgraphs)
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
builder.add_edge("conversational", END)

# Final Graph Compilation
swarm_app = builder.compile()
