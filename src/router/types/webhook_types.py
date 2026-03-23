from pydantic import BaseModel

class Repository(BaseModel):
    full_name: str

class Head(BaseModel):
    sha: str

class PullRequest(BaseModel):
    number: int
    head: Head

class PullRequestEvent(BaseModel):
    action: str
    repository: Repository
    pull_request: PullRequest
