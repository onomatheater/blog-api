# app/dependencies.py

"""
Зависимости для использования в endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models import User
from app.utils.database import get_db
from app.utils.security import decode_token
from typing import Optional

security = HTTPBearer(auto_error=False)

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """
    Получаем текущего авторизованного пользователя

    Извлекаем Bearer токен из заголовка Authorization, декодируем токен,
    из токена берем user_id, ищем пользователя в БД и возвращаем объект User
    """
    # Извлекаем токен
    token = credentials.credentials

    # Декодируем
    payload = decode_token(token)

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Если токен невалиден или истек
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ищем пользователя в БД
    user = db.query(User).filter(User.id == int(user_id)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Необязательный текущий пользователь.

    Если токена нет или он невалиден - возвращаем None,
    иначе - объект User.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user