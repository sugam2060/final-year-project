import asyncio
import logging
from github import Github
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

async def publish_pr_comment(repo_name: str, pr_number: int, comment_body: str):
    """
    Publishes a synthesized swarm review as a comment on a GitHub Pull Request.
    Constraint 1: Uses asyncio.to_thread for blocking PyGithub calls.
    """
    logger.info("Initializing PR comment publication for %s PR #%s...", repo_name, pr_number)
    
    def post_comment():
        # Authenticate (Constraint 3: Secret management)
        g = Github(login_or_token=str(settings.GITHUB_TOKEN), timeout=20)
        
        # Resolve target context
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Constraint 1: Outward bound GitHub API call
        pr.create_issue_comment(comment_body)
        return True

    try:
        # Offload IO-bound operation
        await asyncio.to_thread(post_comment)
        logger.info("Successfully posted review to PR #%s in repository %s", pr_number, repo_name)
        
    except Exception as e:
        logger.error("Failed to publish PR comment for PR #%s: %s", pr_number, e)
        # Raise here to ensure the swarm execution reflects the failure
        raise
