import hmac
import hashlib
import asyncio
from fastapi import APIRouter, Request, HTTPException, status
from github import Github
from config import settings
from router.types.webhook_types import PullRequestEvent
from agent.dummy_agent import run_swarm

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
async def github_webhook_receiver(request: Request, payload: PullRequestEvent):
    """
    Webhook receiver for GitHub Pull Request events.
    Strictly validated using Pydantic (Constraint 3).
    """
    # Security: Verify Signature (Constraint 3)
    await verify_signature(request)
    
    # Filter for relevant actions
    if payload.action not in ["opened", "synchronize"]:
        return {"status": "ignored", "action": payload.action}
    
    # Constraint 1: PyGithub is synchronous, so we offload blocking calls to threadpool.
    def fetch_github_diff():
        # Access repository and pull request
        repo = github_client.get_repo(payload.repository.full_name)
        pr = repo.get_pull(payload.pull_request.number)
        
        # Constraint 5: Use ''.join() for efficiency and filter out empty patches
        # pr.get_files() returns a PaginatedList
        files = pr.get_files()
        diff_chunks = []
        for file in files:
            if file.patch:
                diff_chunks.append(file.patch)
        
        return "\n".join(diff_chunks)

    try:
        # Offload IO-bound operation
        code_diff = await asyncio.to_thread(fetch_github_diff)
        
        # Trigger dummy agent (Constraint 1: also offloaded)
        await asyncio.to_thread(run_swarm, payload.pull_request.number, code_diff)
        
        return {"status": "success", "message": "Swarm activated for PR audit"}
    
    except Exception as e:
        # Constraint 4: Centralized error handling would be better, but adding basic catch here.
        # Note: In a production app, we would use a logger.
        print(f"CRITICAL ERROR in Webhook Processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal processing error"
        )
