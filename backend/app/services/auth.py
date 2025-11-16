# backend/app/services/auth.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..config import settings
from .. import crud, schemas
from ..db import get_connection

security = HTTPBearer()

def verify_password(plain_password: str, password_hash: str) -> bool:
    # reuse the same passlib context as in crud.py
    from . import rag  # hacky import just to avoid circular import; or copy pwd_context from crud
    # Actually better: import from crud directly:
    from ..crud import pwd_context
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def authenticate_user(tenant_id, email, password) -> dict | None:
    conn = get_connection()
    try:
        user = crud.get_user_by_email_and_tenant(conn, tenant_id, email)
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user
    finally:
        conn.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> schemas.UserOut:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        if user_id is None or tenant_id is None or email is None:
            raise credentials_exception
        token_data = schemas.TokenData(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            role=role,
        )
    except JWTError:
        raise credentials_exception

    conn = get_connection()
    try:
        user_row = crud.get_user_by_id(conn, token_data.user_id)
        if not user_row:
            raise credentials_exception
        return schemas.UserOut(
            id=user_row["id"],
            tenant_id=user_row["tenant_id"],
            email=user_row["email"],
            role=user_row["role"],
        )
    finally:
        conn.close()

