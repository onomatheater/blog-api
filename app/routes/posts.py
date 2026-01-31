"""
API endpoints для публикаций
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from app.schemas import PostCreate, PostResponse, PostUpdate, PostWithComments, PostWithAuthor
from app.models import Post, User
from app.utils.database import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/posts", tags=["posts"])

# =========================
# СОЗДАНИЕ НОВОЙ ПУБЛИКАЦИИ
# =========================
@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
        post: PostCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    # Создание публикации с привязкой к текущему пользователю
    db_post = Post(
        title=post.title,
        content=post.content,
        is_published=post.is_published,
        user_id=current_user.id
    )

    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    return db_post


# ==========================
# ПОЛУЧИТЬ СПИСОК ВСЕХ ПУБЛИКАЦИЙ
# ==========================
@router.get("/", response_model=list[PostWithAuthor])
async def list_posts(skip: int = 0,
               limit: int = 10,
               db: Session = Depends(get_db)
):
    """
    Получаем список всех постов (публичных endpoints)

    Не требует авторизации.
    Возвращает посты со своими авторами.
    """

    posts = db.query(Post).offset(skip).limit(limit).all()
    return posts

# ==========================================
# ПОЛУЧИТЬ ПУБЛИКАЦИЮ СО ВСЕМИ КОММЕНТАРИЯМИ
# ==========================================
@router.get("/{post_id}", response_model=PostWithComments)
async def get_post(
        post_id: int,
        db: Session = Depends(get_db)
):
    """
    Получаем полный пост со всеми комментариями.

    Не требует авторизации.
    Возвращает информацию о посте, об авторе, все комментарии с авторами комментариев
    """

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return post


# =====================================
# ОБНОВЛЕНИЕ(РЕДАКТИРОВАНИЕ) ПУБЛИКАЦИИ
# =====================================
@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
        post_id: int,
        post_update: PostUpdate,
        current_user: User = Depends(get_current_user), # Требование авторизации
        db: Session = Depends(get_db)
):
    """
    Обновление (редактирование) поста
    """

    # Поиск поста
    db_post = db.query(Post).filter(Post.id == post_id).first()

    if not db_post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    # Проверяем что текущий пользователь - автор поста
    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    # Обновляем только переданные поля
    update_data = post_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)

    db.commit()
    db.refresh(db_post)

    return db_post


# ==================
# УДАЛИТЬ ПУБЛИКАЦИЮ
# ==================

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
        post_id: int,
        db: Session = Depends(get_db)
):
    """
    Удаление поста
    """

    db_post = db.query(Post).filter(Post.id == post_id).first()

    if not db_post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"

        )

    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    db.delete(db_post)
    db.commit()

    return None
