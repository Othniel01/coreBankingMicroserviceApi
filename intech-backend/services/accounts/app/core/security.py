import uuid
import time
import requests
from typing import Dict
from jose import jwt
from jose.utils import base64_to_long
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.accounts import Account
from app.core.config import settings

_jwks_cache: Dict = {}
_last_fetch = 0
_cache_ttl = 300  # 5 minutes
BANK_CODE = "627"

security = HTTPBearer()


def get_jwks():
    global _jwks_cache, _last_fetch
    now = time.time()
    if not _jwks_cache or (now - _last_fetch > _cache_ttl):
        resp = requests.get(settings.AUTH_JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = {key["kid"]: key for key in resp.json()["keys"]}
        _last_fetch = now
    return _jwks_cache


def jwk_to_pem(jwk: dict) -> str:
    n = base64_to_long(jwk["n"])
    e = base64_to_long(jwk["e"])
    public_key = rsa.RSAPublicNumbers(e, n).public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def verify_jwt(token: str) -> Dict:
    try:
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        keys = get_jwks()
        if kid not in keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token key id",
            )
        jwk = keys[kid]
        pem_key = jwk_to_pem(jwk)
        return jwt.decode(
            token,
            pem_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


def hash_pin(pin: str) -> str:
    return bcrypt.hash(pin)


def verify_pin(pin: str, hashed: str) -> bool:
    return bcrypt.verify(pin, hashed)


def generate_account_number() -> str:
    random_digits = str(uuid.uuid4().int)[:7]
    account_number = f"{BANK_CODE}{random_digits}"
    return account_number


async def get_account_by_number(
    db: AsyncSession, account_number: str
) -> Account | None:
    q = await db.execute(
        select(Account).where(Account.account_number == account_number)
    )
    return q.scalars().first()
