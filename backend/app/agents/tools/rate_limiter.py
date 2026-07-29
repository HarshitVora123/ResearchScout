"""Per-domain rate limiter backed by Redis (token bucket algorithm)."""

import time
from urllib.parse import urlparse

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

    def __init__(self):
        self._last_request: dict[str, float] = {}

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
        """Check rate limit, return wait time in seconds."""
        domain = get_domain(url)
        rate = get_rate_for_domain(domain)
        min_interval_ms = int(1000.0 / rate)

        key = f"ratelimit:{domain}"
        now_ms = int(time.time() * 1000)

        # Try to get last request time
        last_ms = await self.redis.get(key)

        if last_ms is None:
            await self.redis.set(key, str(now_ms), px=min_interval_ms * 2)
            return 0.0

        elapsed_ms = now_ms - int(last_ms)

        if elapsed_ms >= min_interval_ms:
            await self.redis.set(key, str(now_ms), px=min_interval_ms * 2)
            return 0.0
        else:
            wait_ms = min_interval_ms - elapsed_ms
            return wait_ms / 1000.0

    async def wait_and_acquire(self, url: str) -> None:
        """Block until the rate limit allows the request."""
        import asyncio

        wait = await self.acquire(url)
        if wait > 0:
            await asyncio.sleep(wait)
        domain = get_domain(url)
        key = f"ratelimit:{domain}"
        rate = get_rate_for_domain(domain)
        min_interval_ms = int(1000.0 / rate)
        now_ms = int(time.time() * 1000)
        await self.redis.set(key, str(now_ms), px=min_interval_ms * 2)
