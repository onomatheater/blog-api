"""
Docstring for app.config

Конфигурация приложения.
Всё берется из .env файла.
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Server
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Создаем глобальный объект settings
settings = Settings()