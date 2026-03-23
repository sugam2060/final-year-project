import asyncio
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from agent.workflow.llm.llm import get_tool_bound_llm
from agent.workflow.state.state import SwarmState

import logging

logger = logging.getLogger(__name__)

TOOL_CALLING_GUIDELINE = """
CRITICAL TOOL GUIDELINE:
1. NEVER guess or assume a tool name (like 'pull_request_read'). ONLY use the exact functions explicitly provided in your tool-set.
2. If you are unsure or the required tool is missing, proceed with your analysis using ONLY the provided code diff and context.
3. Adhere strictly to the JSON schema: numeric parameters (like 'perPage', 'page', 'line', 'pull_number') MUST be unquoted integers, not strings.
- Correct: "perPage": 5
- Incorrect: "perPage": "5"
"""

# ============================================================================
# SPECIALIST PROMPTS — Initial Review Mode
# ============================================================================

ARCHITECT_PROMPT = """You are a Staff Software Architect. 
You are reviewing a Pull Request in the repository: {repo_name} (PR #{pr_number}).
Review the following code diff for SOLID principles, DRY issues, and architectural soundness. 
If you need more context, use your tools specifically for this repository.
DIFF:
{code_diff}
"""

SECURITY_PROMPT = """You are an Application Security Engineer. 
You are auditing a Pull Request in the repository: {repo_name} (PR #{pr_number}).
Audit the Following code diff for OWASP vulnerabilities, injection risks, or credential leakages.
Use your tools to check for specific library vulnerabilities within this repository context.
DIFF:
{code_diff}
"""

OPTIMIZER_PROMPT = """You are a Performance Engineer.
You are profiling a Pull Request in the repository: {repo_name} (PR #{pr_number}).
Search for algorithmic inefficiencies, nested loops, or excessive memory allocations in the diff.
Recommend O(1) or O(n) optimizations.
DIFF:
{code_diff}
"""

# ============================================================================
# SPECIALIST PROMPTS — Conversational Mode (Appended when is_conversational)
# ============================================================================

CONVERSATIONAL_CONTEXT_PROMPT = """
IMPORTANT: You are engaging in a DIALOGUE with a developer who is replying to a previous code review.

CONVERSATION HISTORY (last 5 comments from the PR thread):
{conversation_history}

LATEST MESSAGE from the developer:
{user_message}

INSTRUCTIONS:
- Evaluate the developer's argument carefully.
- If they provide a valid architectural, legacy, or business constraint, gracefully concede the point and update your stance.
- If their reasoning is flawed, politely but firmly explain why the vulnerability or anti-pattern still stands.
- Be collaborative and constructive, not combative.
"""

# ============================================================================
# SYNTHESIZER PROMPTS
# ============================================================================

SYNTHESIZER_PROMPT_INITIAL = """You are the Lead Engineer. 
Compile the reviews below into a final, prioritized Markdown comment for a Pull Request.
Highlight blockers (Red) vs suggestions (Yellow).

In addition to the summary, extract specific, actionable code fixes from the specialists' reviews and format them strictly as GitHub suggestions.
Use the ANNOTATED DIFF below to determine the exact line numbers. Each line has a [Line X] prefix for accuracy.

ANNOTATED DIFF:
{annotated_diff}

Architect Review: {architect_review}
Security Review: {security_review}
Performance Review: {optimizer_review}
"""

SYNTHESIZER_PROMPT_CONVERSATIONAL = """You are the Lead Engineer. 
The team of specialists has re-evaluated a developer's pushback on a previous code review.
Synthesize their updated stances into a clear, conversational Markdown reply for the PR thread.

CONVERSATION CONTEXT:
{conversation_history}

DEVELOPER'S LATEST MESSAGE:
{user_message}

UPDATED SPECIALIST REVIEWS:
Architect Review: {architect_review}
Security Review: {security_review}
Performance Review: {optimizer_review}

INSTRUCTIONS:
- Write a direct, conversational reply (not a formal review).
- Address the developer's specific points.
- Where the specialists conceded, acknowledge that clearly.
- Where the specialists held firm, explain why concisely.
- Keep the tone collaborative and professional.
- **CRITICAL**: Do NOT include the string '@swarm' in your response. Replace mentions with 'I' or 'the swarm'.
- **CRITICAL**: Every response MUST end with this hidden identification tag: <!-- SWARM_BOT_ID -->
"""


# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================

def _build_specialist_prompt(base_prompt: str, state: SwarmState) -> str:
    """Builds the full prompt, appending conversational context if needed."""
    prompt = base_prompt.format(
        code_diff=state["code_diff"],
        repo_name=state.get("repo_name", "unknown/repo"),
        pr_number=state.get("pr_number", 0)
    )
    
    if state.get("is_conversational"):
        prompt += CONVERSATIONAL_CONTEXT_PROMPT.format(
            conversation_history=state.get("conversation_history", ""),
            user_message=state.get("user_message", "")
        )
    
    prompt += TOOL_CALLING_GUIDELINE
    return prompt


async def architect_node(state: SwarmState) -> Dict[str, str]:
    """Staff Architect Persona."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(ARCHITECT_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"architect_review": response.content}

async def security_node(state: SwarmState) -> Dict[str, str]:
    """AppSec Specialist Persona."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(SECURITY_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"security_review": response.content}

async def optimizer_node(state: SwarmState) -> Dict[str, str]:
    """Performance Tuning Persona."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(OPTIMIZER_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"optimizer_review": response.content}

async def synthesizer_node(state: SwarmState) -> Dict[str, Any]:
    """Synthesizer / Final Aggregator — Dual Mode (Initial vs Conversational)."""
    from langchain_openai import ChatOpenAI
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    from config import settings
    from agent.types.inline_comments import SynthesizerOutput
    
    is_conversational = state.get("is_conversational", False)
    provider = settings.LLM_PROVIDER
    
    # Common function to initialize requested LLM
    def _init_llm(has_structured: bool = False):
        if provider == "NVIDIA":
            llm = ChatNVIDIA(
                model="meta/llama-3.1-405b-instruct",
                api_key=str(settings.NVIDIA_API_KEY),
                temperature=0.7,
                timeout=30
            )
        else:
            llm = ChatOpenAI(
                model="gpt-4o", 
                temperature=0.7,
                api_key=str(settings.OPENAI_API_KEY),
                timeout=30
            )
        
        if has_structured:
            return llm.with_structured_output(SynthesizerOutput)
        return llm

    if is_conversational:
        # --- Conversational Mode: Free-form Markdown reply ---
        llm = _init_llm(has_structured=False)
        
        prompt = SYNTHESIZER_PROMPT_CONVERSATIONAL.format(
            conversation_history=state.get("conversation_history", ""),
            user_message=state.get("user_message", ""),
            architect_review=state["architect_review"],
            security_review=state["security_review"],
            optimizer_review=state["optimizer_review"]
        )
        
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        
        logger.info("Synthesizer produced conversational reply for PR #%s", state["pr_number"])
        return {"final_comment": result.content}
    
    else:
        # --- Initial Review Mode: Structured JSON output ---
        llm = _init_llm(has_structured=True)
        
        prompt = SYNTHESIZER_PROMPT_INITIAL.format(
            annotated_diff=state["annotated_diff"],
            architect_review=state["architect_review"],
            security_review=state["security_review"],
            optimizer_review=state["optimizer_review"]
        )
        
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        
        logger.info("Synthesizer produced structured review for PR #%s", state["pr_number"])
        return {
            "final_comment": result.general_summary, 
            "inline_suggestions": result.inline_suggestions
        }
