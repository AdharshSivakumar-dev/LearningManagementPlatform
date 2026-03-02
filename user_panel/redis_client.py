import os
import logging
from typing import Optional
from redis import asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception as e:
            logging.warning(f"Redis not available: {e}")
            _redis = None
    return _redis


async def close_redis():
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        finally:
            _redis = None

