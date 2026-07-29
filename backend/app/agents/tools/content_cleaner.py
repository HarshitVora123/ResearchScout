"""Content cleaning utilities — transform raw HTML into clean markdown for extraction."""

import re

from markdownify import markdownify as md


def html_to_markdown(html: str) -> str:
    """Convert raw HTML to clean markdown, stripping noise."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            element.decompose()
        clean_html = str(soup)

        markdown = md(
            clean_html,
            heading_style="ATX",
            newline_style="BACKSLASH",
        )
    except Exception:
        # Fallback: strip tags manually
        markdown = re.sub(r"<[^>]+>", " ", html)

    return _clean_markdown(markdown)


def _clean_markdown(text: str) -> str:
    """Post-process markdown for LLM consumption."""
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove common boilerplate patterns
    boilerplate_patterns = [
        r"(?i)cookie\s+(?:policy|consent|preferences).*?\n",
        r"(?i)privacy\s+policy.*?\n",
        r"(?i)terms\s+(?:of\s+)?(?:use|service).*?\n",
        r"(?i)all\s+rights\s+reserved.*?\n",
        r"(?i)©\s*\d{4}.*?\n",
        r"(?i)subscribe\s+to\s+(?:our\s+)?newsletter.*?\n",
        r"(?i)follow\s+us\s+on.*?\n",
        r"(?i)share\s+(?:this|on).*?\n",
        r"(?i)back\s+to\s+top.*?\n",
        r"(?i)skip\s+to\s+(?:main\s+)?content.*?\n",
        r"(?i)toggle\s+navigation.*?\n",
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text)

    # Remove markdown image references (usually logos/icons)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # Remove empty markdown links
    text = re.sub(r"\[]\(.*?\)", "", text)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove excessive blank lines again
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_page_title(html: str) -> str:
    """Extract <title> from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Clean up common title suffixes
        title = re.sub(r"\s*[|\-–—]\s*$", "", title)
        return title[:200]  # Limit length
    return ""


def extract_meta_description(html: str) -> str:
    """Extract meta description from HTML."""
    match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()[:500]
    return ""


def truncate_for_llm(text: str, max_chars: int = 12000) -> str:
    """Truncate text for LLM context window, preferring to keep the beginning."""
    if len(text) <= max_chars:
        return text

    # Try to cut at a paragraph boundary
    truncated = text[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:  # Only if we keep at least 70%
        truncated = truncated[:last_para]

    return truncated + "\n\n[Content truncated...]"
