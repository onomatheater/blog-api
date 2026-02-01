"""
Главный файл приложения
Здесь инициализируется FastAPI и подключаются маршруты
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes import posts, comments, auth
from app.config import settings

from dotenv import load_dotenv
load_dotenv()

# Подключаем кэширование
from contextlib import asynccontextmanager
from app.services.cache import cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.close()

# Создаем приложение
app = FastAPI(
    title="Blog API",
    description="Simple blog with posts and comments",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan, # Redis
)

# CORS (чтобы фронтенд мог обращаться к API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"], # В продакшене указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )


# ==============
# HEALTH-CHECKING
# ==============

@app.get("/health")
async def health_check():
    """Проверка, что приложение живо"""
    return {"status": "ok"}

#

# =====================
# Подключаем все ROUTES
# =====================

app.include_router(auth.router) # Регистрация и авторизация
app.include_router(posts.router) # Посты
app.include_router(comments.router) # Комментарии

# ==============================
# Подключение FRONT-END
# ==============================

# Главная страница
@app.get("/")
async def serve_frontend():
    """Отдаем главную страницу фронтенда"""
    return FileResponse("frontend/index.html")

# Подключение статических файлов
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)