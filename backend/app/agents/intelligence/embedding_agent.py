"""
Embedding Agent — generates vector embeddings for opportunities and user profiles.

Supports multiple embedding backends:
- OpenAI text-embedding-3-large (primary, 3072-dim)
- Google Gemini text-embedding-004 (fallback, 768-dim)
- Local sentence-transformers (offline fallback)
"""

import hashlib
from typing import Any

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# ── Embedding Cache (LRU in-memory) ─────────────────
_embedding_cache: dict[str, list[float]] = {}
MAX_CACHE_SIZE = 500


def _cache_key(text: str) -> str:
    """Generate a short cache key from text."""
    return hashlib.md5(text.encode()).hexdigest()


class EmbeddingAgent:
    """
    Generates vector embeddings for text using LLM APIs.

    Embeds both opportunities (for similarity search + dedup)
    and user profiles (for recommendation matching).
    """

    def __init__(self) -> None:
        self._openai_client = None

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding vector for a single text.

        Tries OpenAI → Gemini → local fallback.
        """
        # Check cache
        key = _cache_key(text)
        if key in _embedding_cache:
            return _embedding_cache[key]

        # Truncate for model limits
        text = text[:8000]

        embedding = None

        # Try OpenAI
        if settings.openai_api_key:
            try:
                embedding = await self._embed_openai(text)
            except Exception as e:
                logger.warning("openai_embedding_failed", error=str(e))

        # Fallback: Google Gemini
        if embedding is None and settings.google_api_key:
            try:
                embedding = await self._embed_gemini(text)
            except Exception as e:
                logger.warning("gemini_embedding_failed", error=str(e))

        if embedding is not None and len(embedding) != settings.embedding_dimensions:
            logger.warning(
                "embedding_dimension_mismatch",
                expected=settings.embedding_dimensions,
                actual=len(embedding),
            )
            embedding = None

        if embedding is None:
            logger.error("all_embedding_backends_failed")
            raise RuntimeError("No embedding backend available")

        # Cache result
        if len(_embedding_cache) >= MAX_CACHE_SIZE:
            # Evict oldest entries (simple FIFO)
            oldest_keys = list(_embedding_cache.keys())[:100]
            for k in oldest_keys:
                del _embedding_cache[k]
        _embedding_cache[key] = embedding

        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch."""
        if settings.openai_api_key:
            try:
                return await self._embed_openai_batch(texts)
            except Exception as e:
                logger.warning("openai_batch_embedding_failed", error=str(e))

        # Fallback to one-by-one
        return [await self.embed_text(text) for text in texts]

    def compose_opportunity_text(self, opp: dict[str, Any]) -> str:
        """
        Compose a rich text representation of an opportunity for embedding.

        Combines title, organization, research areas, skills, and summary
        into a single text optimized for semantic similarity.
        """
        parts = []

        if opp.get("title"):
            parts.append(f"Position: {opp['title']}")
        if opp.get("organization"):
            parts.append(f"Organization: {opp['organization']}")
        if opp.get("opportunity_type"):
            parts.append(f"Type: {opp['opportunity_type']}")
        if opp.get("department"):
            parts.append(f"Department: {opp['department']}")
        if opp.get("country"):
            loc = opp["country"]
            if opp.get("city"):
                loc = f"{opp['city']}, {loc}"
            parts.append(f"Location: {loc}")
        if opp.get("research_areas"):
            areas = opp["research_areas"]
            if isinstance(areas, list):
                parts.append(f"Research Areas: {', '.join(areas)}")
        if opp.get("required_skills"):
            skills = opp["required_skills"]
            if isinstance(skills, list):
                parts.append(f"Required Skills: {', '.join(skills)}")
        if opp.get("programming_languages"):
            langs = opp["programming_languages"]
            if isinstance(langs, list):
                parts.append(f"Programming: {', '.join(langs)}")
        if opp.get("funding_type"):
            parts.append(f"Funding: {opp['funding_type']}")
        if opp.get("summary"):
            parts.append(f"Description: {opp['summary']}")

        return "\n".join(parts)

    def compose_user_text(self, profile: dict[str, Any]) -> str:
        """
        Compose a rich text representation of a user profile for embedding.

        Used for matching users to opportunities via vector similarity.
        """
        parts = []

        if profile.get("full_name"):
            parts.append(f"Researcher: {profile['full_name']}")
        if profile.get("degree_level"):
            parts.append(f"Degree: {profile['degree_level']}")
        if profile.get("university"):
            parts.append(f"University: {profile['university']}")
        if profile.get("career_goals"):
            parts.append(f"Career Goals: {profile['career_goals']}")
        if profile.get("skills"):
            skill_names = [s["skill_name"] if isinstance(s, dict) else s for s in profile["skills"]]
            parts.append(f"Skills: {', '.join(skill_names)}")
        if profile.get("research_interests"):
            topics = [i["topic"] if isinstance(i, dict) else i for i in profile["research_interests"]]
            parts.append(f"Research Interests: {', '.join(topics)}")
        if profile.get("publications"):
            titles = [p["title"] if isinstance(p, dict) else p for p in profile["publications"][:5]]
            parts.append(f"Publications: {'; '.join(titles)}")
        if profile.get("preferred_countries"):
            parts.append(f"Preferred Countries: {', '.join(profile['preferred_countries'])}")

        return "\n".join(parts)

    # ── Backend Implementations ──────────────────────

    async def _embed_openai(self, text: str) -> list[float]:
        """Generate embedding via OpenAI text-embedding-3-large."""
        from openai import AsyncOpenAI

        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        response = await self._openai_client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        return response.data[0].embedding

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding via OpenAI."""
        from openai import AsyncOpenAI

        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Truncate each text
        truncated = [t[:8000] for t in texts]

        response = await self._openai_client.embeddings.create(
            model=settings.embedding_model,
            input=truncated,
            dimensions=settings.embedding_dimensions,
        )

        # Sort by index to preserve order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    async def _embed_gemini(self, text: str) -> list[float]:
        """Generate embedding via Google Gemini."""
        import google.genai as genai

        client = genai.Client(api_key=settings.google_api_key)
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": settings.embedding_dimensions},
        )
        if result.embeddings is None:
            raise RuntimeError("Gemini embedding returned None")
        return result.embeddings[0].values
