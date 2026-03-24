# 🐝 LangGraph PR Swarm: Multi-Agent GitHub Code Reviewer

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Framework](https://img.shields.io/badge/framework-FastAPI-green)
![Orchestration](https://img.shields.io/badge/orchestration-LangGraph-orange)
![Security](https://img.shields.io/badge/security-HMAC--SHA256-red)

A sophisticated, multi-agent AI system designed to automate and enhance GitHub Pull Request reviews. Built on top of **LangGraph**, **FastAPI**, and the **Model Context Protocol (MCP)**, this system orchestrates a "swarm" of specialized AI agents to analyze code changes and provide expert feedback directly on GitHub.

> [!CAUTION]
> ### 🚨 EXPERIMENTAL SYSTEM — READ BEFORE USE
> This project is designed for **testing, research, and experimental purposes only.**
> - **AI Hallucinations**: AI-generated code reviews can contain inaccuracies, hallucinations, or "wrong" suggestions.
> - **Do Not Rely Solely on AI**: Never merge code based ONLY on this system's feedback. **Always perform a double-check** and have a human developer verify every claim made by the swarm.
> - **Security Notice**: While the swarm is designed to find bugs, it is NOT a replacement for a professional security audit or a certified static analysis tool (SAST).

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
2.  **The Bouncer (Triage)**: A deterministic node filters "junk" files (like lock files) and enforces a strict **1,500-line logic limit** per PR to protect token budgets and maintain high review quality.
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

> [!IMPORTANT]
> **Use a Separate Bot Account**: For the best experience, we strongly recommend creating a dedicated GitHub account (e.g., `my-swarm-bot`) to act as the reviewer. 
> 1. Create a new GitHub account.
> 2. Add this account as a **Collaborator** on your target repository (`Settings > Collaborators > Add people`).
> 3. Generate a **Classic PAT** from the **Bot account**.

*   **Classic PAT (Recommended)**: Go to `Settings > Developer settings > Tokens (classic)`. Ensure the **`repo`** scope is selected. This is required for bot accounts on personal repositories.
*   **Fine-grained PAT**: Only recommended if your repository is part of an **Organization**. grant access to:
    *   `Pull Requests` (Read & Write)
    *   `Issues` (Read & Write)
    *   `Contents` (Read-only)

#### ⚓ Webhook Setup
Configure your GitHub repository Webhook (`Settings > Webhooks > Add webhook`) as follows:
*   **Payload URL**: `http://[your-domain]/webhook` (Use **ngrok** for local development).
*   **Content type**: `application/json`.
*   **Secret**: Must match your `GITHUB_WEBHOOK_SECRET` in `.env`.
*   **Events**: Select **"Let me select individual events"** and check:
    *   ✅ **Pull requests** (Actions: `opened`, `reopened`, `synchronize`)
    *   ✅ **Issue comments** (For PR-level thread chat)
    *   ✅ **Pull request review comments** (For localized code chat)

### 2. Environment Setup & API Keys

Get your API keys from these official providers:
*   🔑 **GitHub PAT**: [GitHub Settings > Developer Settings](https://github.com/settings/tokens) (Recommended: **Classic Token** with `repo` scope).
*   🤖 **NVIDIA API (Llama 3.1 405B)**: [NVIDIA API Catalog](https://build.nvidia.com/) (Search for `meta/llama-3.1-405b-instruct`).
*   🧠 **OpenAI API (GPT-4o)**: [OpenAI Platform](https://platform.openai.com/api-keys).

#### Option A: Docker Compose (Production-Ready 🚀)
The easiest way is to use the provided `docker-compose.yml`. Update the environment variables directly:
```yaml
services:
  swarm-bot:
    environment:
      - GITHUB_TOKEN=ghp_...
      - GITHUB_WEBHOOK_SECRET=your_secret
      - LLM_PROVIDER=NVIDIA # Or OPENAI
      - NVIDIA_API_KEY=nvapi-...
```
Then run:
```bash
docker-compose up -d
```

#### Option B: Local Development
Create a `.env` file in the `src/` directory:
```env
GITHUB_TOKEN=your_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_shared_secret
LLM_PROVIDER=NVIDIA # Options: OPENAI, NVIDIA
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=nvapi-...
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

## 🚀 Getting Started (Your First Review)

Once your bot is running, follow these steps to trigger a review:

1.  **Create a Branch**: 
    ```bash
    git checkout -b feature/cool-new-code
    ```
2.  **Commit & Push**: Make some changes and push to GitHub.
    ```bash
    git add .
    git commit -m "add experimental feature"
    git push origin feature/cool-new-code
    ```
3.  **Open a Pull Request**: On GitHub, open a PR from your new branch to `main`.
4.  **The Swarm Arrives**: Within seconds, the swarm will analyze your code and post a formal **PR Review**.

---

## 💬 Conversational Feedback — The `@swarm` Feature

If you disagree with the bot or need more explanation on a specific suggestion:

*   **Reply to a Comment**: Mention **`@swarm`** in any PR comment thread.
*   **The Robot's Response**: The bot will immediately activate in its **Conversational Mode**, analyze the context of your specific question, and reply to you directly.
*   **Speed**: Conversational replies are optimized for speed and usually respond in **under 10 seconds.**

---

## 🛡️ Enforcing AI Reviews (Branch Protection)

To make the AI Swarm a mandatory "gatekeeper" for your project, you should configure **Branch Protection Rules** (Settings > Code and automation > Branches) for your default branch (e.g., `main`):

*   ✅ **Require a pull request before merging**: Forces everyone to use the PR flow.
*   ✅ **Require approvals**: Set "Required number of approvals before merging" to **1** (or more).
*   ✅ **Dismiss stale pull request approvals when new commits are pushed**: **VITAL**. Forces the swarm to re-review every time new code is pushed.
*   ✅ **Block force pushes**: Protects the PR record and history integrity.

---

> [!CAUTION]
> **Self-Review Limitation**: GitHub does not allow users to **Approve** or **Request Changes** on their own Pull Requests. 
> - If the `GITHUB_TOKEN` belongs to the **same user** who created the PR, the swarm will automatically post its findings as a **Standard PR Comment** (instead of a Review) to avoid a GitHub API error. 
> - To see "Green" approvals or "Red" blocks, use a separate bot account as a collaborator.


> [!TIP]
> **Why LangGraph?** We use LangGraph over simpler agent chains to manage cycles, complex states, and parallel "Swarm" behaviors reliably.