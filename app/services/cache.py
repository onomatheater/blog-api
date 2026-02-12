import json
from typing import Any, Optional

import redis.asyncio as redis

from app.config import settings

class RedisCache:
    def __init__(self, url: str):
        self._url = url
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        if self._client is None:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> Optional[Any]:
        if self._client is None:
            return None
        raw_data = await self._client.get(key)
        if raw_data is None:
            return None
        return json.loads(raw_data)

    async def set(
            self,
            key: str,
            value: Any,
            ttl: int = 300,
    ):
        if self._client is None:
            return
        await self._client.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str):
        if self._client is None:
            return
        await self._client.delete(key)

    async def ping(self) -> bool:
        """
        Простейшая проверка доступности Redis
        Возвращает True, если пинг прошел, иначе False.
        """
        if self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

cache = RedisCache(settings.REDIS_URL)