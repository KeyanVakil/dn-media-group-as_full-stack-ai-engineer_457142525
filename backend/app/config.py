from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://newslens:newslens@db:5432/newslens"
    anthropic_api_key: str = ""
    analysis_batch_size: int = 5
    analysis_interval_seconds: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
