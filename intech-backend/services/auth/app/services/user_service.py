# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from datetime import datetime, timedelta, timezone


async def create_user(
    db: AsyncSession, email: str, password: str, full_name: str | None = None
) -> User:
    q = select(User).where(User.email == email)
    res = await db.execute(q)
    if res.scalars().first():
        raise ValueError("User already exists")
    user = User(
        email=email, hashed_password=hash_password(password), full_name=full_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    q = select(User).where(User.email == email)
    res = await db.execute(q)
    user = res.scalars().first()
    if not user:
        return None
    if not verify_password(user.hashed_password, password):
        return None
    return user


async def create_tokens_and_store(db: AsyncSession, user) -> dict:
    access = create_access_token(
        str(user.id), extra_claims={"email": user.email, "role": "user"}
    )
    refresh = create_refresh_token(str(user.id))
    hashed = hash_refresh_token(refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)
    rt = RefreshToken(user_id=user.id, token_hash=hashed, expires_at=expires_at)
    db.add(rt)
    await db.commit()
    return {"access_token": access, "refresh_token": refresh}


async def revoke_refresh(db: AsyncSession, raw_token: str) -> bool:
    hashed = hash_refresh_token(raw_token)
    q = select(RefreshToken).where(RefreshToken.token_hash == hashed)
    res = await db.execute(q)
    rt = res.scalars().first()
    if not rt:
        return False
    rt.revoked = True
    await db.commit()
    return True


async def rotate_refresh(db: AsyncSession, raw_token: str) -> dict | None:

    from app.core.security import verify_token

    try:
        payload = verify_token(raw_token)
    except Exception:
        return None
    if payload.get("typ") != "refresh":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None

    hashed = hash_refresh_token(raw_token)
    q = select(RefreshToken).where(RefreshToken.token_hash == hashed)
    res = await db.execute(q)
    rt = res.scalars().first()
    if not rt or rt.revoked or rt.expires_at < datetime.now(timezone.utc):
        return None

    rt.revoked = True

    q2 = select(User).where(User.id == user_id)
    res2 = await db.execute(q2)
    user = res2.scalars().first()
    if not user:
        return None

    tokens = await create_tokens_and_store(db, user)
    return tokens
