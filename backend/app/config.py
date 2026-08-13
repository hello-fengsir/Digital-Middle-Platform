from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hpl:hpl@db:5432/hpl"
    api_key: str = "change-me"
    cors_origins: str = "*"
    admin_session_ttl_seconds: int = 28800
    admin_session_secret: str = ""
    admin_password_hash: str = ""
    admin_username: str = "admin"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_max_concurrency: int = 4
    ai_total_timeout_seconds: float = 75.0
    # Deployment contract: this points only at the fixed bind-mounted rule file.
    ai_selection_agent_rule_path: str = "/app/runtime-prompts/AI_SELECTION_AGENT.md"


settings = Settings()
