"""
Docstring for app.main

Главный файл приложения
Здесь инициализируется FastAPI и подключаются маршруты
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import posts, comments, auth
from app.config import settings

# Создаем приложение
app = FastAPI(
    title="Blog API",
    description="Simple blog with posts and comments",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# CORS (чтобы фронтенд мог обращаться к API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

# ==============
# HEALTH-CHEKING
# ==============

@app.get("/health")
async def health_check():
    """Проверка что приложение живо"""
    return {"status": "ok"}

@app.get("/")
async def root():
    """ Главная страница API """
    return {
        "message": "Blog API is running",
        "docs": f"{settings.API_PREFIX}/docs",
        "redoc": f"{settings.API_PREFIX}/redoc",
    }


# =====================
# Подключаем все ROUTES
# =====================

# Регистрация и авторизация
app.include_router(auth.router)

# Посты
app.include_router(posts.router)

# Комментарии
app.include_router(comments.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)