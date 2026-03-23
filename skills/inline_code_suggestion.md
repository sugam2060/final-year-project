# Role & Objective
You are an expert AI Engineer and Python Backend Developer. Your objective is to upgrade the existing LangGraph multi-agent swarm to generate actionable, inline code suggestions using GitHub's ````suggestion```` markdown feature, and post them directly to the specific lines of code in the Pull Request.

# Execution Steps

1. **Define the Structured Output Schema (`src/agent/types/inline_comments.py`):**
   - Create a Pydantic model to force the LLM to output a strict JSON structure for the final review.
   - Code requirement:
     ```python
     from pydantic import BaseModel, Field
     from typing import List

     class InlineSuggestion(BaseModel):
         file_path: str = Field(description="The exact relative path to the file in the repository.")
         line_number: int = Field(description="The exact line number in the modified file where the issue occurs.")
         suggestion_body: str = Field(description="The comment body. MUST include the corrected code wrapped in standard GitHub ```suggestion\\n [code] \\n``` markdown block.")

     class SynthesizerOutput(BaseModel):
         general_summary: str = Field(description="The overall prioritized markdown summary of the Blockers and Suggestions.")
         inline_suggestions: List[InlineSuggestion] = Field(description="A list of specific line-by-line code fixes.")
     ```

2. **Update the Swarm State (`src/agent/workflow/state/state.py`):**
   - Add `commit_sha` and `inline_suggestions` to the state.
   - Code requirement:
     ```python
     from typing import TypedDict, List
     from src.agent.types.inline_comments import InlineSuggestion

     class SwarmState(TypedDict):
         pr_number: int
         repo_name: str
         commit_sha: str  # REQUIRED: To anchor inline comments
         code_diff: str
         architect_review: str
         security_review: str
         optimizer_review: str
         final_comment: str
         inline_suggestions: List[InlineSuggestion]
     ```

3. **Update the Webhook Router (`src/router/webhook.py`):**
   - Update the Pydantic models in `webhook_types.py` to extract the latest commit SHA from the PR event payload (`pull_request.head.sha`).
   - Pass this `commit_sha` into the `run_swarm()` function alongside `repo_name`, `pr_number`, and `code_diff`.

4. **Upgrade the Synthesizer Node (`src/agent/workflow/nodes/nodes.py`):**
   - Update the `synthesizer_node` to use `.with_structured_output(SynthesizerOutput)` when invoking the LLM.
   - **Crucial Prompt Update:** Instruct the Lead Engineer agent to extract specific, actionable code fixes from the specialists' reviews and format them strictly as GitHub suggestions.
   - Update the state dictionary return: 
     `return {"final_comment": result.general_summary, "inline_suggestions": result.inline_suggestions}`

5. **Upgrade the Publisher (`src/agent/workflow/tools/publisher.py`):**
   - Update the `publish_pr_comment` function (or create a new `publish_inline_review` function).
   - Use `PyGithub` to create a bundled PR review that includes both the body and the line-specific comments.
   - Code logic requirement (run inside `asyncio.to_thread`):
     ```python
     # Inside your authenticated PyGithub logic:
     pr = repo.get_pull(pr_number)
     commit = repo.get_commit(commit_sha)
     
     # Format comments for the PyGithub API
     github_comments = []
     for suggestion in inline_suggestions:
         github_comments.append({
             "path": suggestion.file_path,
             "line": suggestion.line_number,
             "body": suggestion.suggestion_body
         })
     
     # Create the bundled review
     pr.create_review(
         commit=commit,
         body=general_summary,
         event="COMMENT",
         comments=github_comments
     )
     ```

6. **Update the Entrypoint (`src/agent/swarm.py`):**
   - Ensure `run_swarm` accepts the new `commit_sha` argument and initializes the state with it.
   - Pass both the `final_comment` and `inline_suggestions` to your updated publisher.

*Note: Adhere strictly to the DRY principle and asynchronous performance constraints established in `design_constraints.md`.*