"""Small process-local throttle for authentication endpoints."""

import time
from collections import defaultdict, deque

_attempts: dict[str, deque[float]] = defaultdict(deque)
WINDOW_SECONDS = 900
MAX_FAILED_LOGINS = 10
MAX_REGISTRATIONS = 10


async def check_auth_rate(key: str, limit: int) -> bool:
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        redis_key = f"auth-throttle:{key}"
        count = await redis.eval(
            "local count = redis.call('INCR', KEYS[1]); "
            "if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
            "return count",
            1,
            redis_key,
            WINDOW_SECONDS,
        )
        return count <= limit
    except Exception:
        # Keep a local safety net if Redis is unavailable.
        return _check_local_auth_rate(key, limit)


def _check_local_auth_rate(key: str, limit: int) -> bool:
    now = time.monotonic()
    attempts = _attempts[key]
    while attempts and attempts[0] <= now - WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= limit:
        return False
    attempts.append(now)
    return True


async def clear_auth_rate(key: str) -> None:
    _attempts.pop(key, None)
    try:
        from app.core.redis import get_redis

        await (await get_redis()).delete(f"auth-throttle:{key}")
    except Exception:
        pass
