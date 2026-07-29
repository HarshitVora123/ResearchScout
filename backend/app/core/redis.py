"""Core Redis connection management."""

from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def get_redis() -> Redis:
    """FastAPI dependency that returns the Redis client."""
    return redis_client
