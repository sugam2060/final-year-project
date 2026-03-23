# Role & Objective
You are an expert Python Backend Engineer. Your task is to build out the FastAPI server architecture established in `structure.md`. You will create the webhook endpoint to receive GitHub Pull Request events, extract the necessary data using Pydantic, fetch the code diff using PyGithub, and pass it to a dynamic agent function that supports multiple LLM providers.

# Execution Steps

1. **Environment Variables (`src/.env`):**
   - Populate the `.env` file with the following tokens:
     ```env
     GITHUB_WEBHOOK_SECRET
     GITHUB_TOKEN
     OPENAI_API_KEY
     GROQ_API_KEY
     LLM_PROVIDER=GROQ # Options: GROQ, OPENAI
     GITHUB_BOT_USERNAME=sugam2060
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
     OPENAI_API_KEY = config("OPENAI_API_KEY", cast=Secret)
     GROQ_API_KEY = config("GROQ_API_KEY", cast=Secret)
     LLM_PROVIDER = config("LLM_PROVIDER", default="OPENAI")
     GITHUB_BOT_USERNAME = config("GITHUB_BOT_USERNAME", default="sugam2060")
     ```

3. **Pydantic Types (`src/router/types/webhook_types.py`):**
   - Create models to parse GitHub payloads (`PullRequestEvent` and `IssueCommentEvent`).
   - Use `extra="allow"` to handle extra fields from GitHub gracefully.

4. **Webhook Router (`src/router/webhook.py`):**
   - Create the FastAPI router.
   - Initialize the `PyGithub` client using settings.
   - Implement two handlers:
     - `_handle_pull_request_event`: For initial reviews on `opened`/`reopened` PRs. (Exclude `synchronize` to prevent triggering on every push).
     - `_handle_issue_comment_event`: For conversational reviews triggered by `@swarm`.
   - **Safeguard:** Use `settings.GITHUB_BOT_USERNAME` to ignore personal/bot comments.

5. **Application Entrypoint (`src/main.py`):**
   - Import the webhook router and include it in the main FastAPI app.
   - Initialize logging globally.

6. **Requirements (`src/requirements.txt`):**
   - Include `fastapi`, `uvicorn`, `starlette`, `pydantic`, `pydantic-settings`, `langgraph`, `langchain-core`, `langchain-openai`, `langchain-groq`, `PyGithub`, `langchain-mcp-adapters`, and `mcp`.

*Note: All GitHub API calls (except during webhook processing) should flow through the MCP client in the agent module.*