from fastapi import Request, HTTPException
from datetime import datetime, timezone
from app.core.redis import get_redis
import logging

logger = logging.getLogger(__name__)


def sanitize_path(path: str) -> str:
    return path.replace("/", ":")


async def rate_limit_dependency(
    request: Request, user_id: str | None = None, limit: int = 60, period: int = 60
):
    client = get_redis()
    ts = int(datetime.now(timezone.utc).timestamp())
    window = ts - (ts % period)
    path = sanitize_path(request.url.path)
    uid = (
        user_id
        or (
            request.state.user.get("sub")
            if getattr(request.state, "user", None)
            else None
        )
        or request.client.host
        or "anon"
    )
    key = f"ratelimit:{uid}:{path}:{window}"
    try:
        val = await client.incr(key)
        if val == 1:
            await client.expire(key, period)
        if val > limit:
            raise HTTPException(status_code=429, detail="Too many requests")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Rate limit check failed (redis): %s", e)
