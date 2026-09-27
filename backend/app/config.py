from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import dotenv

dotenv.load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = os.getenv("OPENROUTER_MODEL")

    # App metadata
    app_title: str = "Cover Letter Generator"
    app_url: str = os.getenv("APP_URL", "http://localhost:5173")

    # Postgres (set by docker-compose; this default lets local non-docker runs work too)
    database_url: str = (
        f'postgresql+asyncpg://{os.getenv("LETTER_POSTGRES_USER")}:{os.getenv("LETTER_POSTGRES_PASSWORD")}@db:5432/{os.getenv("LETTER_POSTGRES_DB")}'
    )

    # Path inside the container to the mounted CV
    cv_path: str = "/app/data/" + os.getenv("WORK_EXPERIENCE_JSONFILE")

settings = Settings()
