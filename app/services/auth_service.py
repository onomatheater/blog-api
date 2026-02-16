# app/services/auth_service.py

"""
Сервисный слой для регистрации и логина.

Знает про модели, БД, хэширование и JWT, но не про HTTP-исключения.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate, UserLogin
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.auth_tokens import store_refresh_token


async def register_user_in_db(
    db: Session,
    user_in: UserCreate,
) -> Optional[dict]:
    """
    Зарегистрировать нового пользователя.

    Возвращает словарь с токенами или None, если email/username заняты
    или произошла внутренняя ошибка с токенами.
    """
    # Проверка уникальности email
    if db.query(User).filter(User.email == user_in.email).first():
        return None

    # Проверка уникальности username
    if db.query(User).filter(User.username == user_in.username).first():
        return None

    # Хэшируем пароль и создаём пользователя
    hashed_password = hash_password(user_in.password)
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Генерация access/refresh токенов
    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(db_user.id)})

    # Извлекаем jti из refresh-токена и сохраняем в Redis
    payload = decode_token(refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        return None

    jti = payload.get("jti")
    await store_refresh_token(jti, db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def authenticate_user(
    db: Session,
    creds: UserLogin,
) -> Optional[dict]:
    """
    Аутентифицировать пользователя по email и паролю.

    Возвращает словарь с токенами или None, если данные неверны
    или произошла ошибка генерации/сохранения refresh-токена.
    """
    db_user = db.query(User).filter(User.email == creds.email).first()
    if not db_user:
        return None

    if not verify_password(creds.password, db_user.hashed_password):
        return None

    # Генерация access/refresh токенов
    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(db_user.id)})

    payload = decode_token(refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        return None

    jti = payload.get("jti")
    await store_refresh_token(jti, db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
