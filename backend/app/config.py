import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Policy Data Analytics Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Multi-Cloud LLM Provider Keys & Configs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")

    # LLM Router Strategy
    # Priority list for fallback: if primary fails (e.g. rate limit, auth, network), falls back sequentially
    LLM_PROVIDER_PRIORITY: list[str] = ["openai", "gemini", "bedrock", "local_fallback"]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend_data.db")

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Storage & Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_RAW_DIR: str = os.path.join(BASE_DIR, "data", "raw")
    POLICY_DOCS_DIR: str = os.path.join(BASE_DIR, "data", "policy_docs")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings()
