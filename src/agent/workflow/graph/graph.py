from langgraph.graph import StateGraph, START, END
from agent.workflow.state.state import SwarmState
from agent.workflow.nodes.nodes import (
    architect_node, 
    security_node, 
    optimizer_node, 
    synthesizer_node
)

# Initialize the state graph
builder = StateGraph(SwarmState)

# Add all specialized nodes
builder.add_node("architect", architect_node)
builder.add_node("security", security_node)
builder.add_node("optimizer", optimizer_node)
builder.add_node("synthesizer", synthesizer_node)

# Parallel Routing logic (Fan-out)
# Start -> (Architect, Security, Optimizer)
builder.add_edge(START, "architect")
builder.add_edge(START, "security")
builder.add_edge(START, "optimizer")

# Converge (Fan-in)
# (Architect, Security, Optimizer) -> Synthesizer
builder.add_edge("architect", "synthesizer")
builder.add_edge("security", "synthesizer")
builder.add_edge("optimizer", "synthesizer")

# Finish (Synthesizer -> End)
builder.add_edge("synthesizer", END)

# Final Graph Compilation
swarm_app = builder.compile()
