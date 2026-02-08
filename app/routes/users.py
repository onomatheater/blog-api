# app/routes/users.py

"""
API enpoints для работы с текущим пользователем.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas import UserResponse
from app.models import User
from app.utils.database import get_db
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Возвращает данные текущего пользователя:
    id, username, email, created_at
    """
    return current_user