# app/core/jwks.py
import time
import threading
import requests
from jose import jwt
from jose.backends.cryptography_backend import CryptographyRSAKey
from jose.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any
from app.core.config import settings

_jwks_cache: Dict[str, Any] = {"keys": [], "fetched_at": 0}
_lock = threading.Lock()
CACHE_TTL = 300


def fetch_jwks() -> Dict[str, Any]:
    url = settings.AUTH_JWKS_URL
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def get_jwks(force_refresh: bool = False) -> Dict[str, Any]:
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


def jwk_to_public_key(jwk: Dict[str, Any]):
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
    """
    Verify JWT against JWKS. Returns payload on success, raises jose.JWTError on failure.
    """

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
