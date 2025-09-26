from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):

    ENV: str = Field("development")

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    REDIS_URL: str | None = None

    AUTH_JWKS_URL: str
    JWT_ALGORITHM: str = Field("RS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str = Field("transactions")
    RABBITMQ_QUEUE_TRANSACTIONS: str = Field("new")
    RABBITMQ_QUEUE_SETTLEMENT: str = Field("settlement")
    RABBITMQ_QUEUE_FRAUD: str = Field("fraud")

    LOG_FILE: str = Field("/app/logs/transactions.log")
    LOG_LEVEL: str = Field("info")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
