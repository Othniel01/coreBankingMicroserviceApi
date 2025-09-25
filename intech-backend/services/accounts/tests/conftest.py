import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["AUTH_JWKS_URL"] = "http://testserver/.well-known/jwks.json"

from app.main import app
from app.core.db import Base, get_db
from app.core import auth


async def override_get_current_user_user():
    return {"sub": "normal-user", "role": "user"}


async def override_get_current_user_admin():
    return {"sub": "admin-user", "role": "admin"}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine):
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_app(async_session):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    app.dependency_overrides[auth.get_current_user] = override_get_current_user_user

    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(async_app):
    transport = ASGITransport(app=async_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
def as_admin(async_app):
    app.dependency_overrides[auth.get_current_user] = override_get_current_user_admin
    yield
    app.dependency_overrides[auth.get_current_user] = override_get_current_user_user
