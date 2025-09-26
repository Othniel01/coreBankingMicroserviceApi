import time
import threading
import requests
from jose import jwt
from jose.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer

from app.core.config import settings


_jwks_cache: Dict[str, Any] = {"keys": [], "fetched_at": 0}
_lock = threading.Lock()
CACHE_TTL = 300  # 5 minutes


security = HTTPBearer()


def fetch_jwks() -> Dict[str, Any]:
    url = settings.AUTH_JWKS_URL
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def get_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """Thread-safe JWKS fetch and cache"""
    with _lock:
        now = int(time.time())
        if (
            force_refresh
            or (now - _jwks_cache["fetched_at"]) > CACHE_TTL
            or not _jwks_cache["keys"]
        ):
            try:
                jwks = fetch_jwks()
                _jwks_cache["keys"] = jwks.get("keys", [])
                _jwks_cache["fetched_at"] = now
            except Exception:
                pass
    return _jwks_cache


def jwk_to_public_key(jwk: Dict[str, Any]) -> bytes:
    """Convert JWK dict to PEM"""
    n = int.from_bytes(base64url_decode(jwk["n"].encode()), "big")
    e = int.from_bytes(base64url_decode(jwk["e"].encode()), "big")
    pub_numbers = rsa.RSAPublicNumbers(e, n)
    pub_key = pub_numbers.public_key(default_backend())
    pem = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem


def verify_jwt(token: str) -> Dict[str, Any]:
    """Verify JWT against JWKS. Returns payload on success."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg", settings.JWT_ALGORITHM)
    jwks = get_jwks()
    keys = jwks.get("keys", [])
    jwk = None
    if kid:
        for k in keys:
            if k.get("kid") == kid:
                jwk = k
                break
    if jwk is None and keys:
        jwk = keys[0]
    if jwk is None:
        jwks = get_jwks(force_refresh=True)
        keys = jwks.get("keys", [])
        if keys:
            jwk = keys[0]
        else:
            raise jwt.JWTError("No JWKS keys available")
    public_pem = jwk_to_public_key(jwk)
    payload = jwt.decode(token, public_pem, algorithms=[alg])
    return payload


async def get_current_user(creds=Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to get JWT payload"""
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    token = creds.credentials
    try:
        payload = verify_jwt(token)
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
        )

    payload["is_superuser"] = payload.get("is_superuser", False)
    return payload


async def require_superuser(user=Depends(get_current_user)) -> Dict[str, Any]:
    """FastAPI dependency to enforce superuser access"""
    if not user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required"
        )
    return user
