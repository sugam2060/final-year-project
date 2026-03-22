import hmac
import hashlib
import asyncio
from fastapi import APIRouter, Request, HTTPException, status
from github import Github
from config import settings
from router.types.webhook_types import PullRequestEvent
from agent.dummy_agent import run_swarm

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
    Handles signature verification and filters for Pull Request actions.
    """
    # 1. Security First: Verify Signature
    # We read the raw body once here. Starlette caches it for subsequent JSON parsing.
    await verify_signature(request)
    
    # 2. Extract Event Type
    github_event = request.headers.get("X-GitHub-Event", "unknown")
    
    # 3. Parse JSON Body (Generic Dict to avoid 422 errors)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # 4. Handle PR Events
    if github_event == "pull_request":
        # Zero-Trust Parsing (Constraint 3): Convert dict to Pydantic model
        try:
            pr_event = PullRequestEvent(**payload)
        except Exception as e:
             # If it's a pull_request event but missing our required fields, we log and ignore
             logger.warning("Incomplete PR Event received: %s", e)
             return {"status": "ignored", "reason": "incomplete_pr_data"}

        # Filter for relevant actions
        if pr_event.action not in ["opened", "synchronize"]:
            return {"status": "ignored", "action": pr_event.action}

        # Constraint 1: Offload blocking calls
        def process_swarm():
            # Get code diff
            repo = github_client.get_repo(pr_event.repository.full_name)
            pr = repo.get_pull(pr_event.pull_request.number)
            
            # Constraint 7 filters applied here...
            files = pr.get_files()
            diff_chunks = []
            for file in files:
                if file.patch and len(file.patch) < 51200: # 50KB Guardrail
                    # Directory/Extension filter check...
                    ext = "." + file.filename.split(".")[-1] if "." in file.filename else ""
                    if ext.lower() not in ['.png', '.jpg', '.zip', '.pem']:
                         diff_chunks.append(f"File: {file.filename}\n{file.patch}")
            
            diff_string = "\n\n".join(diff_chunks)
            run_swarm(pr_event.pull_request.number, diff_string)

        # Offload to threadpool
        asyncio.create_task(asyncio.to_thread(process_swarm))
        
        return {"status": "success", "event": "pull_request", "action": pr_event.action}

    # 5. Handle Other Events (Return 200 to acknowledge receipt)
    return {"status": "ignored", "event": github_event}
