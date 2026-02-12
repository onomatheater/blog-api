# app/services/auth_tokens.py

from app.services.cache import cache
from app.config import settings

REFRESH_PREFIX = "refresh"

async def store_refresh_token(jti: str, user_id: int) -> None:
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    key = f"{REFRESH_PREFIX}:{jti}"
    await cache.set(
        key,
        {"user_id": user_id},
        ttl=ttl_seconds,
    )

async def is_refresh_token_active(jti: str) -> bool:
    key = f"{REFRESH_PREFIX}:{jti}"
    data = await cache.get(key)
    return data is not None

async def revoke_refresh_token(jti: str) -> None:
    key = f"{REFRESH_PREFIX}:{jti}"
    await cache.delete(key)
