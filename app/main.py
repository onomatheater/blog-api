"""
Главный файл приложения
Здесь инициализируется FastAPI и подключаются маршруты
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from dotenv import load_dotenv
load_dotenv()

from app.routes import posts, comments, auth
from app.config import settings






# Подключаем кэширование
from app.services.cache import cache
from contextlib import asynccontextmanager


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





# Подключаем хендлеры

from app.utils.exceptions import (
    app_error_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
    AppError,
    rate_limit_exceeded_handler,
)

# Глобальные обработчики ошибок

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# =============================
# Ограничитель частоты запросов
# =============================
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from app.utils.limiter import limiter


app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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