# app/schemas/__init__.py

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# =======================
# СХЕМЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# =======================

#
class UserBase(BaseModel):
    """
    Базовая схема пользователя
    """
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """
    Схема для создания пользователя (регистрация)
    """
    password: str


class UserLogin(BaseModel):
    """
    Схема для логина. Авторизация по e-mail
    """
    email: str
    password: str


class UserResponse(UserBase):
    """
    Схема ответа с инфо о пользователе
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenLogoutRequest(BaseModel):
    refresh_token: str

# ====================
# СХЕМЫ ДЛЯ ПУБЛИКАЦИИ
# ====================


class PostBase(BaseModel):
    """Базовая информация о посте"""
    title: str
    content: str
    is_published: bool = False


class PostCreate(PostBase):
    """Создание поста"""
    pass


class PostUpdate(BaseModel):
    """Обновление поста"""
    title: Optional[str] = None
    content: Optional[str] = None
    is_published: Optional[bool] = None


class PostResponse(PostBase):
    """Ответ с информацией о посте"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostWithAuthor(PostResponse):
    author: UserResponse

# ======================
# СХЕМЫ ДЛЯ КОММЕНТАРИЕВ
# ======================

class CommentBase(BaseModel):
    """Базовая информация о комментарии"""
    content: str

class CommentCreate(CommentBase):
    """Создание комментария"""
    pass

class CommentUpdate(CommentBase):
    """Обновление комментария"""
    content: str

class CommentResponse(CommentBase):
    id: int
    user_id: int
    post_id: int
    created_at: datetime
    updated_at: datetime

class CommentWithAuthor(CommentResponse):
    """Комментарий с инфо об авторе"""
    author: UserResponse

class PostWithComments(PostResponse):
    """Пост со всеми его комментариями и автором"""
    author: UserResponse
    comments: List[CommentWithAuthor]
