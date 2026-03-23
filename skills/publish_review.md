# Role & Objective
You are an expert Python Backend Engineer. The multi-agent LangGraph swarm is currently executing successfully and generating a synthesized code review. Your objective is to take that final output and automatically publish it as a comment on the corresponding GitHub Pull Request.

# Execution Steps

1. **Create the GitHub Publisher Utility (`src/agent/workflow/tools/publisher.py`):**
   - Create a new file to handle outward-bound GitHub API calls.
   - Import the `Github` client from `PyGithub` and your `GITHUB_TOKEN` from `src.config`.
   - Write an asynchronous function `publish_pr_comment(repo_name: str, pr_number: int, comment_body: str)`.
   - **Logic:**
     - Run the synchronous `PyGithub` calls inside `asyncio.to_thread()` to prevent blocking.
     - Authenticate the client: `g = Github(settings.GITHUB_TOKEN)`
     - Fetch the repo: `repo = g.get_repo(repo_name)`
     - Fetch the PR: `pr = repo.get_pull(pr_number)`
     - Post the comment: `pr.create_issue_comment(comment_body)`
     - Add robust logging (e.g., `logger.info(f"Successfully posted review to PR #{pr_number}")`).

2. **Update the Entrypoint (`src/agent/swarm.py`):**
   - Import the new `publish_pr_comment` function.
   - Inside the `run_swarm` function, wait for the LangGraph `swarm_app` to finish executing and grab the `final_comment` from the result dictionary.
   - **Crucial Update:** Replace the simple `logger.info(result["final_comment"])` with a call to your new publisher:
     ```python
     final_review = result.get("final_comment")
     if final_review:
         await publish_pr_comment(repo_name, pr_number, final_review)
     else:
         logger.error("Swarm completed but no final_comment was generated.")
     ```

*Note: Adhere strictly to the asynchronous performance rules in `design_constraints.md`.*