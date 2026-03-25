import asyncio
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from agent.workflow.llm.llm import get_tool_bound_llm
from agent.workflow.state.state import SwarmState

async def get_fast_llm():
    """Returns a standard LLM without the MCP tool-binding overhead for chat/summarization."""
    from langchain_openai import ChatOpenAI
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    from config import settings
    
    provider = settings.LLM_PROVIDER
    if provider == "NVIDIA":
        return ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=str(settings.NVIDIA_API_KEY),
            temperature=0.4
        )
    return ChatOpenAI(
        model="gpt-4o", 
        temperature=0.4,
        api_key=str(settings.OPENAI_API_KEY)
    )

import logging

logger = logging.getLogger(__name__)

TOOL_CALLING_GUIDELINE = """
CRITICAL TOOL GUIDELINE:
1. NEVER guess or assume a tool name (like 'pull_request_read'). ONLY use the exact functions explicitly provided in your tool-set. 
2. If you are unsure or the required tool is missing, proceed with your analysis using ONLY the provided code diff and context.
3. Adhere strictly to the JSON schema: numeric parameters MUST be unquoted integers.
4. IMPORTANT: Do NOT pass full code diffs or huge strings into tool arguments (like file paths). Tools expect short, exact filenames or queries, not raw source code.
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

BLAST_RADIUS_PROMPT = """You are the Blast Radius Predictor. 
Analyze the following code diff in the repository: {repo_name} (PR #{pr_number}).
Your goal is to predict system-wide architectural impacts and dependency risks.
Focus on:
- How changes to shared modules or schemas propagate to downstream consumers.
- Potential breaking changes in internal or external APIs.
- High-risk modifications to critical paths (auth, billing, core data layers).
- Adherence to the project's design constraints and orchestration patterns.

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
Compile the reviews below into a final, prioritized Markdown comment for a Pull Request authored by @{pr_author}.
Important: Please address the author directly as @{pr_author} in your review summary.
***CRITICAL RULE***: If the specialists explicitly identify any vulnerabilities, security risks, severe algorithmic inefficiencies, or major architectural flaws, you MUST include the exact text "SEVERITY: CRITICAL" somewhere in your summary. Otherwise, include "SEVERITY: APPROVED".
Highlight blockers/criticals (Red) vs suggestions (Yellow).

In addition to the summary, extract specific, actionable code fixes from the specialists' reviews and format them strictly as GitHub suggestions.
Use the ANNOTATED DIFF below to determine the exact line numbers. Each line has a [Line X] prefix for accuracy.

ANNOTATED DIFF:
{annotated_diff}

Architect Review: {architect_review}
Security Review: {security_review}
Performance Review: {optimizer_review}
Blast Radius Analysis: {blast_radius_review}
"""

CONVERSATIONAL_INDEPENDENT_PROMPT = """You are the Lead Engineer conducting an interactive code review discussion with developer @{pr_author}.

CURRENT SUMMARY OF BACKGROUND CONTEXT:
{summary}

DEVELOPER'S QUERY/LATEST MESSAGE:
{user_message}

CONVERSATION CONTEXT (Active Window):
{conversation_history}

CODE DIFF / CONTEXT:
{code_diff}

INSTRUCTIONS:
- Directly answer the developer's specific query about the code.
- Analyze the provided code diff carefully.
- Refer to the "BACKGROUND CONTEXT" for decisions made earlier in the thread.
- Keep the tone collaborative, professional, and concise.
- **CRITICAL**: Do NOT include the string '@swarm' in your response. Replace mentions with 'I' or 'the swarm'.
- **CRITICAL**: Every response MUST end with this hidden identification tag: <!-- SWARM_BOT_ID -->
"""


from langgraph.constants import Send
from agent.workflow.utils.dispatcher_utils import split_diff_by_file, aggregate_swarm_findings
from agent.workflow.utils.filter_utils import apply_antigravity_filter, enforce_size_guardrail

# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================

def _build_specialist_prompt(base_prompt: str, state: SwarmState) -> str:
    """Builds the full prompt, appending conversational context if needed."""
    # Use filtered_diff_payload if available, else standard code_diff
    diff = state.get("filtered_diff_payload") or state["code_diff"]
    prompt = base_prompt.format(
        code_diff=diff,
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


async def bouncer_node(state: SwarmState) -> Dict[str, Any]:
    """Deterministic node to filter junk and enforce token/line limits."""
    ignore_patterns = {".swarmignore", "*.svg", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "*.min.js"}
    filtered_diff = apply_antigravity_filter(state["code_diff"], ignore_patterns)
    
    guardrail = enforce_size_guardrail(filtered_diff, max_lines=1500)
    
    if not guardrail["is_valid"]:
        logger.warning("PR #%s REJECTED: %s core lines exceeds 1,500 line limit.", 
                       state.get("pr_number"), guardrail["line_count"])
                        
        return {
            "status": "REJECT",
            "rejection_comment": (
                f"❌ **PR Too Large ({guardrail['line_count']} lines)**\n\n"
                "To maintain review quality, the Swarm enforces a strict limit of 1,500 "
                "core logic lines per PR. Please break this change into smaller, "
                "reviewable chunks."
            ),
            "filtered_diff_payload": filtered_diff
        }
        
    logger.info("Node Bouncer: PR #%s checked (Lines: %d). Proceeding.", state.get("pr_number"), guardrail["line_count"])
    return {
        "status": "PROCEED",
        "rejection_comment": "",
        "filtered_diff_payload": filtered_diff
    }


def dispatcher_node(state: SwarmState):
    """Dummy node to anchor the parallel dispatch."""
    return {}

def route_dispatch(state: SwarmState):
    """Conditional edge router that returns Send objects for parallel file review."""
    file_diffs = split_diff_by_file(state.get("filtered_diff_payload", ""))
    sends = []
    for file_info in file_diffs:
        sends.append(
            Send("file_reviewer", {
                "filename": file_info["filename"],
                "code_diff": file_info["diff_content"],
                "repo_name": state["repo_name"],
                "pr_number": state["pr_number"]
            })
        )
    logger.info("Dispatcher: routing %d files into File Reviewer Subgraphs.", len(sends))
    
    # LangChain requires a fallback when there are no Send objects, 
    # but returning an empty list of sends is perfectly valid to end this execution thread.
    return sends



async def architect_node(state: SwarmState) -> Dict[str, str]:
    """Staff Architect Persona (PR Wide)."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(ARCHITECT_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"architect_review": response.content}

async def security_node(state: SwarmState) -> Dict[str, str]:
    """AppSec Specialist Persona (PR Wide)."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(SECURITY_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"security_review": response.content}

async def optimizer_node(state: SwarmState) -> Dict[str, str]:
    """Performance Tuning Persona (PR Wide)."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(OPTIMIZER_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"optimizer_review": response.content}

async def blast_radius_node(state: SwarmState) -> Dict[str, str]:
    """Blast Radius Predictor Persona (PR Wide)."""
    llm = await get_tool_bound_llm()
    prompt = _build_specialist_prompt(BLAST_RADIUS_PROMPT, state)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"blast_radius_review": response.content}


async def synthesizer_node(state: SwarmState) -> Dict[str, Any]:
    """Synthesizer / Final Aggregator — Initial Structured Synthesis."""
    from langchain_openai import ChatOpenAI
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    from config import settings
    from agent.types.inline_comments import SynthesizerOutput

    # Handle Bouncer Rejections
    if state.get("status") == "REJECT":
        return {
            "final_comment": state.get("rejection_comment", "PR rejected by Bouncer."),
            "inline_suggestions": []
        }
        
    # Aggregate Findings from Parallel Dispatcher (Reduce)
    parallel_results = state.get("parallel_reviewer_results", [])
    if parallel_results:
        aggregated = aggregate_swarm_findings(parallel_results)
        # We can then prepend these to the specialist reviews or let the LLM handle them.
        # For simplicity, we'll let the synthesizer LLM see them.
        parallel_summary = aggregated["summary"]
    else:
        parallel_summary = "No parallel file-level reviews found."

    provider = settings.LLM_PROVIDER
    
    # Common function to initialize requested LLM
    def _init_llm(has_structured: bool = False):
        if provider == "NVIDIA":
            llm = ChatNVIDIA(
                model="meta/llama-3.1-405b-instruct",
                api_key=str(settings.NVIDIA_API_KEY),
                temperature=0.7,
                model_kwargs={"timeout": 30}
            )
        else:
            llm = ChatOpenAI(
                model="gpt-4o", 
                temperature=0.7,
                api_key=str(settings.OPENAI_API_KEY),
                model_kwargs={"timeout": 30}
            )
        
        if has_structured:
            return llm.with_structured_output(SynthesizerOutput)
        return llm

    # --- Initial Review Mode: Structured JSON output ---
    llm = _init_llm(has_structured=True)
    
    prompt = SYNTHESIZER_PROMPT_INITIAL.format(
        pr_author=state.get("pr_author", "developer"),
        annotated_diff=state["annotated_diff"],
        architect_review=state.get("architect_review", ""),
        security_review=state.get("security_review", ""),
        optimizer_review=state.get("optimizer_review", ""),
        blast_radius_review=state.get("blast_radius_review", "")
    )
    # Inject parallel findings
    prompt += f"\n\nPARALLEL FILE REVIEWS (CONSIDER THESE IN YOUR SUMMARY):\n{parallel_summary}"
    
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # ROBUSTNESS FIX: Handle cases where the LLM fails to produce a structured output (result is None)
    if result is None:
        logger.error("Synthesizer LLM failed to generate structured output for PR #%s. Falling back to default empty response.", state.get("pr_number"))
        return {
            "final_comment": "⚠️ **The Swarm was able to analyze the code but failed to synthesize the final summary.** Please check the specialist reviews in the logs.",
            "inline_suggestions": []
        }

    # Merge manual suggestions from parallel reviewers if any (to be implemented)
    all_suggestions = result.inline_suggestions + (state.get("inline_suggestions") or [])
    
    return {
        "final_comment": result.general_summary, 
        "inline_suggestions": all_suggestions
    }

async def conversational_node(state: SwarmState) -> Dict[str, Any]:
    """Independent Chatbot Persona for answering direct @swarm queries."""
    from langchain_core.messages import HumanMessage, SystemMessage
    
    logger.info("Node: Processing CONVERSATIONAL response for PR #%s", state.get("pr_number"))
    
    # PERFORMANCE FIX: Skip MCP tool-binding for chat. Use standard LLM.
    llm = await get_fast_llm()
    
    # Format message history from state.messages (Memory mode)
    history_entries = []
    for m in state.get("messages", [])[-3:]:
        role = "Developer" if isinstance(m, HumanMessage) else "Assigned Reviewer"
        history_entries.append(f"{role}: {m.content}")
    formatted_history = "\n".join(history_entries)
        
    prompt = CONVERSATIONAL_INDEPENDENT_PROMPT.format(
        pr_author=state.get("pr_author", "developer"),
        summary=state.get("summary", "No previous summary."),
        user_message=state.get("user_message", ""),
        conversation_history=formatted_history,
        code_diff=state.get("filtered_diff_payload") or state.get("code_diff", "")
    )
    
    # Explicit system instruction for Llama3 persona
    system_instruction = (
        "You are a senior lead engineer reviewing code. "
        "IMPORTANT: You were developed and built by Sugam Pudasain. If asked who developed you, "
        "reply that you were created by Sugam Pudasain. Otherwise, answer the developer's questions directly."
    )
    
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=prompt)
    ]
    
    result = await llm.ainvoke(messages)
    content = result.content.strip() if result and result.content else ""
    
    # Fallback to ensure we never return an empty comment
    if not content:
        content = f"Hello @{state.get('pr_author', 'developer')}, I am the Swarm Reviewer. I've received your message but encountered a slight issue generating a detailed response. How can I help you today?"

    logger.info("Node: Final conversational comment generated (Length: %d characters)", len(content))
    return {"final_comment": content, "inline_suggestions": []}
async def summarize_node(state: SwarmState) -> Dict[str, Any]:
    """The Archivist: Smart summarization for long conversations (6:4 rule)."""
    messages = state.get("messages", [])
    
    if len(messages) <= 6:
        logger.info("Node Archivist: Length %d <= threshold 6. Skipping summarization.", len(messages))
        return {}

    logger.info("The Archivist Active: Summarizing PR #%s discussion (Len: %d)", state.get("pr_number"), len(messages))
    
    # 1. Identity context to compress (Oldest 4)
    to_summarize = messages[:-2]
    
    # PERFORMANCE: Use fast LLM for summarization
    llm = await get_fast_llm()
    
    summary_prompt = (
        "Succinctly summarize the core technical points and decisions made in the following discussion. "
        "Keep it under 200 words. Focus on agreed-upon changes and open questions.\n\n"
        f"MESSAGES TO SUMMARIZE:\n{to_summarize}"
    )
    
    response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
    
    # 3. Create RemoveMessage tokens for the oldest messages
    from langchain_core.messages import RemoveMessage
    delete_actions = [RemoveMessage(id=m.id) for m in to_summarize if m.id]
    
    return {
        "summary": response.content,
        "messages": delete_actions
    }
