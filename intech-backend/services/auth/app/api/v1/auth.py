# app/api/v1/auth.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user_schema import RegisterIn, LoginIn, TokenOut, RefreshIn
from app.db.db import get_db
from app.core.rate_limiter import rate_limit_dependency
from app.services.user_service import (
    create_user,
    authenticate,
    create_tokens_and_store,
    revoke_refresh,
    rotate_refresh,
)
from app.core import security
from fastapi import Depends, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def signup_rate_limit_dep():
    async def _dep(request: Request):
        return await rate_limit_dependency(
            request=request,
            user_id=None,
            limit=5,
            period=60,
        )

    return Depends(_dep)


@router.post("/register", response_model=dict, status_code=201)
async def register(
    payload: RegisterIn,
    db: AsyncSession = Depends(get_db),
    _: None = signup_rate_limit_dep(),
):
    try:
        user = await create_user(db, payload.email, payload.password, payload.full_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"user_id": str(user.id), "email": user.email}


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    user = await authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    tokens = await create_tokens_and_store(db, user)
    return TokenOut(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=60 * int(15),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:

        await security.verify_token(payload.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    tokens = await rotate_refresh(db, payload.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return TokenOut(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=60 * int(15),
    )


@router.post("/logout")
async def logout(
    payload: RefreshIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ok = await revoke_refresh(db, payload.refresh_token)

    blacklist_success = True
    try:
        await security.blacklist_token_in_redis(payload.refresh_token, "refresh")

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            await security.blacklist_token_in_redis(access_token, "access")

    except Exception as e:
        logger.error(f"Failed to blacklist tokens: {e}")
        blacklist_success = False

    return {"ok": ok, "blacklist_success": blacklist_success}
