# Role & Objective
You are an expert AI Engineer and Python Backend Developer specializing in LangChain, LangGraph, and the Model Context Protocol (MCP). Your objective is to build a multi-agent orchestration graph that uses MCP to load GitHub tools, and synthesizes its findings into a structured output containing exact, line-by-line code suggestions for a GitHub Pull Request.

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
│   │   └── publisher.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── diff_parser.py
│   └── graph/
│       ├── __init__.py
│       └── graph.py
└── swarm.py (Entrypoint)

# Execution Steps

1. **Define the Structured Output Schema (`src/agent/types/inline_comments.py`):**
   - Create Pydantic models to force strict JSON output.
   - ```python
     from pydantic import BaseModel, Field
     from typing import List

     class InlineSuggestion(BaseModel):
         file_path: str = Field(description="The exact relative path to the file.")
         line_number: int = Field(description="The exact integer line number in the new file where the issue occurs.")
         suggestion_body: str = Field(description="The comment body. MUST include the corrected code wrapped in standard GitHub ```suggestion\\n [code] \\n``` markdown block.")

     class SynthesizerOutput(BaseModel):
         general_summary: str = Field(description="The overall prioritized markdown summary.")
         inline_suggestions: List[InlineSuggestion] = Field(description="List of specific line-by-line code fixes.")
     ```

2. **Update the Swarm State (`src/agent/workflow/state/state.py`):**
   - Add `commit_sha` (required to anchor GitHub comments) and `inline_suggestions`.
   - ```python
     from typing import TypedDict, List
     from src.agent.types.inline_comments import InlineSuggestion

     class SwarmState(TypedDict):
         pr_number: int
         repo_name: str
         commit_sha: str 
         code_diff: str
         annotated_diff: str # For the line number trick
         architect_review: str
         security_review: str
         optimizer_review: str
         final_comment: str
         inline_suggestions: List[InlineSuggestion]
     ```

3. **The "Prompt Engineering Trick" Utility (`src/agent/workflow/utils/diff_parser.py`):**
   - Write a function `annotate_diff_with_line_numbers(raw_diff: str) -> str`.
   - **Logic Constraint:** It must parse unified diff `@@ -R,r +N,n @@` headers. It needs to keep a running counter of the right-side (New File) line numbers. Prepend `[Line {N}] ` to every context (starts with ` `) and added (starts with `+`) line in the diff string. Skip deleted lines (`-`). This guarantees the LLM never hallucinates line numbers.

4. **Initialize MCP Client & LLM (`src/agent/workflow/mcp/client.py` & `llm.py`):**
   - Use `MultiServerMCPClient` with the `"transport": "http"` configuration to connect to `https://api.githubcopilot.com/mcp/` without throwing a 405 error.
   - Bind these tools to your `ChatOpenAI` model (`temperature=0`).

5. **Build the Agent Nodes (`src/agent/workflow/nodes/nodes.py`):**
   - `architect_node`, `security_node`, `optimizer_node`: Standard parallel nodes using the MCP-bound LLM.
   - **`synthesizer_node` (CRITICAL UPDATE):** - Use `.with_structured_output(SynthesizerOutput)` when invoking the LLM here.
     - **Prompt:** Instruct the Lead Engineer to read the `annotated_diff` (which has the `[Line X]` prefixes) and the specialist reviews, and output the exact JSON structure matching `SynthesizerOutput`.
     - Return: `{"final_comment": result.general_summary, "inline_suggestions": result.inline_suggestions}`

6. **Create the Publisher (`src/agent/workflow/tools/publisher.py`):**
   - Write `async def publish_bundled_review(repo_name, pr_number, commit_sha, summary, suggestions)`
   - Run PyGithub logic inside `asyncio.to_thread`.
   - Map your `inline_suggestions` into the GitHub dictionary format (`{"path": p, "line": l, "body": b}`).
   - Call `pr.create_review(commit=repo.get_commit(commit_sha), body=summary, event="COMMENT", comments=mapped_suggestions)`.

7. **Wire the Graph & Entrypoint (`src/agent/workflow/graph/graph.py` & `swarm.py`):**
   - In `swarm.py`, ensure your `run_swarm` function receives `commit_sha`.
   - Call `annotate_diff_with_line_numbers(code_diff)` and pass it into the initial state as `annotated_diff`.
   - After `swarm_app.invoke()`, pass the resulting `final_comment` and `inline_suggestions` to `publish_bundled_review`.

*Note: You must also update `src/router/webhook.py` to extract `pull_request.head.sha` from the incoming GitHub webhook payload and pass it to `run_swarm`.*