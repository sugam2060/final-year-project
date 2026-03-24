"""
File Reviewer Subgraph — Selective Specialist Pipeline.

This module implements a 3-step subgraph:
  1. Triage (Deterministic) — Classify file and select relevant specialists.
  2. Selective Specialists (Parallel) — Run only relevant file-scoped specialists.
  3. Local Synthesis — Compress findings into a compact JSON summary.
"""

import os
import logging
from typing import Dict, Any, List

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from agent.workflow.state.state import FileReviewState
from agent.workflow.llm.llm import get_tool_bound_llm

logger = logging.getLogger(__name__)

# ============================================================================
# TRIAGE — O(1) Extension-to-Specialist Mapping
# ============================================================================

# Dictionary for O(1) lookups. Keys are lowercase file extensions.
EXTENSION_SPECIALIST_MAP: Dict[str, List[str]] = {
    # Source code — full analysis
    ".py":    ["architect", "security", "optimizer"],
    ".js":    ["architect", "security", "optimizer"],
    ".ts":    ["architect", "security", "optimizer"],
    ".tsx":   ["architect", "security", "optimizer"],
    ".jsx":   ["architect", "security", "optimizer"],
    ".java":  ["architect", "security", "optimizer"],
    ".go":    ["architect", "security", "optimizer"],
    ".rs":    ["architect", "security", "optimizer"],
    ".rb":    ["architect", "security", "optimizer"],
    ".php":   ["architect", "security", "optimizer"],
    ".cs":    ["architect", "security", "optimizer"],
    # Database / Schema — security + blast radius
    ".sql":    ["security", "blast_radius"],
    ".prisma": ["security", "blast_radius"],
    # Config files — security only
    ".yaml":  ["security"],
    ".yml":   ["security"],
    ".toml":  ["security"],
    ".env":   ["security"],
    ".ini":   ["security"],
    # Frontend markup — architect only
    ".css":   ["architect"],
    ".scss":  ["architect"],
    ".html":  ["architect"],
    # Documentation / Data — skip all (pass-through)
    ".md":    [],
    ".txt":   [],
    ".json":  [],
    ".csv":   [],
}

# Special filename patterns (checked if extension lookup fails)
FILENAME_SPECIALIST_MAP: Dict[str, List[str]] = {
    "dockerfile":       ["security", "blast_radius"],
    "docker-compose":   ["security", "blast_radius"],
    ".dockerignore":    [],
    ".gitignore":       [],
}


def triage_node(state: FileReviewState) -> Dict[str, Any]:
    """
    Deterministic triage: classify file by extension to decide which specialists to run.
    Zero LLM cost. O(1) dictionary lookup.
    """
    filename = state.get("filename", "")
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # 1. Try extension lookup (O(1))
    if ext in EXTENSION_SPECIALIST_MAP:
        selected = EXTENSION_SPECIALIST_MAP[ext]
    else:
        # 2. Try filename pattern lookup
        basename = os.path.basename(filename).lower()
        selected = None
        for pattern, specialists in FILENAME_SPECIALIST_MAP.items():
            if basename.startswith(pattern):
                selected = specialists
                break
        
        # 3. Default: run all specialists for unknown file types
        if selected is None:
            selected = ["architect", "security", "optimizer"]
    
    logger.info("Triage for '%s': selected specialists = %s", filename, selected)
    
    return {"selected_specialists": selected}


# ============================================================================
# FILE-SCOPED SPECIALIST PROMPTS
# ============================================================================

FILE_ARCHITECT_PROMPT = """You are a Staff Software Architect reviewing a SINGLE FILE.
Repository: {repo_name} (PR #{pr_number})
File: {filename}

Focus ONLY on this file's internal quality:
- SOLID violations within this file
- DRY issues (duplicated logic within this file)
- Naming conventions and code organization

DIFF:
{code_diff}
"""

FILE_SECURITY_PROMPT = """You are an Application Security Engineer auditing a SINGLE FILE.
Repository: {repo_name} (PR #{pr_number})
File: {filename}

Focus ONLY on vulnerabilities in this file:
- Injection risks (SQL, XSS, Command)
- Hardcoded credentials or secrets
- Unsafe deserialization or file operations
- OWASP Top 10 relevant to this file type

DIFF:
{code_diff}
"""

FILE_OPTIMIZER_PROMPT = """You are a Performance Engineer profiling a SINGLE FILE.
Repository: {repo_name} (PR #{pr_number})
File: {filename}

Focus ONLY on performance issues in this file:
- O(n²) or worse algorithmic complexity
- Unnecessary memory allocations
- Missing caching opportunities
- Blocking I/O in async contexts

DIFF:
{code_diff}
"""

FILE_BLAST_RADIUS_PROMPT = """You are the Blast Radius Predictor analyzing a SINGLE FILE.
Repository: {repo_name} (PR #{pr_number})
File: {filename}

Focus ONLY on downstream impact of changes in this file:
- Schema changes that affect other services
- API contract modifications
- Configuration changes that affect deployment

DIFF:
{code_diff}
"""

# ============================================================================
# FILE-SCOPED SPECIALIST NODES
# ============================================================================

async def file_architect_node(state: FileReviewState) -> Dict[str, str]:
    """File-scoped architect analysis."""
    llm = await get_tool_bound_llm()
    prompt = FILE_ARCHITECT_PROMPT.format(
        repo_name=state.get("repo_name", ""),
        pr_number=state.get("pr_number", 0),
        filename=state.get("filename", ""),
        code_diff=state.get("code_diff", "")
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"file_architect_review": response.content}


async def file_security_node(state: FileReviewState) -> Dict[str, str]:
    """File-scoped security analysis."""
    llm = await get_tool_bound_llm()
    prompt = FILE_SECURITY_PROMPT.format(
        repo_name=state.get("repo_name", ""),
        pr_number=state.get("pr_number", 0),
        filename=state.get("filename", ""),
        code_diff=state.get("code_diff", "")
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"file_security_review": response.content}


async def file_optimizer_node(state: FileReviewState) -> Dict[str, str]:
    """File-scoped performance analysis."""
    llm = await get_tool_bound_llm()
    prompt = FILE_OPTIMIZER_PROMPT.format(
        repo_name=state.get("repo_name", ""),
        pr_number=state.get("pr_number", 0),
        filename=state.get("filename", ""),
        code_diff=state.get("code_diff", "")
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"file_optimizer_review": response.content}


async def file_blast_radius_node(state: FileReviewState) -> Dict[str, str]:
    """File-scoped blast radius analysis."""
    llm = await get_tool_bound_llm()
    prompt = FILE_BLAST_RADIUS_PROMPT.format(
        repo_name=state.get("repo_name", ""),
        pr_number=state.get("pr_number", 0),
        filename=state.get("filename", ""),
        code_diff=state.get("code_diff", "")
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"file_blast_radius_review": response.content}


# ============================================================================
# LOCAL SYNTHESIS NODE
# ============================================================================

LOCAL_SYNTHESIS_PROMPT = """You are a Lead Engineer compressing review findings for a SINGLE FILE.

File: {filename}

Specialist findings:
{all_findings}

INSTRUCTIONS:
- Produce a COMPACT summary (max 3 sentences).
- Assign a severity: CRITICAL, HIGH, MEDIUM, LOW, or NONE.
- Count the distinct actionable findings.
- Do NOT repeat the full specialist output. Compress it.

Respond in this exact format:
SEVERITY: <level>
COUNT: <number>
SUMMARY: <compact summary>
"""


async def local_synthesis_node(state: FileReviewState) -> Dict[str, Any]:
    """Compress file-scoped specialist findings into a compact summary."""
    filename = state.get("filename", "")
    
    # Collect all findings that were actually produced
    findings_parts = []
    if state.get("file_architect_review"):
        findings_parts.append(f"ARCHITECTURE:\n{state['file_architect_review']}")
    if state.get("file_security_review"):
        findings_parts.append(f"SECURITY:\n{state['file_security_review']}")
    if state.get("file_optimizer_review"):
        findings_parts.append(f"PERFORMANCE:\n{state['file_optimizer_review']}")
    if state.get("file_blast_radius_review"):
        findings_parts.append(f"BLAST RADIUS:\n{state['file_blast_radius_review']}")
    
    if not findings_parts:
        # No specialists were run (e.g. .md file) — pass-through with NONE severity
        return {
            "compact_summary": f"No specialist analysis required for `{filename}`.",
            "severity": "NONE",
            "findings_count": 0
        }
    
    all_findings = "\n\n".join(findings_parts)
    
    llm = await get_tool_bound_llm()
    prompt = LOCAL_SYNTHESIS_PROMPT.format(
        filename=filename,
        all_findings=all_findings
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content
    
    # Parse the structured response
    severity = "MEDIUM"
    findings_count = 0
    summary = content
    
    for line in content.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("SEVERITY:"):
            severity = line_stripped.split(":", 1)[1].strip().upper()
        elif line_stripped.startswith("COUNT:"):
            try:
                findings_count = int(line_stripped.split(":", 1)[1].strip())
            except ValueError:
                findings_count = 0
        elif line_stripped.startswith("SUMMARY:"):
            summary = line_stripped.split(":", 1)[1].strip()
    
    logger.info("Local synthesis for '%s': severity=%s, findings=%d", filename, severity, findings_count)
    
    return {
        "compact_summary": summary,
        "severity": severity,
        "findings_count": findings_count,
        "parallel_reviewer_results": [{
            "filename": filename,
            "summary": summary,
            "severity": severity,
            "findings_count": findings_count
        }]
    }


# ============================================================================
# CONDITIONAL ROUTING — Selective Specialist Dispatch
# ============================================================================

def route_to_specialists(state: FileReviewState):
    """Route to only the specialists selected by triage."""
    selected = state.get("selected_specialists", [])
    
    if not selected:
        # No specialists needed — skip directly to synthesis
        return ["local_synthesis"]
    
    return selected


# ============================================================================
# SUBGRAPH COMPILATION
# ============================================================================

def build_file_reviewer_subgraph():
    """Builds and compiles the File Reviewer Subgraph."""
    
    subgraph = StateGraph(FileReviewState)
    
    # Add nodes
    subgraph.add_node("triage", triage_node)
    subgraph.add_node("architect", file_architect_node)
    subgraph.add_node("security", file_security_node)
    subgraph.add_node("optimizer", file_optimizer_node)
    subgraph.add_node("blast_radius", file_blast_radius_node)
    subgraph.add_node("local_synthesis", local_synthesis_node)
    
    # Edges
    subgraph.add_edge(START, "triage")
    
    # Conditional routing from triage
    subgraph.add_conditional_edges(
        "triage",
        route_to_specialists,
        {
            "architect": "architect",
            "security": "security",
            "optimizer": "optimizer",
            "blast_radius": "blast_radius",
            "local_synthesis": "local_synthesis",
        }
    )
    
    # All specialists converge to local synthesis
    subgraph.add_edge("architect", "local_synthesis")
    subgraph.add_edge("security", "local_synthesis")
    subgraph.add_edge("optimizer", "local_synthesis")
    subgraph.add_edge("blast_radius", "local_synthesis")
    
    # Local synthesis ends the subgraph
    subgraph.add_edge("local_synthesis", END)
    
    return subgraph.compile()


# Pre-compile the subgraph for reuse
file_reviewer_subgraph = build_file_reviewer_subgraph()

async def file_reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper to prevent internal keys from causing concurrent update errors in parent."""
    result = await file_reviewer_subgraph.ainvoke(state)
    return {
        "parallel_reviewer_results": result.get("parallel_reviewer_results", [])
    }
