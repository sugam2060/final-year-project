from typing import TypedDict, List
from agent.types.inline_comments import InlineSuggestion

class SwarmState(TypedDict):
    pr_number: int
    repo_name: str
    commit_sha: str  # REQUIRED: To anchor inline comments
    code_diff: str
    annotated_diff: str  # Pre-parsed diff with line markers for LLM accuracy
    is_conversational: bool  # Flag to change agent routing and behavior
    user_message: str        # The specific comment the user just typed
    conversation_history: str  # Formatted string of previous PR comments
    architect_review: str
    security_review: str
    optimizer_review: str
    blast_radius_review: str
    final_comment: str
    inline_suggestions: List[InlineSuggestion]
