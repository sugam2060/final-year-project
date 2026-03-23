import logging
from agent.workflow.graph.graph import swarm_app
from agent.workflow.state.state import SwarmState
from agent.workflow.tools.publisher import publish_pr_comment
from agent.workflow.utils.diff_parser import annotate_diff_with_line_numbers

# Configure logging
logger = logging.getLogger(__name__)

async def run_swarm(pr_number: int, code_diff: str, repo_name: str, commit_sha: str):
    """
    Entrypoint for the LangGraph swarm orchestration.
    Initializes state, invokes the graph, and automatically publishes the results.
    """
    logger.info("--- LANGGRAPH SWARM ACTIVATED FOR %s PR #%s ---", repo_name, pr_number)
    
    # Pre-parse the diff to include line numbers (Precision Trick)
    annotated_diff = annotate_diff_with_line_numbers(code_diff)
    
    # Initialize the swarm's shared memory (state)
    initial_state = {
        "pr_number": pr_number,
        "repo_name": repo_name,
        "commit_sha": commit_sha, # SHA for anchoring inline comments
        "code_diff": code_diff,
        "annotated_diff": annotated_diff, # Annotated version for line accuracy
        "architect_review": "",
        "security_review": "",
        "optimizer_review": "",
        "final_comment": "",
        "inline_suggestions": [] # Storage for granular inline code suggestions
    }
    
    try:
        # Constraint 1: Fully Asynchronous Graph Execution
        result = await swarm_app.ainvoke(initial_state)
        
        # 1. Capture final aggregated findings
        final_review = result.get("final_comment")
        inline_suggestions = result.get("inline_suggestions", [])
        
        # 2. Automatically Publish to GitHub PR
        if final_review:
            logger.info("--- SWARM FINAL SYTHESIS COMPLETE (PR #%s) ---", pr_number)
            # Pass both the general summary and line-specific suggestions to the publisher
            await publish_pr_comment(
                repo_name=repo_name, 
                pr_number=pr_number, 
                comment_body=final_review,
                commit_sha=commit_sha,
                inline_suggestions=inline_suggestions
            )
        else:
            logger.error("Swarm completed but no final_comment was generated for PR #%s", pr_number)
        
        return final_review
        
    except Exception as e:
        logger.error("Swarm Execution Failed for PR #%s: %s", pr_number, e)
        raise
