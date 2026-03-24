# 🐝 LangGraph PR Swarm: Multi-Agent GitHub Code Reviewer

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Framework](https://img.shields.io/badge/framework-FastAPI-green)
![Orchestration](https://img.shields.io/badge/orchestration-LangGraph-orange)
![Security](https://img.shields.io/badge/security-HMAC--SHA256-red)

A sophisticated, multi-agent AI system designed to automate and enhance GitHub Pull Request reviews. Built on top of **LangGraph**, **FastAPI**, and the **Model Context Protocol (MCP)**, this system orchestrates a "swarm" of specialized AI agents to analyze code changes and provide expert feedback directly on GitHub.

---

## 🚀 Key Features

*   **Map-Reduce Swarm Orchestration**: Leverages high-speed parallel execution. Instead of a single generic scan, it applies **Semantic Chunking** to dispatch each file into a specialized **File Reviewer Subgraph**.
*   **Precision Line-by-Line Suggestions**: Implements a custom "Precision Trick" diff-parser that prevents LLM hallucinations by annotating incoming diffs with real line numbers.
*   **80% Faster Conversational Reviews**: Features an independent logic path for `@swarm` mentions. By extracting only the relevant `diff_hunk` and bypassing the specialist swarm, it provides instant, sub-10s answers to developer pushback.
*   **Hardened Security & Branch Protection**: Automatically flags vulnerabilities with `SEVERITY: CRITICAL`. When integrated with GitHub Branch Protection, the swarm programmatically blocks merges until fixes are pushed.
*   **Dynamic Specialist Feedback**: 
    *   **🏗️ Architect Agent**: Validates structural design and adherence to patterns.
    *   **🛡️ Security Agent**: Scans for vulnerabilities, credential leaks, and insecure code.
    *   **⚡ Optimizer Agent**: Identifies performance bottlenecks and modern code efficiencies.
    *   **🌐 Blast Radius**: Predicts the downstream impact of breaking changes.
*   **Secure & Robust**: Features HMAC-SHA256 signature verification for zero-trust webhook handling and structured Pydantic data models for guaranteed JSON predictability.

---

## 🏗️ Project Structure

The project follows a hyper-modular architecture designed for scalability and clear separation of concerns:

```text
├── skills/                     # Swarm brain: design constraints & agent protocols
│   ├── langgraph_swarm.md      # Core architecture blueprint
│   ├── file_reviewer_subgraph.md # Subgraph map-reduce logic
│   ├── filter.md               # Bouncer & Triage deterministic rules
│   └── ...
├── src/
│   ├── main.py                 # FastAPI Application entry point
│   ├── config.py               # Environment & Global settings
│   ├── router/                 # Webhook Handling
│   │   ├── webhook.py          # Receives GitHub events & triggers Swarm
│   │   └── types/              # Pydantic models for webhook payloads
│   └── agent/                  # Core AI Orchestration
│       ├── swarm.py            # Entrypoint for LangGraph execution
│       └── workflow/           # Internal Graph Components
│           ├── graph/          # Parent graph topology & bifurcated routing
│           ├── nodes/          # Agent Logic & File Reviewer Subgraph
│           ├── state/          # Shared memory (TypedDict SwarmState)
│           ├── tools/          # External actions (Publisher)
│           └── utils/          # Precision Diff Parser & Dispatcher helpers
└── requirements.txt            # System dependencies
```

---

## 🔄 Core Workflow

1.  **Incoming Trigger**: A GitHub Webhook is received. `opened`/`reopened` triggers a full review; `synchronize` (new push) triggers a re-review; `review_comment` triggers a localized conversational reply.
2.  **The Bouncer (Triage)**: A deterministic node filters "junk" files (like lock files) and enforces the 1,000-line logic limit to protect token budgets.
3.  **Precision Annotation**: The PR diff is annotated with `[Line X]` markers to ensure 0% line-reference hallucinations.
4.  **Map-Reduce Dispatch**:
    *   **Fan-out (Map)**: The **Dispatcher** slices the PR by file and spawns isolated **File Reviewer Subgraph** instances.
    *   **Selective Specialists**: Each subgraph runs only relevant specialists (e.g., Security for `.py`, Architect for `.css`).
5.  **PR-Wide Analysis**: Parallel to subgraphs, high-level specialists (Architect, Security, Optimizer, Blast Radius) analyze the global impact across the entire PR.
6.  **Synthesize & Publish**: Findings are reduced into a structured `SynthesizerOutput`. If vulnerabilities exist, a **Block Merge** review is posted; otherwise, it **Approves**.

---

## 🛠️ Configuration & Setup

### 1. GitHub Configuration

#### 🔏 Personal Access Token (PAT)
The system requires a GitHub PAT to post reviews and fetch PR data.
*   **Classic PAT**: Ensure the `repo` scope is selected (Full control of repositories).
*   **Fine-grained PAT**: Grant access to:
    *   `Pull Requests` (Read & Write) - To post bundled reviews/suggestions.
    *   `Issues` (Read & Write) - To post conversational replies to `@swarm` mentions.
    *   `Contents` (Read-only) - To access repository source code for analysis.
    *   `Metadata` (Read-only) - Mandatory for all tokens.

#### ⚓ Webhook Setup
Configure your GitHub repository Webhook (`Settings > Webhooks > Add webhook`) as follows:
*   **Payload URL**: `http://[your-domain]/webhook` (Use **ngrok** for local development).
*   **Content type**: `application/json`.
*   **Secret**: Must match your `GITHUB_WEBHOOK_SECRET` in `.env`.
*   **Events**: Select **"Let me select individual events"** and check:
    *   ✅ **Pull requests** (Actions: `opened`, `reopened`, `synchronize`)
    *   ✅ **Issue comments** (For PR-level thread chat)
    *   ✅ **Pull request review comments** (For localized code chat)

### 2. Environment Variables
Create a `.env` file in the `src/` directory with the following keys:
```env
GITHUB_TOKEN=your_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_shared_secret
LLM_PROVIDER=NVIDIA # Options: OPENAI, NVIDIA
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=nvapi-...
GITHUB_BOT_USERNAME=your_bot_username
```

### 3. Running the Server
Install dependencies and start the FastAPI server:
```bash
pip install -r src/requirements.txt
python src/main.py
```


---

## 📚 Expert Skills & Constraints

The system is guided by "Skills" (brain modules) in the `skills/` directory:
- **`langgraph_swarm.md`**: Main orchestration blueprint.
- **`file_reviewer_subgraph.md`**: Map-Reduce & Subgraph patterns.
- **`filter.md`**: Bouncer & Triage deterministic rules.
- **`parallel_dispatcher.md`**: Concurrency & state aggregation logic.
- **`blast_radius.md`**: Architectural dependency prediction.

---

> [!TIP]
> **Why LangGraph?** We use LangGraph over simpler agent chains to manage cycles, complex states, and parallel "Swarm" behaviors reliably.