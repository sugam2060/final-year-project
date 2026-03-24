import asyncio
import logging
from typing import List, Optional
from github import Github
from config import settings
from agent.types.inline_comments import InlineSuggestion

# Configure logging
logger = logging.getLogger(__name__)

async def publish_pr_comment(
    repo_name: str, 
    pr_number: int, 
    comment_body: str, 
    commit_sha: Optional[str] = None, 
    inline_suggestions: Optional[List[InlineSuggestion]] = None
):
    """
    Unified publisher for both initial reviews and conversational replies.
    
    Logic:
    - If commit_sha and inline_suggestions are provided: Creates a structured PR Review.
    - Otherwise: Posts a standard issue comment.
    
    Constraint 1: Uses asyncio.to_thread for blocking PyGithub calls.
    Includes Path Validation to prevent 422 errors.
    """
    logger.info("Initializing PR publication for %s PR #%s...", repo_name, pr_number)
    
    def post_review():
        # Authenticate
        g = Github(login_or_token=str(settings.GITHUB_TOKEN), timeout=20)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        if commit_sha:
            # Determine Review State
            event_type = "APPROVE"
            if "SEVERITY: CRITICAL" in comment_body.upper():
                event_type = "REQUEST_CHANGES"

            # PROACTIVE SELF-REVIEW CHECK:
            # GitHub does not allow a user to Approve or Request Changes on their own PR.
            # Detect this upfront and use COMMENT to avoid the 422 error entirely.
            authenticated_user = g.get_user().login
            pr_author = pr.user.login
            if authenticated_user == pr_author:
                logger.warning(
                    "Self-Review detected: Bot user '%s' is the PR author. "
                    "Forcing event_type to 'COMMENT' (GitHub blocks Approve/Request Changes on own PRs).",
                    authenticated_user
                )
                event_type = "COMMENT"

            github_comments = []
            if inline_suggestions:
                logger.info("Validating %s inline suggestions against PR files...", len(inline_suggestions))
                pr_files = [f.filename for f in pr.get_files()]
                for suggestion in inline_suggestions:
                    if suggestion.file_path in pr_files and suggestion.line_number > 0:
                        github_comments.append({
                            "path": suggestion.file_path,
                            "line": suggestion.line_number,
                            "body": suggestion.suggestion_body
                        })
                    else:
                        logger.warning(
                            "Dropping invalid suggestion for PR #%s: Path '%s' (valid: %s), Line %s",
                            pr_number, suggestion.file_path, suggestion.file_path in pr_files, suggestion.line_number
                        )

            logger.info("Submitting %s PR Review with %s inline suggestions.", event_type, len(github_comments))
            pr.create_review(event=event_type, body=comment_body, comments=github_comments if github_comments else [])
        else:
            # Conversational reply
            logger.info("Posting as general issue comment (Conversational).")
            pr.create_issue_comment(comment_body)
            
        return True

    try:
        await asyncio.to_thread(post_review)
        logger.info("Successfully published to PR #%s in repository %s", pr_number, repo_name)
    except Exception as e:
        logger.error("Failed to publish PR comment for PR #%s: %s", pr_number, e)
        # Swallowing the error here to prevent the swarm from crashing, 
        # but we should still log it.
        pass
