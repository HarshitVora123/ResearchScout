"""Search Agent — executes intelligent searches across multiple APIs."""


import httpx

from app.config import get_settings
from app.models.schemas.agent import SearchResult

settings = get_settings()


class SearchAgent:
    """
    Executes multi-engine searches to discover research opportunity URLs.

    Supports:
    - Google Custom Search Engine
    - Bing Web Search API
    - Tavily Search API
    - Direct site-specific searches

    Uses API fallback chains: Google → Bing → Tavily on failure.
    """

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=15.0)

    async def search(
        self,
        query: str,
        engines: list[str] | None = None,
        max_results: int = 10,
        site_restrict: str | None = None,
    ) -> list[SearchResult]:
        """Execute a search query across multiple engines."""
        engines = engines or ["google", "tavily"]
        results: list[SearchResult] = []

        if site_restrict:
            query = f"site:{site_restrict} {query}"

        for engine in engines:
            try:
                engine_results = await self._search_engine(engine, query, max_results)
                results.extend(engine_results)
            except Exception as e:
                print(f"Search engine {engine} failed: {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        return unique_results

    async def _search_engine(
        self, engine: str, query: str, max_results: int
    ) -> list[SearchResult]:
        """Dispatch to the appropriate search engine."""
        match engine:
            case "google":
                return await self._search_google(query, max_results)
            case "bing":
                return await self._search_bing(query, max_results)
            case "tavily":
                return await self._search_tavily(query, max_results)
            case _:
                return []

    async def _search_google(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using Google Custom Search Engine API."""
        if not settings.google_cse_api_key or not settings.google_cse_cx:
            return []

        response = await self.client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.google_cse_api_key,
                "cx": settings.google_cse_cx,
                "q": query,
                "num": min(max_results, 10),
            },
        )
        response.raise_for_status()
        data = response.json()

        return [
            SearchResult(
                url=item["link"],
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                source_engine="google",
                relevance_score=1.0 - (i * 0.05),
            )
            for i, item in enumerate(data.get("items", []))
        ]

    async def _search_bing(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using Bing Web Search API."""
        if not settings.bing_search_api_key:
            return []

        response = await self.client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            params={"q": query, "count": max_results},
            headers={"Ocp-Apim-Subscription-Key": settings.bing_search_api_key},
        )
        response.raise_for_status()
        data = response.json()

        return [
            SearchResult(
                url=item["url"],
                title=item.get("name", ""),
                snippet=item.get("snippet", ""),
                source_engine="bing",
                relevance_score=1.0 - (i * 0.05),
            )
            for i, item in enumerate(data.get("webPages", {}).get("value", []))
        ]

    async def _search_tavily(self, query: str, max_results: int) -> list[SearchResult]:
        """Search using Tavily Search API (AI-optimized)."""
        if not settings.tavily_api_key:
            return []

        response = await self.client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
            },
        )
        response.raise_for_status()
        data = response.json()

        return [
            SearchResult(
                url=item["url"],
                title=item.get("title", ""),
                snippet=item.get("content", "")[:300],
                source_engine="tavily",
                relevance_score=item.get("score", 0.5),
            )
            for item in data.get("results", [])
        ]

    async def close(self) -> None:
        """Clean up the HTTP client."""
        await self.client.aclose()
