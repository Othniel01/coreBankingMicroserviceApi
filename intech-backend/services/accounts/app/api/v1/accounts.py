# app/api/v1/accounts.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid

from app.schemas.account import AccountCreate, AccountOut, AccountUpdate, BalanceOut
from app.models.accounts import Account
from app.core.db import get_db
from app.core.auth import get_current_user
from app.core.rate_limiter import rate_limit_dependency
from app.core.events import publish_event

router = APIRouter(prefix="/accounts", tags=["accounts"])


def rate_limit_dep(request: Request, limit: int = 20, period: int = 60):
    return rate_limit_dependency(request, limit, period)


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    external_id = payload.external_id or str(uuid.uuid4())
    account = Account(
        external_id=external_id,
        owner_user_id=payload.owner_user_id,
        currency=payload.currency,
        balance=Decimal(0),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    await publish_event(
        "account.created",
        {
            "external_id": account.external_id,
            "owner_user_id": account.owner_user_id,
            "currency": account.currency,
        },
    )

    return account


@router.get("", response_model=List[AccountOut])
async def list_accounts(
    owner_user_id: Optional[str] = None,
    currency: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _rl=Depends(rate_limit_dep),
):
    query = select(Account)

    # Non-admin can only list their own accounts
    if user.get("role") != "admin":
        query = query.where(Account.owner_user_id == user.get("sub"))
    elif owner_user_id:
        query = query.where(Account.owner_user_id == owner_user_id)

    if currency:
        query = query.where(Account.currency == currency)
    if is_active is not None:
        query = query.where(Account.is_active == is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{external_id}", response_model=AccountOut)
async def get_account(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _rl=Depends(rate_limit_dep),
):
    q = await db.execute(select(Account).where(Account.external_id == external_id))
    account = q.scalars().first()
    if not account:
        raise HTTPException(404, "Account not found")

    if user.get("sub") != account.owner_user_id and user.get("role") != "admin":
        raise HTTPException(403, "Forbidden")
    return account


@router.get("/{external_id}/balance", response_model=BalanceOut)
async def get_balance(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    _rl=Depends(rate_limit_dep),
):
    q = await db.execute(select(Account).where(Account.external_id == external_id))
    account = q.scalars().first()
    if not account:
        raise HTTPException(404, "Account not found")
    if user.get("sub") != account.owner_user_id and user.get("role") != "admin":
        raise HTTPException(403, "Forbidden")
    return BalanceOut(
        external_id=account.external_id,
        balance=account.balance,
        currency=account.currency,
    )


@router.patch("/{external_id}/status", response_model=AccountOut)
async def patch_status(
    external_id: str,
    is_frozen: bool,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = await db.execute(select(Account).where(Account.external_id == external_id))
    account = q.scalars().first()
    if not account:
        raise HTTPException(404, "Account not found")

    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden")
    account.is_frozen = is_frozen
    await db.commit()
    await db.refresh(account)

    await publish_event(
        "account.status_changed",
        {"external_id": account.external_id, "is_frozen": account.is_frozen},
    )
    return account


@router.patch("/{external_id}", response_model=AccountOut)
async def update_account(
    external_id: str,
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = await db.execute(select(Account).where(Account.external_id == external_id))
    account = q.scalars().first()
    if not account:
        raise HTTPException(404, "Account not found")

    if user.get("role") != "admin" and user.get("sub") != account.owner_user_id:
        raise HTTPException(403, "Forbidden")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    await publish_event(
        "account.updated",
        {"external_id": account.external_id, **payload.dict(exclude_unset=True)},
    )
    return account


@router.patch("/{external_id}/active", response_model=AccountOut)
async def set_account_active_status(
    external_id: str,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden")

    q = await db.execute(select(Account).where(Account.external_id == external_id))
    account = q.scalars().first()
    if not account:
        raise HTTPException(404, "Account not found")

    account.is_active = is_active
    await db.commit()
    await db.refresh(account)

    await publish_event(
        "account.active_status_changed",
        {"external_id": account.external_id, "is_active": is_active},
    )
    return account
