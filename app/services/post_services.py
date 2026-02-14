# app/services/post_services.py

"""
Сервисный слой для постов.

Знает про модели и кэш, но не про HTTP-статусы/исключения.
"""

from typing import Optional, Literal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, desc

from app.models import Post, User, Comment
from app.schemas import PostCreate, PostUpdate, PostWithAuthor
from app.services.cache import cache

# Ключ кэша для "главной" публичной ленты
POSTS_CACHE_KEY = "posts:list:main"
# Префикс для кэша поисковых запросов
SEARCH_CACHE_PREFIX = "posts:search:"


async def create_post_for_user(
    db: Session,
    author: User,
    post_in: PostCreate,
) -> Post:
    """
    Создать пост для конкретного пользователя и сбросить кэш ленты.
    """
    db_post = Post(
        title=post_in.title,
        content=post_in.content,
        is_published=post_in.is_published,
        user_id=author.id,
    )

    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    # Инвалидация кэша главной ленты
    await cache.delete(POSTS_CACHE_KEY)

    return db_post


async def list_posts_with_filters(
    db: Session,
    skip: int,
    limit: int,
    sort: Literal["asc", "desc"],
    is_published: Optional[bool],
    q: Optional[str],
    current_user: Optional[User],
) -> list[PostWithAuthor] | list[dict]:
    """
    Вернуть список постов с учётом:
    - прав доступа (аноним / авторизованный),
    - фильтра публикации,
    - поисковой строки q,
    - кэширования главной ленты и простых поисковых запросов.
    """

    # Условие использования кэша для главной публичной ленты
    use_cache = (
        skip == 0
        and limit == 10
        and sort == "desc"
        and is_published is None
        and current_user is None
        and q is None
    )

    search_cache_key: Optional[str] = None

    # Кэшируем только "простые" поисковые запросы: публичный поиск, дефолтная пагинация
    if q and skip == 0 and limit == 10 and sort == "desc" and current_user is None:
        search_cache_key = f"{SEARCH_CACHE_PREFIX}q={q}"
        cached_search = await cache.get(search_cache_key)
        if cached_search is not None:
            # Здесь уже словари, готовые к возврату
            return cached_search

    # Проверяем кэш главной ленты
    if use_cache:
        cached = await cache.get(POSTS_CACHE_KEY)
        if cached is not None:
            return cached

    # Базовый запрос с подгрузкой автора
    query = db.query(Post).options(joinedload(Post.author))

    # Логика видимости по is_published и текущему пользователю
    if is_published is False:
        if current_user is None:
            # Аноним с is_published=false: показываем только опубликованные
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

    # Поиск по заголовку/контенту (регистронезависимый)
    if q:
        # Защита от слишком коротких запросов
        if len(q) < 3:
            return []
        pattern = f"%{q}%"
        query = query.filter(
            (Post.title.ilike(pattern)) | (Post.content.ilike(pattern))
        )

    # Сортировка по дате создания
    if sort == "asc":
        query = query.order_by(asc(Post.created_at))
    else:
        query = query.order_by(desc(Post.created_at))

    # Пагинация
    posts = query.offset(skip).limit(limit).all()

    # Кэшируем главную ленту
    if use_cache:
        data = [PostWithAuthor.model_validate(p).model_dump() for p in posts]
        await cache.set(POSTS_CACHE_KEY, data, ttl=300)
        return data

    # Кэшируем поисковые результаты (для простых запросов)
    if search_cache_key:
        data = [PostWithAuthor.model_validate(p).model_dump() for p in posts]
        await cache.set(search_cache_key, data, ttl=300)
        return data

    # Без кэша возвращаем ORM-объекты, FastAPI сам их превратит в PostWithAuthor
    return posts


async def get_post_with_comments(
    db: Session,
    post_id: int,
) -> Optional[Post]:
    """
    Вернуть пост с автором и комментариями (без HTTP-исключений).
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
    return post


async def update_post_for_user(
    db: Session,
    post_id: int,
    post_update: PostUpdate,
    current_user: User,
) -> Optional[Post] | bool:
    """
    Обновить пост:
    - None  -> пост не найден;
    - False -> пользователь не владелец;
    - Post  -> успешное обновление.
    """
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        return None

    if db_post.user_id != current_user.id:
        return False

    update_data = post_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)

    db.commit()
    db.refresh(db_post)

    # Инвалидация кэша главной ленты
    await cache.delete(POSTS_CACHE_KEY)

    return db_post


async def delete_post_for_user(
    db: Session,
    post_id: int,
    current_user: User,
) -> Optional[bool]:
    """
    Удалить пост:
    - None  -> пост не найден;
    - False -> пользователь не владелец;
    - True  -> успешно удалён.
    """
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        return None

    if db_post.user_id != current_user.id:
        return False

    db.delete(db_post)
    db.commit()

    # Инвалидация кэша главной ленты
    await cache.delete(POSTS_CACHE_KEY)

    return True
