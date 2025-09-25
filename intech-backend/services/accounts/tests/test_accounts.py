import pytest
from app.core import auth

pytestmark = pytest.mark.asyncio


async def override_get_current_user_admin():
    return {"sub": "admin-user", "role": "admin"}


async def override_get_current_user_user():
    return {"sub": "normal-user", "role": "user"}


async def test_create_account(client, async_app):
    async_app.dependency_overrides[auth.get_current_user] = (
        override_get_current_user_user
    )

    payload = {"owner_user_id": "normal-user", "currency": "NGN"}
    resp = await client.post("/accounts", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["currency"] == "NGN"
    assert float(data["balance"]) == 0.0
    assert data["owner_user_id"] == "normal-user"


async def test_get_account_forbidden(client, async_app):
    async_app.dependency_overrides[auth.get_current_user] = (
        override_get_current_user_user
    )

    payload = {"owner_user_id": "normal-user", "currency": "NGN"}
    resp = await client.post("/accounts", json=payload)
    acc = resp.json()

    async def another_user():
        return {"sub": "hacker", "role": "user"}

    async_app.dependency_overrides[auth.get_current_user] = another_user

    r = await client.get(f"/accounts/{acc['external_id']}")
    assert r.status_code == 403


async def test_admin_can_list_all(client, async_app):
    async_app.dependency_overrides[auth.get_current_user] = (
        override_get_current_user_admin
    )

    resp = await client.get("/accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
