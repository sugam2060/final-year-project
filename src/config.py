from starlette.config import Config
from starlette.datastructures import Secret

# Load configurations from .env
config = Config(".env")

GITHUB_WEBHOOK_SECRET = config("GITHUB_WEBHOOK_SECRET", cast=Secret)
GITHUB_TOKEN = config("GITHUB_TOKEN", cast=Secret)
OPENAI_API_KEY = config("OPENAI_API_KEY", cast=Secret, default="your_openai_key_here")

class Settings:
    GITHUB_WEBHOOK_SECRET: Secret = GITHUB_WEBHOOK_SECRET
    GITHUB_TOKEN: Secret = GITHUB_TOKEN
    OPENAI_API_KEY: Secret = OPENAI_API_KEY

settings = Settings()
