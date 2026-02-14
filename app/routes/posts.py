# app/routes/posts.py

"""
API endpoints для публикаций

Роуты тонкие: только валидация и вызов сервисного слоя.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Literal, Optional

from app.schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    PostWithComments,
    PostWithAuthor,
)
from app.models import User
from app.utils.database import get_db
from app.dependencies import get_current_user, get_current_user_optional

from app.services.post_services import (
    create_post_for_user,
    list_posts_with_filters,
    get_post_with_comments,
    update_post_for_user,
    delete_post_for_user,
)

router = APIRouter(prefix="/api/v1/posts", tags=["posts"])


# =========================
# СОЗДАНИЕ НОВОЙ ПУБЛИКАЦИИ
# =========================

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создание публикации с привязкой к текущему пользователю.
    """
    db_post = await create_post_for_user(db=db, author=current_user, post_in=post)
    return db_post


# ==========================
# ПОЛУЧИТЬ СПИСОК ВСЕХ ПУБЛИКАЦИЙ
# ==========================

@router.get("", response_model=list[PostWithAuthor])
async def list_posts(
    skip: int = 0,
    limit: int = 10,
    sort: Literal["asc", "desc"] = "desc",
    is_published: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Список постов с фильтрами, поиском и кэшированием.
    """
    return await list_posts_with_filters(
        db=db,
        skip=skip,
        limit=limit,
        sort=sort,
        is_published=is_published,
        q=q,
        current_user=current_user,
    )


# ==========================================
# ПОЛУЧИТЬ ПУБЛИКАЦИЮ СО ВСЕМИ КОММЕНТАРИЯМИ
# ==========================================

@router.get("/{post_id}", response_model=PostWithComments)
async def get_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    """
    Полный пост с автором и комментариями.
    """
    post = await get_post_with_comments(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )
    return post


# =====================================
# ОБНОВЛЕНИЕ(РЕДАКТИРОВАНИЕ) ПУБЛИКАЦИИ
# =====================================

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Обновление поста, доступно только автору.
    """
    result = await update_post_for_user(
        db=db,
        post_id=post_id,
        post_update=post_update,
        current_user=current_user,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if result is False:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
        )

    return result


# ==================
# УДАЛИТЬ ПУБЛИКАЦИЮ
# ==================

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Удаление поста, доступно только автору.
    """
    result = await delete_post_for_user(
        db=db,
        post_id=post_id,
        current_user=current_user,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if result is False:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
        )

    return None
