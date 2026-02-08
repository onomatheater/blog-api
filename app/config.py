"""
Docstring for app.config

Конфигурация приложения.
Всё берется из .env файла.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pydantic Settings конфиг
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

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

    # RATE-LIMITS
    REGISTER_RATE_LIMIT: str = "5/minute" # Значения по-умолчанию, на случай
    LOGIN_RATE_LIMIT: str = "10/minute"   # если в .env не указаны иные значения

# Создаем глобальный объект settings
settings = Settings()