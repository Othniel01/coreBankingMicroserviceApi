# app/core/security.py
from passlib.hash import argon2
from app.core.config import settings
from typing import Optional
from jose import jwt, JWTError
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import os
from app.core.redis import get_redis


def hash_password(password: str) -> str:
    return argon2.using(
        rounds=settings.ARGON2_TIME_COST,
        memory_cost=settings.ARGON2_MEMORY_COST,
        parallelism=settings.ARGON2_PARALLELISM,
    ).hash(password)


def verify_password(hash: str, password: str) -> bool:
    try:
        return argon2.verify(password, hash)
    except Exception:
        return False


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_key(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if p.exists():
        return p.read_text()
    return os.getenv(path)


def _get_private_key() -> str:
    key = _load_key(settings.JWT_PRIVATE_KEY_PATH)
    if not key:
        raise RuntimeError("JWT private key not found. Set JWT_PRIVATE_KEY_PATH")
    return key


def _get_public_key() -> str:
    key = _load_key(settings.JWT_PUBLIC_KEY_PATH)
    if not key:
        raise RuntimeError("JWT public key not found. Set JWT_PUBLIC_KEY_PATH")
    return key


def _blacklist_key_for_token(token_type: str, token_hash: str) -> str:

    return f"blacklist:{token_type}:{token_hash}"


async def blacklist_token_in_redis(token: str, token_type: str) -> None:
    """
    Stores the token hash in redis with TTL until token's exp claim.
    token_type should match the token's 'typ' or your scheme ("access"|"refresh").
    """
    r = get_redis()
    try:
        payload = jwt.get_unverified_claims(token)
        exp = payload.get("exp")
        if exp is None:

            return
        ttl = int(exp) - int(datetime.now(timezone.utc).timestamp())
        if ttl <= 0:
            return
        h = hashlib.sha256(token.encode()).hexdigest()
        key = _blacklist_key_for_token(token_type, h)
        await r.set(key, b"1", ex=ttl)
    except Exception as e:
        raise RuntimeError(f"Failed to blacklist token: {e}")


async def is_token_blacklisted(token: str, token_type: str) -> bool:
    r = get_redis()
    h = hashlib.sha256(token.encode()).hexdigest()
    key = _blacklist_key_for_token(token_type, h)
    try:
        exists = await r.exists(key)
        return bool(exists)
    except Exception:
        return False


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    private = _get_private_key()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, private, algorithm="RS256")
    return token


def create_refresh_token(subject: str) -> str:
    private = _get_private_key()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "typ": "refresh",
    }
    token = jwt.encode(payload, private, algorithm="RS256")
    return token


async def verify_token(token: str, expected_type: str | None = None) -> dict:
    """
    Verifies token signature/exp and checks redis blacklist.
    returns payload dict on success, raises JWTError on invalid signature/exp.
    returns None if blacklisted (caller should treat as invalid).
    """
    public = _get_public_key()
    try:
        payload = jwt.decode(token, public, algorithms=["RS256"])
    except JWTError as e:
        raise e

    if expected_type is not None:
        typ = payload.get("typ")
        if typ != expected_type:

            raise JWTError("Invalid token type")

    blacklisted = await is_token_blacklisted(token, payload.get("typ", "access"))
    if blacklisted:
        raise JWTError("Token has been revoked")

    return payload
