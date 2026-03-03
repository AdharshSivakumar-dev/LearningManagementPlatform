from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .auth import decode_token
from lms.models import LMSUser

# Expose a standards-compliant OAuth2 Password flow token endpoint at /token/
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token/")


def get_current_user(token: str = Depends(oauth2_scheme)) -> LMSUser:
    # Support "Bearer <token>" format
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    try:
        user = LMSUser.objects.get(pk=int(payload["sub"]))
        return user
    except LMSUser.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")


def require_role(required: str):
    def _dep(user: LMSUser = Depends(get_current_user)):
        if user.role != required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep
