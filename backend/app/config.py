from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = "minimax/minimax-m3"

    # App metadata
    app_title: str = "Cover Letter Generator"
    app_url: str = "http://localhost:5173"

    # Postgres (set by docker-compose; this default lets local non-docker runs work too)
    database_url: str = (
        "postgresql+asyncpg://coverletter:coverletter@db:5432/coverletter"
    )

    # Path inside the container to the mounted CV
    cv_path: str = "/app/data/work_experience.json"


settings = Settings()
