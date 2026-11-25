"""Per-domain rate limiter backed by Redis (token bucket algorithm)."""

import asyncio
import time

import tldextract

# Domain-specific rate limits (requests per second)
DOMAIN_RATES: dict[str, float] = {
    # Universities — be polite
    "edu": 0.5,
    "ac.uk": 0.5,
    "ac.in": 0.5,
    # Government — very polite
    "gov": 0.3,
    "europa.eu": 0.3,
    # AI companies — moderate
    "google.com": 1.0,
    "microsoft.com": 1.0,
    "openai.com": 0.5,
    "anthropic.com": 0.5,
    "deepmind.google": 0.5,
    "huggingface.co": 1.0,
    # APIs — can be faster
    "github.com": 2.0,
    "api.github.com": 5.0,
    # Scholar — very restrictive
    "scholar.google.com": 0.1,
    "semanticscholar.org": 1.0,
}

DEFAULT_RATE = 1.0  # 1 request per second


def get_domain(url: str) -> str:
    """Extract the registered domain from a URL."""
    extracted = tldextract.extract(url)
    if extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"
    return extracted.domain


def get_rate_for_domain(domain: str) -> float:
    """Get the rate limit for a domain, checking suffix-based rules too."""
    # Direct domain match
    if domain in DOMAIN_RATES:
        return DOMAIN_RATES[domain]

    # Suffix match (e.g., *.edu)
    parts = domain.split(".")
    for i in range(len(parts)):
        suffix = ".".join(parts[i:])
        if suffix in DOMAIN_RATES:
            return DOMAIN_RATES[suffix]

    return DEFAULT_RATE


class InMemoryRateLimiter:
    """
    Simple in-memory token bucket rate limiter.

    For production use with multiple workers, replace with
    RedisRateLimiter (below). This version works for single-process.
    """

    def __init__(self) -> None:
        self._last_request: dict[str, float] = {}
        self._async_locks: dict[str, asyncio.Lock] = {}

    async def wait_and_acquire_async(self, url: str) -> None:
        """Rate limit without blocking the event loop or racing local callers."""
        domain = get_domain(url)
        lock = self._async_locks.setdefault(domain, asyncio.Lock())
        async with lock:
            wait = self.acquire(url)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[domain] = time.time()

    def acquire(self, url: str) -> float:
        """
        Check rate limit and return wait time in seconds.

        Returns 0.0 if the request can proceed immediately.
        Returns > 0.0 with the number of seconds to wait.
        """
        domain = get_domain(url)
        rate = get_rate_for_domain(domain)
        min_interval = 1.0 / rate

        now = time.time()
        last = self._last_request.get(domain, 0.0)
        elapsed = now - last

        if elapsed >= min_interval:
            self._last_request[domain] = now
            return 0.0
        else:
            wait_time = min_interval - elapsed
            return wait_time

    def wait_and_acquire(self, url: str) -> None:
        """Block until the rate limit allows the request."""
        wait = self.acquire(url)
        if wait > 0:
            time.sleep(wait)
        # Update timestamp after waiting
        domain = get_domain(url)
        self._last_request[domain] = time.time()


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed crawling.

    Uses a sliding window approach with Redis SETNX + PEXPIRE.
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    async def acquire(self, url: str) -> float:
        """Atomically reserve a domain slot and return any required wait."""
        domain = get_domain(url)
        rate = get_rate_for_domain(domain)
        min_interval_ms = int(1000.0 / rate)

        key = f"ratelimit:{domain}"
        now_ms = int(time.time() * 1000)
        wait_ms = await self.redis.eval(
            "local now = tonumber(ARGV[1]); local interval = tonumber(ARGV[2]); "
            "local slot = tonumber(redis.call('GET', KEYS[1]) or now); "
            "if slot < now then slot = now end; "
            "redis.call('SET', KEYS[1], slot + interval, 'PX', (slot - now) + interval * 2); "
            "return slot - now",
            1,
            key,
            now_ms,
            min_interval_ms,
        )
        return max(int(wait_ms), 0) / 1000.0

    async def wait_and_acquire(self, url: str) -> None:
        """Block until the rate limit allows the request."""
        import asyncio

        wait = await self.acquire(url)
        if wait > 0:
            await asyncio.sleep(wait)


class RedisSyncRateLimiter:
    """Redis-backed atomic reservation for synchronous Celery crawler tasks."""

    def __init__(self, redis_url: str) -> None:
        from redis import Redis

        self.redis = Redis.from_url(redis_url)

    def wait_and_acquire(self, url: str) -> None:
        domain = get_domain(url)
        interval_ms = int(1000.0 / get_rate_for_domain(domain))
        now_ms = int(time.time() * 1000)
        wait_ms = self.redis.eval(
            "local now = tonumber(ARGV[1]); local interval = tonumber(ARGV[2]); "
            "local slot = tonumber(redis.call('GET', KEYS[1]) or now); "
            "if slot < now then slot = now end; "
            "redis.call('SET', KEYS[1], slot + interval, 'PX', (slot - now) + interval * 2); "
            "return slot - now",
            1,
            f"ratelimit:{domain}",
            now_ms,
            interval_ms,
        )
        if wait_ms > 0:
            time.sleep(wait_ms / 1000)
