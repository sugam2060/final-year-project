from typing import TypedDict, List, Annotated, Any, Dict
import operator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from agent.types.inline_comments import InlineSuggestion

class FileReviewState(TypedDict):
    """Isolated state for the File Reviewer Subgraph (one per file)."""
    filename: str
    code_diff: str
    repo_name: str
    pr_number: int
    # Triage output
    selected_specialists: List[str]
    # File-scoped specialist outputs
    file_architect_review: str
    file_security_review: str
    file_optimizer_review: str
    file_blast_radius_review: str
    # Local synthesis output
    compact_summary: str
    severity: str
    findings_count: int
    parallel_reviewer_results: List[Dict[str, Any]]

class SwarmState(TypedDict):
    """PR-wide state for the parent orchestration graph."""
    pr_number: int
    repo_name: str
    commit_sha: str  # REQUIRED: To anchor inline comments
    pr_author: str  # The username of the person who opened the PR or triggered the swarm
    code_diff: str
    annotated_diff: str  # Pre-parsed diff with line markers for LLM accuracy
    is_conversational: bool  # Flag to change agent routing and behavior
    user_message: str        # The specific comment the user just typed
    
    # NEW: Thread-based message history (replaces conversation_history string)
    messages: Annotated[List[AnyMessage], add_messages]
    
    status: str  # "PROCEED" or "REJECT"
    rejection_comment: str
    filtered_diff_payload: str
    architect_review: str
    security_review: str
    optimizer_review: str
    blast_radius_review: str
    final_comment: str
    inline_suggestions: List[InlineSuggestion]
    summary: str  # NEW: Compressed context for long conversations
    parallel_reviewer_results: Annotated[List[Dict[str, Any]], operator.add]
