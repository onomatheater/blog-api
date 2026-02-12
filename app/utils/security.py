# app/utils/security.py

"""
Утилиты для безопасности: хэширование пароля и JWT токены
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from app.config import settings

from uuid import uuid4

# Контекст bcrypt алгоритм
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================
# ФУНКЦИЯ ДЛЯ РАБОТЫ С ПАРОЛЯМИ
# =============================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Проверка, что введённый пароль совпадает с хэшем в БД
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# =============================
# ФУНКЦИИ ДЛЯ РАБОТЫ С JWT
# =============================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    # Определяем время истечения токена
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Добавляем в токен время истечения
    to_encode.update({
        "exp": expire,
        "token_type": "access",
    })

    # Кодируем в JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    # Определяем время истечения токена
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    jti = str(uuid4())

    # Добавляем в токен время истечения
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "jti": jti
    })

    # Кодируем в JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt



def decode_token(token: str) -> Optional[dict]:
    """
    Декодируем JWT токен и проверяем подпись
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Токен истек
        return None
    except jwt.InvalidTokenError:
        # Токен подделан
        return None
