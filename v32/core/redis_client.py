import redis.asyncio as redis
from typing import Optional
from v32.config.settings import settings

# Global client instance
_redis_client: Optional[redis.Redis] = None

async def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client

async def close_redis_pool():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
