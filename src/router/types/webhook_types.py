from pydantic import BaseModel

class Repository(BaseModel):
    full_name: str

class PullRequest(BaseModel):
    number: int

class PullRequestEvent(BaseModel):
    action: str
    repository: Repository
    pull_request: PullRequest
