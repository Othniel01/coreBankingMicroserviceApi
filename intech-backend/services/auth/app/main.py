# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.redis import init_redis, _redis_client
from app.core.logger import configure_logging
from app.api.v1 import auth as auth_router
from app.api.v1 import jwks as jwks


@asynccontextmanager
async def lifespan(app: FastAPI):

    configure_logging()

    if settings.REDIS_URL:
        init_redis(settings.REDIS_URL)

    app.include_router(auth_router.router)
    app.include_router(jwks.router, prefix="/auth", tags=["jwks"])

    yield

    try:
        if _redis_client:
            await _redis_client.close()
    except Exception:
        pass


app = FastAPI(title="Auth service", lifespan=lifespan)
