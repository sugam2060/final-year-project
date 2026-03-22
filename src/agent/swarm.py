import logging
from agent.workflow.graph.graph import swarm_app
from agent.workflow.state.state import SwarmState
from agent.workflow.tools.publisher import publish_pr_comment

# Configure logging
logger = logging.getLogger(__name__)

async def run_swarm(pr_number: int, code_diff: str, repo_name: str):
    """
    Entrypoint for the LangGraph swarm orchestration.
    Initializes state, invokes the graph, and automatically publishes the results.
    """
    logger.info("--- LANGGRAPH SWARM ACTIVATED FOR %s PR #%s ---", repo_name, pr_number)
    
    # Initialize the swarm's shared memory (state)
    initial_state = {
        "pr_number": pr_number,
        "repo_name": repo_name,
        "code_diff": code_diff,
        "architect_review": "",
        "security_review": "",
        "optimizer_review": "",
        "final_comment": ""
    }
    
    try:
        # Constraint 1: Fully Asynchronous Graph Execution
        result = await swarm_app.ainvoke(initial_state)
        
        # 1. Capture final aggregated findings
        final_review = result.get("final_comment")
        
        # 2. Automatically Publish to GitHub PR
        if final_review:
            logger.info("--- SWARM FINAL SYTHESIS COMPLETE (PR #%s) ---", pr_number)
            await publish_pr_comment(repo_name, pr_number, final_review)
        else:
            logger.error("Swarm completed but no final_comment was generated for PR #%s", pr_number)
        
        return final_review
        
    except Exception as e:
        logger.error("Swarm Execution Failed for PR #%s: %s", pr_number, e)
        raise
