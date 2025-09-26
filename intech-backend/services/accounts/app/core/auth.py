from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.jwks import verify_jwt

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = creds.credentials
    try:
        payload = verify_jwt(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "is_superuser": payload.get("is_superuser", False),
    }
