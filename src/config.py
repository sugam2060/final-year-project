from starlette.config import Config
from starlette.datastructures import Secret

import os

# Load configurations from .env
config = Config(".env")

GITHUB_WEBHOOK_SECRET = config("GITHUB_WEBHOOK_SECRET", cast=Secret)
GITHUB_TOKEN = config("GITHUB_TOKEN", cast=Secret)
OPENAI_API_KEY = config("OPENAI_API_KEY", cast=Secret, default="your_openai_key_here")
NVIDIA_API_KEY = config("NVIDIA_API_KEY", cast=Secret, default="")
LLM_PROVIDER = config("LLM_PROVIDER", default="OPENAI")
DATABASE_URL = config("DATABASE_URL", default="postgresql://postgres:postgres@localhost:5432/postgres")

# LangSmith Configurations (Auto-traced by LangChain if LANGSMITH_TRACING is "true")
LANGSMITH_TRACING = config("LANGSMITH_TRACING", default="false")
LANGSMITH_API_KEY = config("LANGSMITH_API_KEY", cast=Secret, default="")
LANGSMITH_PROJECT = config("LANGSMITH_PROJECT", default="code-reviewer")
LANGSMITH_ENDPOINT = config("LANGSMITH_ENDPOINT", default="https://api.smith.langchain.com")

class Settings:
    GITHUB_WEBHOOK_SECRET: Secret = GITHUB_WEBHOOK_SECRET
    GITHUB_TOKEN: Secret = GITHUB_TOKEN
    OPENAI_API_KEY: Secret = OPENAI_API_KEY
    NVIDIA_API_KEY: Secret = NVIDIA_API_KEY
    LLM_PROVIDER: str = LLM_PROVIDER.strip().upper()
    DATABASE_URL: str = DATABASE_URL
    
    # Llangsmith
    # langgraph-checkpoint-postgres
    # asyncpg
    LANGSMITH_TRACING: str = LANGSMITH_TRACING
    LANGSMITH_API_KEY: Secret = LANGSMITH_API_KEY
    LANGSMITH_PROJECT: str = LANGSMITH_PROJECT
    LANGSMITH_ENDPOINT: str = LANGSMITH_ENDPOINT

settings = Settings()

# CRITICAL: Export Langsmith to environment for automatic LangChain tracing
if settings.LANGSMITH_TRACING == "true":
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = str(settings.LANGSMITH_API_KEY)
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
