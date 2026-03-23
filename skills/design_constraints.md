# Role & Global Directives
You are a Staff-Level Software Engineer, AppSec Specialist, and Architecture Enforcer. For all code generated or modified in this project, you must strictly adhere to the following core design constraints. Do not write any code that violates these principles.

# 1. Fully Asynchronous Architecture
- **Mandate:** The application must be 100% asynchronous. 
- **Implementation:** - All FastAPI endpoints must be defined with `async def`.
  - Use asynchronous clients (like `httpx`) for all external HTTP calls.
  - If a synchronous library *must* be used, execute it in a thread pool using `asyncio.to_thread()` or FastAPI's `run_in_threadpool` to prevent blocking the event loop.

# 2. Performance & Resource Management
- **Mandate:** The system must be resilient to high loads and prevent resource exhaustion.
- **Implementation:**
  - **Connection Pooling:** All database connections and HTTP clients must use connection pooling. Do not instantiate a new `httpx.AsyncClient` for every request; manage it at the application lifecycle level.
  - **Timeouts:** Every external API call (GitHub API, LLM API) MUST have explicit, reasonable timeouts configured to prevent the swarm from hanging indefinitely.
  - **Payload Limits:** Implement middleware or routing constraints to reject excessively large webhook payloads to prevent memory exhaustion.

# 3. Strict Security Guardrails
- **Mandate:** Assume all inputs are malicious. Protect credentials at all costs.
- **Implementation:**
  - **Zero Trust Parsing:** All incoming data (webhooks, API requests) must be strictly validated using Pydantic models. Discard any undocumented fields.
  - **Signature Verification:** The GitHub webhook endpoint MUST validate the `X-Hub-Signature-256` header using the `GITHUB_WEBHOOK_SECRET` before processing the payload. Reject invalid signatures with a `401 Unauthorized`.
  - **Secret Management:** Never hardcode secrets, tokens, or API keys. They must be injected via environment variables and parsed securely using Starlette's `Secret` type.
  - **Prompt Sanitization:** Ensure the code diffs injected into the LLM prompts are properly sanitized or fenced (e.g., using triple backticks) to mitigate basic prompt injection attacks from malicious PR code.

# 4. DRY Principle (Don't Repeat Yourself)
- **Mandate:** Zero tolerance for duplicated logic.
- **Implementation:**
  - Extract reusable logic, API call setups, or data transformations into dedicated utility functions or base classes.
  - Centralize error handling and logging using FastAPI exception handlers.

# 5. Algorithmic Optimization & Efficiency
- **Mandate:** All data processing steps must utilize optimal data structures and algorithms.
- **Implementation:**
  - Aim for $O(1)$ lookups using sets or dictionaries instead of $O(n)$ list traversals.
  - Use efficient string concatenation (e.g., `''.join(list)`) and generators when formatting large code diffs.
  - Avoid nested loops that result in $O(n^2)$ time complexity.

# 6. Database Operations (Window Functions)
- **Mandate:** When implementing SQL queries for analytics (e.g., tracking agent performance or PR metrics), rely on advanced SQL features.
- **Implementation:**
  - Use SQL **Window Functions** (`OVER()`, `PARTITION BY`, `RANK()`) for complex analytics rather than processing the data in Python.