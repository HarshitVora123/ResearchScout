"""Unit tests for content cleaning and rate limiting utilities."""

import pytest

from app.agents.tools.content_cleaner import (
    html_to_markdown,
    extract_page_title,
    extract_meta_description,
    truncate_for_llm,
)
from app.agents.tools.rate_limiter import (
    get_domain,
    get_rate_for_domain,
    InMemoryRateLimiter,
)


# ══════════════════════════════════════════════════════
# Content Cleaner Tests
# ══════════════════════════════════════════════════════

class TestContentCleaner:
    """Test HTML-to-markdown cleaning."""

    def test_basic_html_to_markdown(self):
        html = "<h1>Hello</h1><p>World</p>"
        md = html_to_markdown(html)
        assert "Hello" in md
        assert "World" in md

    def test_strips_scripts_and_styles(self):
        html = """
        <html>
        <script>var x = 1;</script>
        <style>.cls { color: red; }</style>
        <p>Actual content</p>
        </html>
        """
        md = html_to_markdown(html)
        assert "var x" not in md
        assert "color: red" not in md
        assert "Actual content" in md

    def test_strips_navigation(self):
        html = """
        <nav><a href="/">Home</a><a href="/about">About</a></nav>
        <main><p>Main content here</p></main>
        """
        md = html_to_markdown(html)
        assert "Main content" in md

    def test_removes_boilerplate(self):
        html = "<p>Research position</p><p>Cookie policy: we use cookies</p>"
        md = html_to_markdown(html)
        assert "Research position" in md

    def test_extract_title(self):
        html = "<html><head><title>PhD Position - MIT</title></head><body></body></html>"
        title = extract_page_title(html)
        assert title == "PhD Position - MIT"

    def test_extract_meta_description(self):
        html = '<html><head><meta name="description" content="Apply for our PhD program"></head></html>'
        desc = extract_meta_description(html)
        assert "PhD program" in desc

    def test_truncate_short_text(self):
        text = "Short text"
        assert truncate_for_llm(text, 1000) == text

    def test_truncate_long_text(self):
        text = "Word " * 5000  # 25000 chars
        truncated = truncate_for_llm(text, 1000)
        assert len(truncated) <= 1100  # Some margin for "[Content truncated...]"
        assert "[Content truncated...]" in truncated


# ══════════════════════════════════════════════════════
# Rate Limiter Tests
# ══════════════════════════════════════════════════════

class TestRateLimiter:
    """Test rate limiting utilities."""

    def test_get_domain(self):
        assert get_domain("https://cs.stanford.edu/positions") == "stanford.edu"
        assert get_domain("https://openai.com/careers") == "openai.com"
        assert get_domain("https://api.github.com/repos") == "github.com"

    def test_get_rate_for_known_domain(self):
        rate = get_rate_for_domain("openai.com")
        assert rate == 0.5

    def test_get_rate_for_edu_suffix(self):
        rate = get_rate_for_domain("stanford.edu")
        assert rate == 0.5  # edu rate

    def test_get_rate_for_unknown_domain(self):
        rate = get_rate_for_domain("random-site.xyz")
        assert rate == 1.0  # default rate

    def test_in_memory_limiter_first_request_instant(self):
        limiter = InMemoryRateLimiter()
        wait = limiter.acquire("https://example.com/page1")
        assert wait == 0.0

    def test_in_memory_limiter_second_request_delayed(self):
        limiter = InMemoryRateLimiter()
        limiter.acquire("https://example.com/page1")
        wait = limiter.acquire("https://example.com/page2")
        # Second request to same domain should require waiting
        assert wait > 0.0

    def test_different_domains_independent(self):
        limiter = InMemoryRateLimiter()
        limiter.acquire("https://example.com/page1")
        wait = limiter.acquire("https://other-site.org/page1")
        # Different domain should not be rate limited
        assert wait == 0.0
