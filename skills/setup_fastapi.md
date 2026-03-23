# Role & Objective
You are an expert Python Backend Engineer. Your task is to build out the FastAPI server architecture established in `structure.md`. You will create the webhook endpoint to receive GitHub Pull Request events, extract the necessary data using Pydantic, fetch the code diff using PyGithub, and pass it to a dummy agent function.

# Execution Steps

1. **Environment Variables (`src/.env`):**
   - Populate the `.env` file with the following tokens:
     ```env
     GITHUB_WEBHOOK_SECRET
     GITHUB_TOKEN
     ```

2. **Configuration (`src/config.py`):**
   - Implement Starlette config to securely load the tokens.
   - Code requirement:
     ```python
     from starlette.config import Config
     from starlette.datastructures import Secret

     config = Config(".env")
     GITHUB_WEBHOOK_SECRET = config("GITHUB_WEBHOOK_SECRET", cast=Secret)
     GITHUB_TOKEN = config("GITHUB_TOKEN", cast=Secret)
     ```

3. **Pydantic Types (`src/router/types/webhook_types.py`):**
   - Create this file to parse the incoming GitHub webhook payload.
   - We only need the PR number, repository name, and action type.
   - Code requirement:
     ```python
     from pydantic import BaseModel

     class Repository(BaseModel):
         full_name: str

     class PullRequest(BaseModel):
         number: int

     class PullRequestEvent(BaseModel):
         action: str
         repository: Repository
         pull_request: PullRequest
     ```

4. **Dummy Agent (`src/agent/dummy_agent.py`):**
   - Create a simple function to simulate the LangGraph entry point.
   - Code requirement:
     ```python
     def run_swarm(pr_number: int, code_diff: str):
         print(f"--- SWARM ACTIVATED FOR PR #{pr_number} ---")
         print(f"Received Diff Length: {len(code_diff)} characters")
         print("Agent analysis pending...")
         print("-----------------------------------")
     ```

5. **Webhook Router (`src/router/webhook.py`):**
   - Create the FastAPI router.
   - Initialize the `PyGithub` client using the token from `config.py`.
   - Create a `POST /webhook` endpoint that accepts the `PullRequestEvent`.
   - Logic: 
     - If the action is not "opened" or "synchronize", return early.
     - Use `github_client.get_repo()` and `repo.get_pull()` to access the PR.
     - Call `pr.get_files()` and concatenate the `.patch` property of each file to create the full string diff.
     - Pass the `pr.number` and the compiled diff string to `run_swarm()`.

6. **Application Entrypoint (`src/main.py`):**
   - Import the webhook router and include it in the main FastAPI app.
   - ```python
     from fastapi import FastAPI
     from src.router.webhook import router as webhook_router

     app = FastAPI()
     app.include_router(webhook_router)
     ```