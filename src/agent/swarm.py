import logging
from agent.workflow.graph.graph import swarm_app
from agent.workflow.tools.publisher import publish_pr_comment
from agent.workflow.utils.diff_parser import annotate_diff_with_line_numbers

# Configure logging
logger = logging.getLogger(__name__)

async def run_swarm(
    pr_number: int,
    code_diff: str,
    repo_name: str,
    commit_sha: str,
    is_conversational: bool = False,
    user_message: str = "",
    conversation_history: str = ""
):
    """
    Entrypoint for the LangGraph swarm orchestration.
    Initializes state, invokes the graph, and automatically publishes the results.
    
    Supports two modes:
    - Initial Review (is_conversational=False): Full structured review with inline suggestions.
    - Conversational Review (is_conversational=True): Follow-up reply to developer pushback.
    """
    mode = "CONVERSATIONAL" if is_conversational else "INITIAL"
    logger.info("--- LANGGRAPH SWARM ACTIVATED [%s] FOR %s PR #%s ---", mode, repo_name, pr_number)
    
    # Pre-parse the diff to include line numbers (Precision Trick)
    annotated_diff = annotate_diff_with_line_numbers(code_diff)
    
    # Initialize the swarm's shared memory (state)
    initial_state = {
        "pr_number": pr_number,
        "repo_name": repo_name,
        "commit_sha": commit_sha,
        "code_diff": code_diff,
        "annotated_diff": annotated_diff,
        "is_conversational": is_conversational,
        "user_message": user_message,
        "conversation_history": conversation_history,
        "architect_review": "",
        "security_review": "",
        "optimizer_review": "",
        "final_comment": "",
        "inline_suggestions": []
    }
    
    try:
        # 1. Orchestrate analysis (Specialists fan-out)
        result = await swarm_app.ainvoke(initial_state)
        
        # 2. Extract synthesized findings
        final_review = result.get("final_comment")
        inline_suggestions = result.get("inline_suggestions", [])
        
        if not final_review:
            logger.error("Swarm completed but no final_comment was generated for PR #%s", pr_number)
            return None
        
        logger.info("--- SWARM FINAL SYNTHESIS COMPLETE [%s] (PR #%s) ---", mode, pr_number)
        
        # 3. Automatically Publish to GitHub PR
        # Unified publisher handles both structured reviews and conversational replies.
        # In conversational mode, we pass None to commit_sha to ensure issue comment.
        await publish_pr_comment(
            repo_name=repo_name, 
            pr_number=pr_number, 
            comment_body=final_review,
            commit_sha=commit_sha if not is_conversational else None,
            inline_suggestions=inline_suggestions if not is_conversational else None
        )
        
        return final_review
        
    except Exception as e:
        logger.error("Swarm Execution Failed [%s] for PR #%s: %s", mode, pr_number, e)
        raise
