import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from v32.config.settings import settings

pool = ConnectionPool.from_url(
    str(settings.REDIS_URL),
    decode_responses=True,
    max_connections=25
)

async def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=pool)

async def close_redis_pool():
    if pool:
        await pool.disconnect()
