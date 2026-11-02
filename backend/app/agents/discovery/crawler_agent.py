"""Crawler Agent — fetches and renders web pages with fallback strategies."""

import hashlib
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from markdownify import markdownify as md

from app.config import get_settings
from app.core.url_safety import resolve_redirect, validate_public_http_url
from app.models.schemas.agent import CrawlResult

settings = get_settings()


class CrawlerAgent:
    """
    Fetches web pages with intelligent fallback and content extraction.

    Fallback chain: httpx (static) → Crawl4AI (AI-native) → Playwright (complex JS)
    Respects robots.txt, rate limits, and anti-bot etiquette.
    """

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=settings.crawler_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.crawler_user_agent},
        )

    async def crawl(self, url: str, render_js: bool = False) -> CrawlResult:
        """
        Crawl a URL and return structured content.

        Args:
            url: The URL to crawl
            render_js: Whether JavaScript rendering is required

        Returns:
            CrawlResult with raw HTML, markdown, and metadata
        """
        start = time.time()

        try:
            if render_js:
                result = await self._crawl_with_js(url)
            else:
                result = await self._crawl_static(url)

            result.duration_ms = int((time.time() - start) * 1000)
            result.content_hash = hashlib.sha256(
                result.markdown.encode()
            ).hexdigest()

            return result

        except Exception as e:
            return CrawlResult(
                url=url,
                status_code=0,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )

    async def _crawl_static(self, url: str) -> CrawlResult:
        """Crawl a static HTML page with httpx."""
        current_url = validate_public_http_url(url)
        for _ in range(6):
            if not await self._robots_allowed(current_url):
                raise PermissionError("Crawl disallowed by robots.txt")
            async with self.client.stream("GET", current_url, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if location:
                        current_url = resolve_redirect(current_url, location)
                        continue
                size_header = response.headers.get("content-length")
                if size_header and int(size_header) > 5 * 1024 * 1024:
                    raise ValueError("Page exceeds the 5 MiB crawl limit")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 5 * 1024 * 1024:
                        raise ValueError("Page exceeds the 5 MiB crawl limit")
                raw_html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                response_url = str(response.url)
                response_status = response.status_code
                response_content_type = response.headers.get("content-type", "text/html")
                response_headers = dict(response.headers)
            break
        else:
            raise ValueError("Too many redirects")

        markdown = self._html_to_markdown(raw_html)
        title = self._extract_title(raw_html)

        return CrawlResult(
            url=response_url,
            status_code=response_status,
            content_type=response_content_type,
            raw_html=raw_html,
            markdown=markdown,
            title=title,
            metadata={
                "final_url": response_url,
                "content_length": len(raw_html),
                "headers": response_headers,
            },
        )

    async def _robots_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            response = await self.client.get(robots_url, follow_redirects=False)
        except httpx.HTTPError:
            return False
        if response.status_code == 404:
            return True
        if response.status_code != 200:
            return False
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(settings.crawler_user_agent, url)

    async def _crawl_with_js(self, url: str) -> CrawlResult:
        """
        Crawl a JavaScript-heavy page.

        Tries Crawl4AI first, falls back to Playwright.
        This is a placeholder — full implementation in Phase 2.
        """
        # For now, fall back to static crawling
        # TODO: Integrate Crawl4AI and Playwright
        return await self._crawl_static(url)

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to clean markdown, stripping navigation/ads."""
        try:
            # Use markdownify for conversion
            markdown = md(
                html,
                strip=["script", "style", "nav", "footer", "header", "aside"],
                heading_style="ATX",
            )
            # Clean up excessive whitespace
            lines = [line.strip() for line in markdown.split("\n")]
            markdown = "\n".join(line for line in lines if line)
            return markdown[:50000]  # Limit to 50K chars
        except Exception:
            return html[:50000]

    def _extract_title(self, html: str) -> str:
        """Extract the page title from HTML."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            return title_tag.get_text(strip=True) if title_tag else ""
        except Exception:
            return ""

    async def close(self) -> None:
        """Clean up the HTTP client."""
        await self.client.aclose()
