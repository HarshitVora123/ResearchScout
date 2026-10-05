"""
Async Redis Caching Layer — decorator and utilities for API response caching.
"""

import functools
import json
from collections.abc import Callable
from typing import Any

import structlog

from app.core.redis import get_redis

logger = structlog.get_logger(__name__)


def cache_response(ttl_seconds: int = 300, key_prefix: str = "cache") -> Callable:
    """
    Decorator for caching async FastAPI endpoint responses in Redis.

    Args:
        ttl_seconds: Cache time-to-live in seconds (default: 5 minutes)
        key_prefix: Redis key namespace
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Compose cache key from function name and sorted kwargs
            kwargs_str = json.dumps(
                {k: str(v) for k, v in sorted(kwargs.items()) if k not in ("db", "user", "request")},
                sort_keys=True,
            )
            cache_key = f"{key_prefix}:{func.__name__}:{kwargs_str}"

            try:
                redis = await get_redis()
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug("cache_hit", key=cache_key)
                    return json.loads(cached)
            except Exception as e:
                logger.warning("cache_read_error", error=str(e))

            # Execute function
            result = await func(*args, **kwargs)

            try:
                redis = await get_redis()
                # Serialize Pydantic models or dicts/lists
                serializable = result.model_dump() if hasattr(result, "model_dump") else result
                await redis.setex(cache_key, ttl_seconds, json.dumps(serializable))
                logger.debug("cache_set", key=cache_key, ttl=ttl_seconds)
            except Exception as e:
                logger.warning("cache_write_error", error=str(e))

            return result

        return wrapper

    return decorator


async def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate all Redis keys matching a pattern (e.g. 'cache:get_trending:*')."""
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        if keys:
            deleted = await redis.delete(*keys)
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
            return deleted
    except Exception as e:
        logger.warning("cache_invalidate_error", error=str(e))
    return 0
