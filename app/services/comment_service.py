# app/services/comment_service.py

"""
Сервисный слой для комментариев.

Знает про Comment/Post/User и БД, но не про HTTP-исключения.
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from app.models import Comment, User, Post
from app.schemas import CommentCreate, CommentUpdate


async def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    """
    Утилита для поиска поста по id.
    """
    return db.query(Post).filter(Post.id == post_id).first()


async def create_comment_for_post(
    db: Session,
    post: Post,
    author: User,
    comment_in: CommentCreate,
) -> Comment:
    """
    Создать комментарий к посту от имени пользователя.
    """
    db_comment = Comment(
        content=comment_in.content,
        user_id=author.id,
        post_id=post.id,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


async def list_comments_for_post(
    db: Session,
    post_id: int,
) -> List[Comment]:
    """
    Вернуть все комментарии к посту без учёта кэша.
    """
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
        .all()
    )


async def get_comment_for_post(
    db: Session,
    post_id: int,
    comment_id: int,
) -> Optional[Comment]:
    """
    Найти конкретный комментарий по post_id и comment_id.
    """
    return (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        )
        .first()
    )


async def update_comment_for_user(
    db: Session,
    post_id: int,
    comment_id: int,
    comment_update: CommentUpdate,
    current_user: User,
) -> Optional[Comment] | bool:
    """
    Обновить комментарий:
    - None  -> комментарий не найден (или не принадлежит post_id);
    - False -> пользователь не владелец;
    - Comment -> успешно обновлён.
    """
    db_comment = await get_comment_for_post(db=db, post_id=post_id, comment_id=comment_id)
    if not db_comment:
        return None

    if db_comment.user_id != current_user.id:
        return False

    update_data = comment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_comment, key, value)

    db.commit()
    db.refresh(db_comment)
    return db_comment


async def delete_comment_for_user(
    db: Session,
    post_id: int,
    comment_id: int,
    current_user: User,
) -> Optional[bool]:
    """
    Удалить комментарий:
    - None  -> комментарий не найден (или не принадлежит post_id);
    - False -> пользователь не владелец;
    - True  -> успешно удалён.
    """
    db_comment = await get_comment_for_post(db=db, post_id=post_id, comment_id=comment_id)
    if not db_comment:
        return None

    if db_comment.user_id != current_user.id:
        return False

    db.delete(db_comment)
    db.commit()
    return True
