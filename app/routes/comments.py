# app/routes/comments.py

"""
API endpoints для комментариев.

Все endpoints кроме GET требуют авторизации.
Удаление/обновление - только для автора комментария.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import CommentCreate, CommentResponse, CommentUpdate, CommentWithAuthor
from app.models import Comment, Post, User
from app.utils.database import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/comments", tags=["comments"])

@router.post("/posts/{post_id}", response_model=CommentWithAuthor, status_code=status.HTTP_201_CREATED)
async def create_comment(
        post_id: int,
        comment: CommentCreate,
        current_user: User = Depends(get_current_user), # <- требуем авторизацию
        db: Session = Depends(get_db)
):
    """
    Создаем комментарий к посту.

    Только для авторизованных пользователей.
    """

    # Проверяем что пост существует
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Создаем комментарий
    db_comment = Comment(
        content=comment.content,
        user_id=current_user.id,
        post_id=post.id
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment

@router.get("/posts/{post_id}", response_model=list[CommentWithAuthor])
async def list_comments(
        post_id: int,
        skip: int = 0,
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """
    Получить все комментарии к посту.

    Не требует авторизации.
    """
    post = db.query(Post).filter(Post.id == post_id).first()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Получаем комментарии к посту
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return comments

@router.get("/{comment_id}", response_model=CommentWithAuthor)
async def get_comment(
        comment_id: int,
        db: Session = Depends(get_db)
):
    """
    Получить конкретный комментарий.

    Не требует авторизации
    """

    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    return comment

@router.put("/{comment_id}", response_model=CommentWithAuthor)
async def update_comment(
        comment_id: int,
        comment: CommentUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Обновить комментарий.

    Только для автора комментария.
    """

    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    # Проверка на авторство комментария
    if db_comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to update this comment"
        )

    # Обновляем комментарий
    db_comment.content = comment.content

    db.commit()
    db.refresh(db_comment)

    return db_comment

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
        comment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Удалить комментарий.

    Проверка авторизации, поиск комментария, проверка на авторство.
    """

    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if db_comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail = "You are not allowed to delete this comment"
        )

    db.delete(db_comment)
    db.commit()

    return None