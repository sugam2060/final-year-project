from pydantic import BaseModel, ConfigDict


# --- Shared Models ---

class Repository(BaseModel):
    model_config = ConfigDict(extra="allow")
    full_name: str


# --- Pull Request Event Models ---

class Head(BaseModel):
    model_config = ConfigDict(extra="allow")
    sha: str

class PullRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    number: int
    head: Head

class PullRequestEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str
    repository: Repository
    pull_request: PullRequest


# --- Issue Comment Event Models (Conversational Reviews) ---

class CommentUser(BaseModel):
    model_config = ConfigDict(extra="allow")
    login: str

class Comment(BaseModel):
    model_config = ConfigDict(extra="allow")
    body: str
    user: CommentUser

class Issue(BaseModel):
    model_config = ConfigDict(extra="allow")
    number: int

class IssueCommentEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str
    repository: Repository
    issue: Issue
    comment: Comment


# --- PR Review Comment Event Models (Replies to inline suggestions) ---

class PullRequestReviewCommentEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str
    repository: Repository
    pull_request: PullRequest
    comment: Comment
