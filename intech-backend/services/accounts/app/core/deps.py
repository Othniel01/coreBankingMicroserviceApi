from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user


async def require_superuser(
    user=Depends(get_current_user),
):
    if not user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return user
