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
        
        if commit_sha and inline_suggestions:
            logger.info("Validating %s inline suggestions against PR files...", len(inline_suggestions))
            
            # Fetch valid file paths from the PR to prevent 422 errors
            pr_files = [f.filename for f in pr.get_files()]
            github_comments = []
            
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

            if github_comments:
                logger.info("Creating bundled PR review with %s valid inline suggestions...", len(github_comments))
                pr.create_review(
                    commit=repo.get_commit(commit_sha),
                    body=comment_body,
                    event="COMMENT",
                    comments=github_comments
                )
            else:
                logger.info("No valid inline suggestions remain. Falling back to issue comment.")
                pr.create_issue_comment(f"{comment_body}\n\n*Note: Suggestions were found but their file paths could not be accurately resolved.*")
        else:
            # Conversational reply or review with no suggestions
            logger.info("Posting as general issue comment (Conversational/No Suggestions).")
            pr.create_issue_comment(comment_body)
            
        return True

    try:
        await asyncio.to_thread(post_review)
        logger.info("Successfully published to PR #%s in repository %s", pr_number, repo_name)
    except Exception as e:
        logger.error("Failed to publish PR comment for PR #%s: %s", pr_number, e)
        raise
