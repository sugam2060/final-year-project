import hmac
import hashlib
import asyncio
from fastapi import APIRouter, Request, HTTPException, status
from github import Github
from config import settings
from router.types.webhook_types import PullRequestEvent, IssueCommentEvent, PullRequestReviewCommentEvent
from agent.swarm import run_swarm

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

# Constraint 2: Explicit timeouts. PyGithub timeout is in seconds.
github_client = Github(login_or_token=str(settings.GITHUB_TOKEN), timeout=15)

async def verify_signature(request: Request):
    """Constraint 3: Validate X-Hub-Signature-256 header using GITHUB_WEBHOOK_SECRET."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
         raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED, 
             detail="Missing X-Hub-Signature-256 header"
         )
    
    secret = str(settings.GITHUB_WEBHOOK_SECRET).encode()
    body = await request.body()
    
    hash_object = hmac.new(secret, body, hashlib.sha256)
    expected_signature = f"sha256={hash_object.hexdigest()}"
    
    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid HMAC signature"
        )

@router.post("/webhook")
async def github_webhook_receiver(request: Request):
    """
    Webhook receiver for GitHub events.
    Handles signature verification and filters for Pull Request and Issue Comment actions.
    """
    # 0. Log reception (Diagnostic)
    github_event = request.headers.get("X-GitHub-Event", "unknown")
    logger.info(">>> [WEBHOOK] Received %s event", github_event)
    
    # 1. Security First: Verify Signature
    await verify_signature(request)
    
    # 2. Extract Event Type
    github_event = request.headers.get("X-GitHub-Event", "unknown")
    
    # 3. Parse JSON Body (Generic Dict to avoid 422 errors)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # 4. Handle PR Events (Initial Reviews)
    if github_event == "pull_request":
        return await _handle_pull_request_event(payload)

    # 5. Handle Issue Comment Events (Conversational Reviews)
    if github_event == "issue_comment":
        return await _handle_issue_comment_event(payload)

    # 6. Handle PR Review Comment Events (Conversational Reviews in inline reviews)
    if github_event == "pull_request_review_comment":
        return await _handle_review_comment_event(payload)

    # 7. Handle Other Events (Return 200 to acknowledge receipt)
    return {"status": "ignored", "event": github_event}


async def _handle_pull_request_event(payload: dict):
    """Handles pull_request webhook events — triggers initial code review."""
    # Zero-Trust Parsing: Convert dict to Pydantic model
    try:
        pr_event = PullRequestEvent(**payload)
    except Exception as e:
        logger.warning("Incomplete PR Event received: %s", e)
        return {"status": "ignored", "reason": "incomplete_pr_data"}

    # Filter for relevant actions
    # We include 'synchronize' to allow the swarm to review new commits pushed to an open PR
    if pr_event.action not in ["opened", "reopened", "synchronize"]:
        return {"status": "ignored", "action": pr_event.action}

    # Constraint 1: Full Async orchestration
    async def process_swarm_async():
        # Get code diff (offloaded to thread as PyGithub is sync)
        def fetch_diff():
            repo = github_client.get_repo(pr_event.repository.full_name)
            pr = repo.get_pull(pr_event.pull_request.number)
            
            files = pr.get_files()
            diff_chunks = []
            for file in files:
                if file.patch and len(file.patch) < 51200:  # 50KB Guardrail
                    ext = "." + file.filename.split(".")[-1] if "." in file.filename else ""
                    if ext.lower() not in ['.png', '.jpg', '.zip', '.pem']:
                         diff_chunks.append(f"diff --git a/{file.filename} b/{file.filename}\n{file.patch}")
            
            return "\n\n".join(diff_chunks)
        
        try:
            # 1. Non-blocking Fetch
            diff_string = await asyncio.to_thread(fetch_diff)
            
            # 2. Invoke LangGraph Orchestration (Async-native)
            await run_swarm(
                pr_number=pr_event.pull_request.number,
                code_diff=diff_string,
                repo_name=pr_event.repository.full_name,
                commit_sha=pr_event.pull_request.head.sha,
                pr_author=payload.get("pull_request", {}).get("user", {}).get("login", "developer"),
                is_conversational=False,
                user_message="",
                conversation_history=""
            )
        except Exception as e:
            logger.error("Async Scaffolding Failure: %s", e)

    # Trigger background execution without blocking the response
    asyncio.create_task(process_swarm_async())
    
    return {"status": "success", "event": "pull_request", "action": pr_event.action}


async def _handle_issue_comment_event(payload: dict):
    """Handles issue_comment webhook events — triggers conversational code reviews."""
    # Zero-Trust Parsing
    try:
        comment_event = IssueCommentEvent(**payload)
    except Exception as e:
        logger.warning("Incomplete Issue Comment Event received: %s", e)
        return {"status": "ignored", "reason": "incomplete_comment_data"}

    # 1. Action Check: Only process newly created comments
    if comment_event.action != "created":
        return {"status": "ignored", "action": comment_event.action}

    # 2. Trigger Check: Check if comment mentions @swarm and is NOT a bot response
    comment_body = comment_event.comment.body
    
    # safeguard: ignore if this comment was generated by the swarm itself to avoid loop
    if "<!-- SWARM_BOT_ID -->" in comment_body:
        return {"status": "ignored", "reason": "self_response_loop"}

    if "@swarm" not in comment_body.lower():
        return {"status": "ignored", "reason": "no_swarm_mention"}

    # 3. Safeguard Check: Prevent infinite bot loops
    # Only block if the bot *itself* is mentioning @swarm (which it shouldn't do)
    # This allows the user (e.g. sugam2060) to trigger it even if they share the login.
    comment_author = comment_event.comment.user.login
    if "[bot]" in comment_author:
        logger.info("Ignoring automated bot trigger from %s on PR #%s", comment_author, comment_event.issue.number)
        return {"status": "ignored", "reason": "bot_trigger"}

    repo_name = comment_event.repository.full_name
    pr_number = comment_event.issue.number

    logger.info("@swarm mentioned in PR #%s by %s — triggering conversational review", pr_number, comment_author)

    async def process_conversational_swarm():
        def fetch_context():
            """Fetch PR diff and conversation history using PyGithub (sync)."""
            repo = github_client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # 1. Fetch the code diff
            files = pr.get_files()
            diff_chunks = []
            for file in files:
                if file.patch and len(file.patch) < 51200:
                    ext = "." + file.filename.split(".")[-1] if "." in file.filename else ""
                    if ext.lower() not in ['.png', '.jpg', '.zip', '.pem']:
                        diff_chunks.append(f"diff --git a/{file.filename} b/{file.filename}\n{file.patch}")
            diff_string = "\n\n".join(diff_chunks)

            # 2. Fetch the last 5 comments for conversation context
            all_comments = list(pr.get_issue_comments())
            recent_comments = all_comments[-5:] if len(all_comments) > 5 else all_comments
            history_parts = []
            for c in recent_comments:
                history_parts.append(f"**@{c.user.login}** said:\n{c.body}")
            conversation_history = "\n\n---\n\n".join(history_parts)

            # 3. Get commit SHA for anchoring
            commit_sha = pr.head.sha

            return diff_string, conversation_history, commit_sha

        try:
            diff_string, conversation_history, commit_sha = await asyncio.to_thread(fetch_context)

            await run_swarm(
                pr_number=pr_number,
                code_diff=diff_string,
                repo_name=repo_name,
                commit_sha=commit_sha,
                pr_author=comment_author,
                is_conversational=True,
                user_message=comment_body,
                conversation_history=conversation_history
            )
        except Exception as e:
            logger.error("Conversational Swarm Failure for PR #%s: %s", pr_number, e)

    # Trigger background execution
    asyncio.create_task(process_conversational_swarm())

    return {"status": "success", "event": "issue_comment", "pr_number": pr_number}


async def _handle_review_comment_event(payload: dict):
    """Handles pull_request_review_comment events — triggers conversational reviews on inline suggestions."""
    try:
        review_event = PullRequestReviewCommentEvent(**payload)
    except Exception as e:
        logger.warning("Incomplete Review Comment Event received: %s", e)
        return {"status": "ignored", "reason": "incomplete_review_comment_data"}

    # 1. Action Check: Only process newly created comments
    if review_event.action != "created":
        return {"status": "ignored", "action": review_event.action}

    # 2. Trigger Check: Check for @swarm mention and avoid bot loops
    comment_body = review_event.comment.body
    
    # safeguard: ignore if this comment was generated by the swarm itself to avoid loop
    if "<!-- SWARM_BOT_ID -->" in comment_body:
        return {"status": "ignored", "reason": "self_response_loop_inline"}

    if "@swarm" not in comment_body.lower():
        return {"status": "ignored", "reason": "no_swarm_mention"}

    # 3. Safeguard Check: Prevent infinite bot loops
    comment_author = review_event.comment.user.login
    if "[bot]" in comment_author:
        logger.info("Ignoring automated bot trigger from %s on PR #%s", comment_author, review_event.pull_request.number)
        return {"status": "ignored", "reason": "bot_trigger"}

    repo_name = review_event.repository.full_name
    pr_number = review_event.pull_request.number

    logger.info("@swarm mentioned in review comment PR #%s — triggering conversational review", pr_number)

    async def process_review_swarm():
        def fetch_context():
            repo = github_client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # 1. OPTIMIZATION: Only review the specific lines the user commented on.
            path = payload.get("comment", {}).get("path")
            diff_hunk = payload.get("comment", {}).get("diff_hunk")
            if path and diff_hunk:
                diff_string = f"diff --git a/{path} b/{path}\n{diff_hunk}"
            else:
                # Fallback to full PR diff if the hunk is somehow missing
                files = pr.get_files()
                diff_chunks = []
                for file in files:
                    if file.patch and len(file.patch) < 51200:
                        ext = "." + file.filename.split(".")[-1] if "." in file.filename else ""
                        if ext.lower() not in ['.png', '.jpg', '.zip', '.pem']:
                            diff_chunks.append(f"diff --git a/{file.filename} b/{file.filename}\n{file.patch}")
                diff_string = "\n\n".join(diff_chunks)

            # 2. Fetch history (mixing issue comments and review comments for better context)
            issue_comments = list(pr.get_issue_comments())[-3:]
            review_comments = list(pr.get_review_comments())[-3:]
            recent_comments = sorted(issue_comments + review_comments, key=lambda x: x.created_at)
            
            history_parts = []
            for c in recent_comments[-5:]:
                history_parts.append(f"**@{c.user.login}** said:\n{c.body}")
            conversation_history = "\n\n---\n\n".join(history_parts)

            return diff_string, conversation_history, pr.head.sha

        try:
            diff_string, conversation_history, commit_sha = await asyncio.to_thread(fetch_context)
            await run_swarm(
                pr_number=pr_number,
                code_diff=diff_string,
                repo_name=repo_name,
                commit_sha=commit_sha,
                pr_author=comment_author,
                is_conversational=True,
                user_message=comment_body,
                conversation_history=conversation_history
            )
        except Exception as e:
            logger.error("Review Comment Swarm Failure for PR #%s: %s", pr_number, e)

    asyncio.create_task(process_review_swarm())
    return {"status": "success", "event": "pull_request_review_comment", "pr_number": pr_number}

