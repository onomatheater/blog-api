# app/routes/comments.py

"""
API endpoints для комментариев.

Все endpoints кроме GET требуют авторизации.
Удаление/обновление - только для автора комментария.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Literal
from sqlalchemy import asc, desc

from app.schemas import CommentCreate, CommentResponse, CommentUpdate, CommentWithAuthor
from app.models import Comment, Post, User
from app.utils.database import get_db
from app.dependencies import get_current_user
from app.services.cache import cache
from app.services.comment_service import (
    get_post_by_id,
    create_comment_for_post,
    list_comments_for_post,
    get_comment_for_post,
    update_comment_for_user,
    delete_comment_for_user,
)


router = APIRouter(prefix="/api/v1/posts", tags=["comments"])

COMMENTS_CACHE_KEY = "comments"

async def invalidate_comments_cache(
        post_id: int,
):
    # чистим обе сортировки
    await cache.delete(f"{COMMENTS_CACHE_KEY}:{post_id}:sort=desc")
    await cache.delete(f"{COMMENTS_CACHE_KEY}:{post_id}:sort=asc")

@router.post(
    "/{post_id}/comments",
    response_model=CommentWithAuthor,
    status_code=status.HTTP_201_CREATED
)
async def create_comment(
    post_id: int,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создаём комментарий к посту.

    Только для авторизованных пользователей.
    """

    post = await get_post_by_id(db=db, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    db_comment = await create_comment_for_post(
        db=db,
        post=post,
        author=current_user,
        comment_in=comment,
    )

    await invalidate_comments_cache(post_id)

    return db_comment


@router.get("/{post_id}/comments", response_model=list[CommentWithAuthor])
async def list_comments(
    post_id: int,
    skip: int = 0,
    limit: int = 50,
    sort: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    """
    Получить все комментарии к посту с сортировкой и пагинацией.

    Не требует авторизации.
    """

    post = await get_post_by_id(db=db, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    use_cache = skip == 0 and limit == 50
    cache_key = f"{COMMENTS_CACHE_KEY}:{post_id}:sort={sort}"

    if use_cache:
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

    # базовый список из сервиса
    comments = await list_comments_for_post(db=db, post_id=post_id)

    # сортировка и пагинация остаются в роуте (это уже HTTP-уровень)
    if sort == "asc":
        comments.sort(key=lambda c: c.created_at)
    else:
        comments.sort(key=lambda c: c.created_at, reverse=True)

    comments_slice = comments[skip: skip + limit]

    if use_cache:
        data = [
            CommentWithAuthor.model_validate(
                c, from_attributes=True
            ).model_dump()
            for c in comments_slice
        ]
        await cache.set(cache_key, data, ttl=300)
        return data

    return comments_slice


@router.get("/{post_id}/comments/{comment_id}", response_model=CommentWithAuthor)
async def get_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
):
    """
    Получить конкретный комментарий.

    Не требует авторизации.
    """

    comment = await get_comment_for_post(
        db=db,
        post_id=post_id,
        comment_id=comment_id
    )
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    return comment


@router.put("/{post_id}/comments/{comment_id}", response_model=CommentWithAuthor)
async def update_comment(
    post_id: int,
    comment_id: int,
    comment: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Обновить комментарий.

    Только для автора комментария.
    """

    result = await update_comment_for_user(
        db=db,
        post_id=post_id,
        comment_id=comment_id,
        comment_update=comment,
        current_user=current_user,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if result is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update this comment",
        )

    await invalidate_comments_cache(post_id)
    return result


@router.delete("/{post_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Удалить комментарий.

    Только автор комментария.
    """

    result = await delete_comment_for_user(
        db=db,
        post_id=post_id,
        comment_id=comment_id,
        current_user=current_user,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if result is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this comment",
        )

    await invalidate_comments_cache(post_id)
    return None
