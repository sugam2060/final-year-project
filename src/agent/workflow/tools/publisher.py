import asyncio
import logging
from github import Github
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

async def publish_pr_comment(
    repo_name: str, 
    pr_number: int, 
    comment_body: str, 
    commit_sha: str = None, 
    inline_suggestions: list = None
):
    """
    Publishes a synthesized swarm review as a comment on a GitHub Pull Request.
    If inline_suggestions and commit_sha are provided, it creates a structured Review.
    Constraint 1: Uses asyncio.to_thread for blocking PyGithub calls.
    """
    logger.info("Initializing PR review publication for %s PR #%s...", repo_name, pr_number)
    
    def post_review():
        # Authenticate (Constraint 3: Secret management)
        g = Github(login_or_token=str(settings.GITHUB_TOKEN), timeout=20)
        
        # Resolve target context
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        if commit_sha and inline_suggestions:
            logger.info("Creating bundled PR review with %s inline suggestions...", len(inline_suggestions))
            
            # Format comments for the PyGithub API
            github_comments = []
            for suggestion in inline_suggestions:
                github_comments.append({
                    "path": suggestion.file_path,
                    "line": suggestion.line_number,
                    "body": suggestion.suggestion_body
                })
            
            # Create the bundled review including the general summary and all inline suggestion blocks
            pr.create_review(
                commit=repo.get_commit(commit_sha),
                body=comment_body,
                event="COMMENT",
                comments=github_comments
            )
        else:
            # Fallback to standard issue comment
            logger.info("No inline suggestions found. Posting as general issue comment.")
            pr.create_issue_comment(comment_body)
            
        return True

    try:
        # Offload IO-bound operation
        await asyncio.to_thread(post_review)
        logger.info("Successfully posted review to PR #%s in repository %s", pr_number, repo_name)
        
    except Exception as e:
        logger.error("Failed to publish PR comment for PR #%s: %s", pr_number, e)
        # Raise here to ensure the swarm execution reflects the failure
        raise
