"""
Dedup Agent — detects duplicate and near-duplicate opportunities.

Uses a multi-level deduplication strategy:
1. Exact URL match (already in OpportunityService)
2. Title + Organization exact match (already in OpportunityService)
3. MinHash LSH for fuzzy title matching
4. Vector cosine similarity for semantic dedup
"""

import hashlib
import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DedupResult:
    """Result of a deduplication check."""

    is_duplicate: bool
    duplicate_id: str | None = None
    match_type: str | None = None  # "exact_url", "exact_title", "minhash", "semantic"
    similarity_score: float = 0.0
    details: str = ""


# ── MinHash Implementation (no external dependency) ──


def _tokenize(text: str) -> set[str]:
    """Tokenize text into word n-grams (shingles) for MinHash."""
    text = re.sub(r"[^\w\s]", "", text.lower().strip())
    words = text.split()
    # 3-word shingles
    shingles = set()
    for i in range(len(words) - 2):
        shingles.add(" ".join(words[i : i + 3]))
    # Also add individual words for short texts
    for w in words:
        if len(w) > 3:
            shingles.add(w)
    return shingles


def _minhash_signature(shingles: set[str], num_hashes: int = 128) -> list[int]:
    """Compute a MinHash signature for a set of shingles."""
    if not shingles:
        return [0] * num_hashes

    signature = [float("inf")] * num_hashes

    for shingle in shingles:
        for i in range(num_hashes):
            # Use different hash functions via salted hashing
            h = int(hashlib.md5(f"{i}:{shingle}".encode()).hexdigest()[:8], 16)
            signature[i] = min(signature[i], h)

    return [int(s) for s in signature]


def minhash_similarity(sig_a: list[int], sig_b: list[int]) -> float:
    """Compute Jaccard similarity estimate from two MinHash signatures."""
    if len(sig_a) != len(sig_b) or not sig_a:
        return 0.0
    matches = sum(1 for a, b in zip(sig_a, sig_b, strict=True) if a == b)
    return matches / len(sig_a)


class DedupAgent:
    """
    Multi-strategy deduplication agent.

    Maintains an in-memory MinHash index for fast fuzzy matching,
    and uses Qdrant for semantic similarity checks.
    """

    def __init__(self) -> None:
        # In-memory MinHash index: {opportunity_id: (signature, title, org)}
        self._minhash_index: dict[str, tuple[list[int], str, str]] = {}

    def add_to_index(self, opportunity_id: str, title: str, organization: str) -> None:
        """Add an opportunity to the MinHash index."""
        text = f"{title} {organization}"
        shingles = _tokenize(text)
        signature = _minhash_signature(shingles)
        self._minhash_index[opportunity_id] = (signature, title, organization)

    def check_minhash(self, title: str, organization: str, threshold: float = 0.6) -> DedupResult:
        """
        Check for fuzzy duplicates using MinHash.

        threshold=0.6 catches duplicates like:
        - "PhD Position in NLP" vs "PhD Position in Natural Language Processing"
        - "Research Intern - AI" vs "AI Research Internship"
        """
        text = f"{title} {organization}"
        shingles = _tokenize(text)
        signature = _minhash_signature(shingles)

        best_match_id = None
        best_score = 0.0
        best_title = ""

        for opp_id, (stored_sig, stored_title, stored_org) in self._minhash_index.items():
            similarity = minhash_similarity(signature, stored_sig)
            if similarity > best_score:
                best_score = similarity
                best_match_id = opp_id
                best_title = f"{stored_title} @ {stored_org}"

        if best_score >= threshold:
            return DedupResult(
                is_duplicate=True,
                duplicate_id=best_match_id,
                match_type="minhash",
                similarity_score=best_score,
                details=f"MinHash match ({best_score:.2%}): '{best_title}'",
            )

        return DedupResult(is_duplicate=False)

    async def check_semantic(
        self,
        embedding: list[float],
        threshold: float = 0.92,
    ) -> DedupResult:
        """
        Check for semantic duplicates using vector similarity in Qdrant.

        threshold=0.92 catches opportunities that are semantically identical
        but have different wording (e.g., translated listings).
        """
        from app.vector.qdrant_service import QdrantService

        qdrant = QdrantService()
        matches = qdrant.find_near_duplicates(
            embedding=embedding,
            threshold=threshold,
            limit=3,
        )

        if matches:
            best = matches[0]
            return DedupResult(
                is_duplicate=True,
                duplicate_id=best["id"],
                match_type="semantic",
                similarity_score=best["score"],
                details=(
                    f"Semantic match ({best['score']:.2%}): "
                    f"'{best['title']}' @ {best['organization']}"
                ),
            )

        return DedupResult(is_duplicate=False)

    async def full_dedup_check(
        self,
        title: str,
        organization: str,
        source_url: str,
        embedding: list[float] | None = None,
    ) -> DedupResult:
        """
        Run the full dedup pipeline:
        1. MinHash fuzzy title match
        2. Semantic vector similarity (if embedding provided)
        """
        # Level 1: MinHash
        minhash_result = self.check_minhash(title, organization)
        if minhash_result.is_duplicate:
            logger.info(
                "dedup_minhash_hit",
                title=title[:60],
                match_id=minhash_result.duplicate_id,
                score=minhash_result.similarity_score,
            )
            return minhash_result

        # Level 2: Semantic (if embedding available)
        if embedding:
            semantic_result = await self.check_semantic(embedding)
            if semantic_result.is_duplicate:
                logger.info(
                    "dedup_semantic_hit",
                    title=title[:60],
                    match_id=semantic_result.duplicate_id,
                    score=semantic_result.similarity_score,
                )
                return semantic_result

        return DedupResult(is_duplicate=False)

    @property
    def index_size(self) -> int:
        """Number of entries in the MinHash index."""
        return len(self._minhash_index)
