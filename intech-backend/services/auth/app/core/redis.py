# app/core/redis_client.py
from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

_redis_client: Optional[Redis] = None


def init_redis(url: str | None) -> None:
    global _redis_client
    if _redis_client is None and url:
        pool = ConnectionPool.from_url(url, decode_responses=False)
        _redis_client = Redis(connection_pool=pool)


def get_redis() -> Redis:
    if _redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. Call init_redis() on startup."
        )
    return _redis_client
