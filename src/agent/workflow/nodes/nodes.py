import asyncio
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from agent.workflow.llm.llm import get_tool_bound_llm
from agent.workflow.state.state import SwarmState

# Define specialized prompts for each engineering persona
ARCHITECT_PROMPT = """You are a Staff Software Architect. 
Review the following code diff for SOLID principles, DRY issues, and architectural soundness. 
If needed, use your tools to check repository context.
DIFF:
{code_diff}
"""

SECURITY_PROMPT = """You are an Application Security Engineer. 
Audit the Following code diff for OWASP vulnerabilities, injection risks, or credential leakages.
Use your tools to check for specific library vulnerabilities in the repository.
DIFF:
{code_diff}
"""

OPTIMIZER_PROMPT = """You are a Performance Engineer.
Search for algorithmic inefficiencies, nested loops, or excessive memory allocations in the diff.
Recommend O(1) or O(n) optimizations.
DIFF:
{code_diff}
"""

SYNTHESIZER_PROMPT = """You are the Lead Engineer. 
Compile the reviews below into a final, prioritized Markdown comment for a Pull Request.
Highlight blockers (Red) vs suggestions (Yellow).

Architect Review: {architect_review}
Security Review: {security_review}
Performance Review: {optimizer_review}
"""

async def architect_node(state: SwarmState) -> Dict[str, str]:
    """Staff Architect Persona."""
    llm = await get_tool_bound_llm()
    prompt = ARCHITECT_PROMPT.format(code_diff=state["code_diff"])
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"architect_review": response.content}

async def security_node(state: SwarmState) -> Dict[str, str]:
    """AppSec Specialist Persona."""
    llm = await get_tool_bound_llm()
    prompt = SECURITY_PROMPT.format(code_diff=state["code_diff"])
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"security_review": response.content}

async def optimizer_node(state: SwarmState) -> Dict[str, str]:
    """Performance Tuning Persona."""
    llm = await get_tool_bound_llm()
    prompt = OPTIMIZER_PROMPT.format(code_diff=state["code_diff"])
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"optimizer_review": response.content}

async def synthesizer_node(state: SwarmState) -> Dict[str, str]:
    """Synthesizer / Final Aggregator."""
    from langchain_openai import ChatOpenAI
    # No tools needed for synthesis (Constraint 1: use ChatOpenAI directly)
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    prompt = SYNTHESIZER_PROMPT.format(
        architect_review=state["architect_review"],
        security_review=state["security_review"],
        optimizer_review=state["optimizer_review"]
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"final_comment": response.content}
