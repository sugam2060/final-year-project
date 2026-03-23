# Role & Objective
You are an expert AI Engineer and Python Backend Developer specializing in LangChain, LangGraph, and the Model Context Protocol (MCP). Your objective is to build a multi-agent orchestration graph that uses MCP to load GitHub tools, synthesizes its findings into a structured output containing exact, line-by-line code suggestions, and publishes the review using the standard `PyGithub` package. The system supports a dual-provider LLM strategy (OpenAI and NVIDIA) and conversational follow-up reviews.

# Architecture & Directory Constraints
Before writing the logic, strictly adhere to this hyper-modular folder structure:

Expected Structure:
src/agent/
├── types/
│   ├── __init__.py
│   └── inline_comments.py
├── workflow/
│   ├── __init__.py
│   ├── state/
│   │   ├── __init__.py
│   │   └── state.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── llm.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   └── nodes.py
│   ├── tools/
│   │   ├── __init__.py
│   │   └── publisher.py (Standard PyGithub implementation)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── diff_parser.py
│   └── graph/
│       ├── __init__.py
│       └── graph.py
└── swarm.py (Entrypoint)

# Execution Steps

1. **Define the Structured Output Schema (`src/agent/types/inline_comments.py`):**
   - Create Pydantic models for structured review output.

2. **Update the Swarm State (`src/agent/workflow/state/state.py`):**
   - Add necessary keys for review metadata and conversational context.

3. **The "Diff Annotation" Utility (`src/agent/workflow/utils/diff_parser.py`):**
   - Write `annotate_diff_with_line_numbers(raw_diff: str) -> str`.
   - Prepend `[Line X]` to every context and added line to prevent LLM hallucinations.

4. **Update Webhook Router (`src/router/webhook.py`):**
   - Listen for `pull_request`, `issue_comment`, and `pull_request_review_comment` events.
   - Implement safety checks for bot comments while allowing manually triggered @swarm mentions.

5. **Initialize MCP Client & LLM Factory (`src/agent/workflow/mcp/client.py` & `llm.py`):**
   - Bind dynamic GitHub tools from MCP to your model for ANALYSIS ONLY.
   - **LLM Selection Logic:** Implement a factory in `llm.py` that switches between `ChatOpenAI` and `ChatNVIDIA`.

6. **Specialist Nodes (`src/agent/workflow/nodes/nodes.py`):**
   - `architect_node`, `security_node`, `optimizer_node`: Parallel analysis nodes.
   - Inject repository and PR context into the prompts to prevent tool hallucinations.
   - **NVIDIA Guideline:** Instruct LLM to use unquoted integers for numeric tool parameters (e.g., `perPage: 5`).

7. **Synthesizer Node (`src/agent/workflow/nodes/nodes.py`):**
   - Consolidate findings. Use `with_structured_output(SynthesizerOutput)` for initial reviews and free-form Markdown for follow-ups.

8. **Publisher Tools (`src/agent/workflow/tools/publisher.py`):**
   - **CRITICAL:** Use a unified `publish_pr_comment` function (via `PyGithub`).
   - If `commit_sha` and `inline_suggestions` are provided, post a bundled Review.
   - Otherwise, post a standard Issue Comment (conversational mode).
   - **Validation:** Always validate `suggestion.file_path` against actual PR files to prevent GitHub 422 errors.

9. **Wire the Graph & Entrypoint (`src/agent/workflow/graph/graph.py` & `swarm.py`):**
   - Connect specialists to synthesizer (graph ends at synthesizer).
   - The `run_swarm` entrypoint invokes the graph and calls the unified publisher.

*Note: Adhere to asynchronous performance constraints. Use explicit timeouts (20s) for GitHub API calls.*