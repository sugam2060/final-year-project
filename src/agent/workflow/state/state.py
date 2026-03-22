from typing import TypedDict
from langchain_core.messages import BaseMessage

class SwarmState(TypedDict):
    pr_number: int
    repo_name: str
    code_diff: str
    architect_review: str
    security_review: str
    optimizer_review: str
    final_comment: str
