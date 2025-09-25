# from fastapi import FastAPI
# from contextlib import asynccontextmanager
# from app.core.config import settings
# from app.core.logger import configure_logging
# from app.core.redis import init_redis, _redis_client
# from app.api.v1 import accounts as accounts_router
# from app.core.db import engine, Base


# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     configure_logging()

#     if settings.REDIS_URL:
#         init_redis(settings.REDIS_URL)

#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     # attach routers
#     app.include_router(accounts_router.router)

#     try:
#         yield
#     finally:

#         try:
#             if _redis_client:
#                 await _redis_client.close()
#         except Exception:
#             pass


# app = FastAPI(title="Accounts service", lifespan=lifespan)


from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import configure_logging
from app.core.redis import init_redis, _redis_client
from app.api.v1 import accounts as accounts_router
from app.core.db import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    if settings.REDIS_URL:
        init_redis(settings.REDIS_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        try:
            if _redis_client:
                await _redis_client.close()
        except Exception:
            pass


app = FastAPI(title="Accounts service", lifespan=lifespan)


app.include_router(accounts_router.router)
