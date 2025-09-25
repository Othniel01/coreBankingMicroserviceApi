# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    ENV: str = Field("development")
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str | None = None

    JWT_PRIVATE_KEY_PATH: str | None = None
    JWT_PUBLIC_KEY_PATH: str | None = None

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Argon2 tuning (tune for your environment)
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 102400
    ARGON2_PARALLELISM: int = 8

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
