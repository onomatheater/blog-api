# app/routes/auth.py

"""
API endpoints для регистрации и авторизации.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.models import User
from app.utils.database import get_db
from app.utils.security import hash_password, verify_password, create_access_token

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
def register_user(
        user: UserCreate,
        db: Session = Depends(get_db),
):

    # Проверяем сложность пароля
    validate_password_strength(user.password)

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

    return {"access_token": access_token, "token_type": "bearer"}


# ==============================
# Авторизация созданного профиля
# ==============================

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """Логин пользователя"""

    # Поиск пользователя по email или username
    db_user = None

    db_user = db.query(User).filter(User.email == user.email).first()

    # Если пользователь не найден
    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка пароля

    #DEBUG_TEMP
    print("LOGIN DEBUG:", user.email, user.password, db_user.hashed_password)

    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(db_user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }