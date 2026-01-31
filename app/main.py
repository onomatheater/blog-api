"""
Docstring for app.main

Главный файл приложения
Здесь инициализируется FastAPI и подключаются маршруты
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import posts
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

# Тестовый endpoint
@app.get("/health")
async def health_check():
    """Проверка что приложение живо"""
    return {"status": "ok"}

# Подключить маршруты ниже

app.include_router(posts.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Blog API is running"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)