"""
API endpoints для публикаций
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Literal, Optional
from sqlalchemy import asc, desc

from app.schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    PostWithComments,
    PostWithAuthor,
)
from app.models import Post, User, Comment
from app.utils.database import get_db
from app.dependencies import get_current_user, get_current_user_optional

from app.services.cache import cache

POSTS_CACHE_KEY = "posts:list:main"
SEARCH_CACHE_PREFIX = "posts:search:"

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

    db_post = Post(
        title=post.title,
        content=post.content,
        is_published=post.is_published,
        user_id=current_user.id,
    )

    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    await cache.delete(POSTS_CACHE_KEY)

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
    Получаем список всех постов.

    Не требует авторизации.
    Возвращает посты со своими авторами, отсортированные по created_at.
    """

    # Кэшируем только "главную" ленту без фильтра и авторизации
    use_cache = (
            skip == 0
            and limit == 10
            and sort == "desc"
            and is_published is None
            and current_user is None
            and q is None
    )

    search_cache_key = None
    # Кэшируем только публичный поиск по умолчанию
    if q and skip == 0 and limit == 10 and sort == "desc" and current_user is None:
        search_cache_key = f"{SEARCH_CACHE_PREFIX}:q={q}"
        cached_search = await cache.get(search_cache_key)
        if cached_search is not None:
            return cached_search

    if use_cache:
        cached = await cache.get(POSTS_CACHE_KEY)
        if cached is not None:
            return cached


    query = db.query(Post).options(joinedload(Post.author))

    if is_published is False:
        if current_user is None:
            # Неавторизованный запрос с is_published=false:
            # можно либо игнорировать параметр, либо явно возвращать только опубликованные.
            query = query.filter(Post.is_published == True)
        else:
            # Авторизованный: только свои черновики
            query = query.filter(
                Post.is_published == False,
                Post.user_id == current_user.id,
            )
    elif is_published is True:
        # Явный запрос только опубликованных
        query = query.filter(Post.is_published == True)
    else:
        # is_published не указан
        if current_user is None:
            # Аноним: только опубликованные
            query = query.filter(Post.is_published == True)
        else:
            # Авторизованный: опубликованные + свои черновики
            query = query.filter(
                (Post.is_published == True) | (Post.user_id == current_user.id)
            )

    if q:
        if len(q) < 3 :
            return []
        pattern = f"%{q}%"
        query = query.filter(
            (Post.title.ilike(pattern)) | (Post.content.ilike(pattern))
        )

    if sort == "asc":
        query = query.order_by(asc(Post.created_at))
    else:
        query = query.order_by(desc(Post.created_at))

    posts = query.offset(skip).limit(limit).all()

    if use_cache:
        data = [PostWithAuthor.model_validate(p).model_dump() for p in posts]
        await cache.set(POSTS_CACHE_KEY, data, ttl=300)
        return data

    if search_cache_key:
        data = [PostWithAuthor.model_validate(p).model_dump() for p in posts]
        await cache.set(search_cache_key, data, ttl=300)
        return data

    return posts




# ==========================================
# ПОЛУЧИТЬ ПУБЛИКАЦИЮ СО ВСЕМИ КОММЕНТАРИЯМИ
# ==========================================

@router.get("/{post_id}", response_model=PostWithComments)
async def get_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    """
    Получаем полный пост со всеми комментариями.

    Не требует авторизации.
    Возвращает информацию о посте, об авторе, все комментарии с авторами комментариев.
    """

    post = (
        db.query(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.comments).joinedload(Comment.author),
        )
        .filter(Post.id == post_id)
        .first()
    )

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
    Обновление (редактирование) поста.
    """

    db_post = db.query(Post).filter(Post.id == post_id).first()

    if not db_post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
        )

    update_data = post_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)

    db.commit()
    db.refresh(db_post)

    await cache.delete(POSTS_CACHE_KEY)

    return db_post




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
    Удаление поста.
    """

    db_post = db.query(Post).filter(Post.id == post_id).first()

    if not db_post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
        )

    db.delete(db_post)
    db.commit()

    await cache.delete(POSTS_CACHE_KEY)

    return None
