from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import configure_logging
from app.core.redis import init_redis, _redis_client
from app.api.v1 import transaction as transactions_router
from app.db.db import engine, Base
from app.core.queue import get_channel


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    if settings.REDIS_URL:
        init_redis(settings.REDIS_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await get_channel()

    try:
        yield
    finally:

        try:
            if _redis_client:
                await _redis_client.close()
        except Exception:
            pass


app = FastAPI(title="Transactions Service", lifespan=lifespan)


app.include_router(transactions_router.router)
