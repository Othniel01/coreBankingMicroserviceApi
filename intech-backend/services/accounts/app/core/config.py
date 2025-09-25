# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Environment
    ENV: str = Field("development")

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str | None = None

    # JWT / Auth (accounts verifies tokens, doesn’t issue them)
    AUTH_JWKS_URL: str
    JWT_ALGORITHM: str = Field("RS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_FILE: str = Field("/app/logs/accounts.log")
    LOG_LEVEL: str = Field("info")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
