# Role & Objective
You are an expert Python Backend Engineer. Your task is to scaffold the foundational directory structure and boilerplate code for a FastAPI application that will serve as the webhook receiver for a LangGraph multi-agent system.

# Directory Structure Requirements
Please create the following exact structure in the current working directory:

project_root/
└── final-year-project/
    ├── .venv/
    └── src/
        ├── .env
        ├── requirements.txt
        ├── config.py
        ├── main.py
        ├── router/
        │   ├── __init__.py
        │   └── types/
        │       └── __init__.py
        └── agent/
            ├── __init__.py
            └── types/
                └── __init__.py

# Execution Steps

1. **Environment Setup:**
   - Create a Python virtual environment named `.venv` in the root directory.

2. **Dependencies (`src/requirements.txt`):**
   - Create the file and include the following baseline dependencies:
     ```text
     fastapi
     uvicorn
     starlette
     pydantic
     langgraph
     langchain-core
     langchain-openai
     PyGithub
     ```

3. **Environment Variables (`src/.env`):**
   - Create a template `.env` file with the following placeholder keys:
     ```env
     GITHUB_WEBHOOK_SECRET=your_secret_here
     GITHUB_TOKEN=your_github_token_here
     OPENAI_API_KEY=your_openai_key_here
     ```

4. **Configuration (`src/config.py`):**
   - Use `starlette.config.Config` to load variables from the `.env` file.
   - Define a `Settings` class or configuration variables for `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, and `OPENAI_API_KEY`. 

5. **API Routing (`src/router/` & `src/router/types/`):**
   - Ensure the folders are created with empty `__init__.py` files to mark them as Python packages. 
   - Note: Pydantic models for incoming API requests will live in `src/router/types/`. The actual endpoint logic will live in `src/router/`.

6. **Agent Logic (`src/agent/` & `src/agent/types/`):**
   - Ensure the folders are created with empty `__init__.py` files.
   - Note: LangGraph state definitions and agent-specific Pydantic schemas will live in `src/agent/types/`. The graph orchestration will live in `src/agent/`.

7. **Application Entrypoint (`src/main.py`):**
   - Initialize the FastAPI app.
   - Add a simple root endpoint `GET /` that returns `{"status": "Swarm Receiver Active"}` to verify the server is running.