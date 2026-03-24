import os
from github import Github
from config import settings

def check_token_info():
    try:
        g = Github(login_or_token=str(settings.GITHUB_TOKEN), timeout=20)
        user = g.get_user()
        print(f"Token belongs to user: {user.login}")
        
        # Test PR Access for the specific repository
        repo_name = "sugam2060/swarm-testing-repo"
        repo = g.get_repo(repo_name)
        print(f"Repo access: {repo_name} (found)")
        
        # Check permissions for the authenticated user on this repo
        # PyGithub repo.get_collaborator_permission(user.login) requires higher admin access usually.
        # We'll just try to see if 'push' permission is True in repo.permissions
        print(f"Permissions: {repo.permissions}")
        
    except Exception as e:
        print(f"Error checking token: {e}")

if __name__ == "__main__":
    check_token_info()
