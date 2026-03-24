# Role & Objective
You are an expert AI Engineer and Python Backend Developer specializing in LangChain, LangGraph, and the Model Context Protocol (MCP). Your objective is to build a multi-agent orchestration graph that uses MCP to load GitHub tools, synthesizes its findings into a structured output containing exact, line-by-line code suggestions, and publishes the review using the standard `PyGithub` package. The system supports a dual-provider LLM strategy (OpenAI and NVIDIA), conversational follow-up reviews, and a **File Reviewer Subgraph** for selective, file-scoped analysis.

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
│   │   └── state.py          (SwarmState + FileReviewState)
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── llm.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── nodes.py           (PR-wide: bouncer, dispatcher, synthesizer)
│   │   └── file_reviewer.py   (Subgraph: triage, file-scoped specialists, local synthesis)
│   ├── tools/
│   │   ├── __init__.py
│   │   └── publisher.py       (Standard PyGithub implementation)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── diff_parser.py
│   │   ├── filter_utils.py    (Bouncer utilities)
│   │   └── dispatcher_utils.py (Dispatcher utilities)
│   └── graph/
│       ├── __init__.py
│       └── graph.py           (Parent graph + subgraph wiring)
└── swarm.py (Entrypoint)

# Execution Steps

1. **Define the Structured Output Schema (`src/agent/types/inline_comments.py`):**
   - Create Pydantic models for structured review output (`SynthesizerOutput`).

2. **Update the Swarm State (`src/agent/workflow/state/state.py`):**
   - `SwarmState`: PR-wide keys for review metadata, conversational context, and parallel results.
   - `FileReviewState`: File-scoped keys for triage output, file-level specialist reviews, and local synthesis output.

3. **The "Diff Annotation" Utility (`src/agent/workflow/utils/diff_parser.py`):**
   - Write `annotate_diff_with_line_numbers(raw_diff: str) -> str`.
   - Prepend `[Line X]` to every context and added line to prevent LLM hallucinations.

4. **Update Webhook Router (`src/router/webhook.py`):**
   - Listen for `pull_request`, `issue_comment`, and `pull_request_review_comment` events.
   - Implement safety checks for bot comments while allowing manually triggered @swarm mentions.

5. **Entry-Level Orchestration (The Bouncer & Dispatcher):**
   - **Bouncer:** Implement a deterministic node to filter "junk" files (e.g., `package-lock.json`) and enforce a 1,000-line logic limit.
   - **Dispatcher:** Use LangGraph's Map-Reduce (Send API) to slice the diff by file and dispatch each file into a **File Reviewer Subgraph** instance.

6. **File Reviewer Subgraph (`src/agent/workflow/nodes/file_reviewer.py`):**
   - **Triage Node (Deterministic):** Classify file by extension to select relevant specialists. $O(1)$ dictionary lookup.
   - **Selective Specialists (Parallel):** Run only relevant file-scoped specialists (e.g., Security + Optimizer for `.py`). Each sees only one file's diff.
   - **Local Synthesis Node:** Compress findings into a compact JSON summary before returning to the parent graph. This is the key hallucination and token reducer.

7. **Initialize MCP Client & LLM Factory (`src/agent/workflow/mcp/client.py` & `llm.py`):**
   - Bind dynamic GitHub tools from MCP to your model for ANALYSIS ONLY.
   - **LLM Selection Logic:** Implement a factory in `llm.py` that switches between `ChatOpenAI` and `ChatNVIDIA`.

8. **PR-Wide Specialist Nodes (`src/agent/workflow/nodes/nodes.py`):**
   - `architect_node`, `security_node`, `optimizer_node`, `blast_radius_node`: Parallel analysis nodes for cross-file architectural impact.
   - Inject repository and PR context into the prompts to prevent tool hallucinations.
   - **NVIDIA Guideline:** Instruct LLM to use unquoted integers for numeric tool parameters (e.g., `perPage: 5`).

9. **Synthesizer Node (`src/agent/workflow/nodes/nodes.py`):**
   - Consolidate findings from PR-wide specialists AND file-scoped subgraph results.
   - Use `with_structured_output(SynthesizerOutput)` for initial reviews and free-form Markdown for follow-ups.

10. **Publisher Tools (`src/agent/workflow/tools/publisher.py`):**
    - **CRITICAL:** Use a unified `publish_pr_comment` function (via `PyGithub`).
    - **Option B (PR Protection):** If `commit_sha` is provided, post a formal Pull Request Review. Scan for `SEVERITY: CRITICAL` in the synthesized comment body to trigger a `REQUEST_CHANGES` event (blocking the merge); otherwise use `APPROVE` to unlock code merging.
    - If `commit_sha` is NOT provided (conversational mode), post a standard Issue Comment.
    - **Validation:** Always validate `suggestion.file_path` against actual PR files to prevent GitHub 422 errors.

11. **Wire the Graph & Entrypoint (`src/agent/workflow/graph/graph.py` & `swarm.py`):**
    - Compile the File Reviewer Subgraph as a standalone `StateGraph`.
    - Register the compiled subgraph as a node in the parent graph.
    - Connect: `START → Bouncer → (Dispatcher + PR-Wide Specialists) → Synthesizer → END`.
    - The `run_swarm` entrypoint invokes the graph and calls the unified publisher.

*Note: Adhere to asynchronous performance constraints. Use explicit timeouts (20s) for GitHub API calls and $O(1)$ lookup strategies for filtering.*