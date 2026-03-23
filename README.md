# 🐝 LangGraph PR Swarm: Multi-Agent GitHub Code Reviewer

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Framework](https://img.shields.io/badge/framework-FastAPI-green)
![Orchestration](https://img.shields.io/badge/orchestration-LangGraph-orange)
![Security](https://img.shields.io/badge/security-HMAC--SHA256-red)

A sophisticated, multi-agent AI system designed to automate and enhance GitHub Pull Request reviews. Built on top of **LangGraph**, **FastAPI**, and the **Model Context Protocol (MCP)**, this system orchestrates a "swarm" of specialized AI agents to analyze code changes and provide expert feedback directly on GitHub.

---

## 🚀 Key Features

*   **Multi-Agent Swarm Orchestration**: Leverages parallel execution of specialized agents (Architect, Security, Optimizer) controlled by a central Lead Engineer (Synthesizer).
*   **Precision Line-by-Line Suggestions**: Implements a custom "Precision Trick" diff-parser that prevents LLM hallucinations by annotating incoming diffs with real line numbers.
*   **Automated GitHub Integration**: Responds to real-time GitHub Webhooks and publishes findings directly as formatted PR Reviews and inline code comments.
*   **Dynamic Specialist Feedback**: 
    *   **🏗️ Architect Agent**: Validates structural design and adherence to patterns.
    *   **🛡️ Security Agent**: Scans for vulnerabilities, credential leaks, and insecure code.
    *   **⚡ Optimizer Agent**: Identifies performance bottlenecks and modern code efficiencies.
*   **Secure & Robust**: Features HMAC-SHA256 signature verification for zero-trust webhook handling and structured Pydantic data models for guaranteed JSON predictability.

---

## 🏗️ Project Structure

The project follows a hyper-modular architecture designed for scalability and clear separation of concerns:

```text
├── skills/                     # Domain knowledge & design constraints for the swarm
├── src/
│   ├── main.py                 # FastAPI Application entry point
│   ├── config.py               # Environment & Global settings
│   ├── router/                 # Webhook Handling
│   │   ├── webhook.py          # Receives GitHub events & triggers Swarm
│   │   └── types/              # Pydantic models for webhook payloads
│   └── agent/                  # Core AI Orchestration
│       ├── swarm.py            # Entrypoint for LangGraph execution
│       └── workflow/           # Internal Graph Components
│           ├── graph/          # LangGraph Topology (Edges & Nodes wiring)
│           ├── nodes/          # Agent Logic (Architect, Security, etc.)
│           ├── state/          # Shared memory (TypedDict SwarmState)
│           ├── tools/          # External actions (GitHub PR Publisher)
│           └── utils/          # Precision Diff Parser & Helper functions
└── requirements.txt            # System dependencies
```

---

## 🔄 Core Workflow

1.  **Incoming Trigger**: A GitHub Webhook (`pull_request`) is received by the FastAPI server.
2.  **Security Check**: The HMAC-SHA256 signature is verified using the system's `GITHUB_WEBHOOK_SECRET`.
3.  **Context Assembly**: The system fetches the PR diff and applies **Precision Annotation**, marking each line with its destination line number to ensure the LLM never hallucinates line references.
4.  **Swarm Orchestration**:
    *   The **Architect**, **Security**, and **Optimizer** agents analyze the diff in parallel.
    *   Findings are passed to the **Synthesizer Node**.
5.  **Output Generation**: The Synthesizer produces a structured `SynthesizerOutput` containing a high-level summary and specific `InlineSuggestion` objects.
6.  **Publication**: The `publisher.py` tool bundles these findings into a unified GitHub Review and posts it to the PR.

---

## 🛠️ Configuration & Setup

### 1. Requirements
Ensure you have Python 3.10+ and the required libraries installed:
```bash
pip install -r src/requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the `src/` directory with the following keys:
```env
GITHUB_TOKEN=your_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_shared_secret
OPENAI_API_KEY=your_openai_key
```

### 3. Running the Server
Start the FastAPI server (running on `localhost:8000` by default):
```bash
python src/main.py
```

### 4. GitHub Hook Setup
Configure your GitHub repository to send `Pull Request` events to:
`http://[your-domain]/webhook` (Note: Use tools like **ngrok** for local testing).

---

## 📚 Expert Skills & Constraints

The system is guided by a set of "Skills" found in the `skills/` directory. These define how the agents should behave, including:
- **`langgraph_swarm.md`**: The blueprint for architecting multi-agent systems.
- **`design_constraints.md`**: Rules for UI/UX and API design.
- **`structure.md`**: Folder hierarchy and modularity standards.

---

> [!TIP]
> **Why LangGraph?** We use LangGraph over simpler agent chains to manage cycles, complex states, and parallel "Swarm" behaviors reliably.