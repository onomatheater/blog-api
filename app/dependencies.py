# app/dependencies.py

"""
Зависимости для использования в endpoints
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from app.models import User
from app.utils.database import get_db
from app.utils.security import decode_token

security = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthCredentials = Depends(security),
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