from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Tuple
from .auth import decode_token

# Expose a standards-compliant OAuth2 Password flow token endpoint at /token/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token/")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Tuple[int, str]:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return int(payload["sub"]), payload["role"]


def require_role(required: str):
    def _dep(user=Depends(get_current_user)):
        _user_id, role = user
        if role != required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep
