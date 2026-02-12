# app/routes/auth.py

"""
API endpoints для регистрации и авторизации.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request

from sqlalchemy.orm import Session

from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
    TokenLogoutRequest,
)

from app.models import User
from app.utils.database import get_db

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.auth_tokens import (
    store_refresh_token,
    is_refresh_token_active,
    revoke_refresh_token,
)

from app.utils.limiter import limiter
from app.config import settings

# Router для всех auth-эндпоинтов
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    responses={400: {"description": "Bad Request"}},
)


# ===============================
# РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
# ===============================

# Вспомогательная функция проверки пароля
def validate_password_strength(password: str) -> None:
    """
    Проверяет базовую сложность пароля.

    Условия:
    - длина не меньше 8 символов;
    - минимум одна буква;
    - минимум одна цифра;
    """

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    if not any(ch.isalpha() for ch in password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one letter",
        )

    if not any(ch.isdigit() for ch in password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one digit",
        )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.REGISTER_RATE_LIMIT)
async def register_user(
        user: UserCreate,
        request: Request,
        db: Session = Depends(get_db)
):

    # Проверяем что email не занят
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Проверяем что username не занят
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    # Хэшируем пароль
    hashed_password = hash_password(user.password)

    # Создаем новый объект User в БД
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(db_user.id)})

    payload = decode_token(refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(status_code=500, detail="Invalid refresh token payload")

    jti = payload.get("jti")
    await store_refresh_token(jti, db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ==============================
# Авторизация созданного профиля
# ==============================

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login_user(
        user: UserLogin,
        request: Request,
        db: Session = Depends(get_db)
):
    """Логин пользователя"""

    # Поиск пользователя по email или username
    db_user = db.query(User).filter(User.email == user.email).first()

    # Если пользователь не найден или неверный пароль
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token   = create_refresh_token(data={"sub": str(db_user.id)})

    payload = decode_token(refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(status_code=500, detail="Invalid refresh token payload")

    jti = payload.get("jti")
    await store_refresh_token(jti, db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# ================
# REFRESH ENDPOINT
# ================

@router.post("/refresh", response_model=TokenResponse,
             status_code=status.HTTP_200_OK)
async def refresh_token_endpoint(
        body: TokenRefreshRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    # Проверяем, не отозван ли токен
    if not await is_refresh_token_active(jti):
        raise HTTPException(
            status_code=401,
            detail="Refresh token has been revoked",
        )

    # Проверить, что пользователь еще существует / активен
    db_user = db.query(User).filter(
        User.id == int(user_id)
    ).first()
    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    new_access_token = create_access_token(data={"sub": str(db_user.id)})
    return {
        "access_token": new_access_token,
        "refresh_token": body.refresh_token,
        "token_type": "bearer",
    }

# ===============
# LOGOUT ENDPOINT
# ===============

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
        body: TokenLogoutRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    # Отзываем refresh-токен: удаляем запись из Redis
    await revoke_refresh_token(jti)
    return