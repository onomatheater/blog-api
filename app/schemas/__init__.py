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
    Схема для логина. Авторизация либо по e-mail, либо по username
    """
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str


class UserResponse(UserBase):
    """
    Схема ответа с инфо о пользователе
    """
    id: int
    create_at: datetime

    class Config:
        from_attribute = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    author_rel: UserResponse

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
    author_rel: UserResponse

class PostWithComments(PostResponse):
    """Пост со всеми его комментариями и автором"""
    author_rel: UserResponse
    comments: List[CommentWithAuthor]
