from fastapi import APIRouter
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jose.utils import base64url_encode
import json

router = APIRouter()


# Load public key from PEM
def load_public_key(path: str):
    with open(path, "rb") as f:
        key = serialization.load_pem_public_key(f.read(), backend=default_backend())
    return key


def public_key_to_jwk(key, kid="auth-key-1"):
    numbers = key.public_numbers()
    e = base64url_encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big"))
    n = base64url_encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big"))

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": n.decode(),
        "e": e.decode(),
    }
    return jwk


@router.get("/.well-known/jwks.json")
async def jwks():
    public_key = load_public_key("/app/keys/jwt-public.pem")
    jwk = public_key_to_jwk(public_key, kid="auth-key-1")
    return {"keys": [jwk]}
