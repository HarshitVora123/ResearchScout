"""
Recommendation Engine — Multi-signal scoring, Reciprocal Rank Fusion (RRF),
and Maximal Marginal Relevance (MMR) for personalized opportunity recommendations.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from app.nlp.skill_extraction import compute_skill_overlap
from app.vector.qdrant_service import QdrantService

logger = structlog.get_logger(__name__)


@dataclass
class RecommendationItem:
    """A recommended opportunity with score decomposition."""

    opportunity_id: str
    total_score: float
    vector_score: float
    graph_score: float
    rule_score: float
    match_reasons: list[str]
    opportunity_data: dict[str, Any]


class RecommendationEngine:
    """
    Multi-Signal Recommendation Engine for ResearchScout.

    Combines:
    - Vector Semantic Similarity (Qdrant)
    - Knowledge Graph Proximity (Neo4j)
    - Rule-based eligibility & preference matching
    - Reciprocal Rank Fusion (RRF)
    - Maximal Marginal Relevance (MMR) diversification
    """

    def __init__(
        self,
        vector_weight: float = 0.45,
        graph_weight: float = 0.30,
        rule_weight: float = 0.25,
    ):
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.rule_weight = rule_weight

    def calculate_rule_score(
        self,
        user_profile: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """
        Calculate rule-based match score and match reasons.

        Checks:
        - Country match (preferred countries vs. opportunity country)
        - Degree level eligibility
        - Skill overlap (profile skills vs. required skills)
        - Research interest alignment
        - Funding type preference
        """
        score = 0.0
        max_possible = 1.0
        reasons = []

        # 1. Preferred Countries (25% of rule score)
        pref_countries = [c.lower() for c in user_profile.get("preferred_countries", [])]
        opp_country = (opportunity.get("country") or "").lower()
        if pref_countries:
            if opp_country in pref_countries:
                score += 0.25
                reasons.append(f"Located in target country ({opportunity.get('country')})")
        else:
            score += 0.15  # Neutral if no preference set

        # 2. Degree Level Compatibility (25% of rule score)
        user_degree = user_profile.get("degree_level", "")
        opp_type = opportunity.get("opportunity_type", "")
        opp_degrees = [d.lower() for d in opportunity.get("degree_levels", [])]

        if user_degree:
            if "phd" in user_degree.lower() and opp_type in ["Postdoc", "AI Residency"]:
                score += 0.25
                reasons.append(f"Ideal fit for {user_degree} degree level")
            elif "master" in user_degree.lower() and opp_type in ["PhD", "Research Assistant"]:
                score += 0.25
                reasons.append(f"Natural progression for {user_degree} degree")
            elif "bachelor" in user_degree.lower() and opp_type in ["Internship", "Scholarship", "PhD"]:
                score += 0.25
                reasons.append(f"Eligible for {user_degree} level background")
            elif any(user_degree.lower() in d for d in opp_degrees):
                score += 0.25
                reasons.append(f"Matches degree eligibility ({user_degree})")

        # 3. Skill & Programming Language Overlap (30% of rule score)
        user_skills = [
            s["skill_name"] if isinstance(s, dict) else s
            for s in user_profile.get("skills", [])
        ]
        opp_skills = opportunity.get("required_skills", []) or []
        opp_langs = opportunity.get("programming_languages", []) or []

        _, _, overlap = compute_skill_overlap(opp_skills + opp_langs, user_skills)
        if overlap > 0:
            skill_score = min(0.30, overlap * 0.4)
            score += skill_score
            reasons.append(f"Matching technical skills ({int(overlap * 100)}% overlap)")

        # 4. Research Interest Alignment (20% of rule score)
        user_interests = [
            i["topic"].lower() if isinstance(i, dict) else i.lower()
            for i in user_profile.get("research_interests", [])
        ]
        opp_areas = [a.lower() for a in opportunity.get("research_areas", [])]

        matched_areas = []
        for interest in user_interests:
            for area in opp_areas:
                if interest in area or area in interest:
                    matched_areas.append(area.title())

        if matched_areas:
            score += 0.20
            reasons.append(f"Aligns with research in {', '.join(set(matched_areas[:2]))}")

        return min(score, max_possible), reasons

    def rrf_combine(
        self,
        vector_rankings: list[str],
        graph_rankings: list[str],
        k: int = 60,
    ) -> dict[str, float]:
        """
        Reciprocal Rank Fusion (RRF).

        RRF_score(d) = sum(1 / (k + rank_i(d)))
        Aggregates rankings from vector search and graph search.
        """
        scores: dict[str, float] = {}

        for rank, item_id in enumerate(vector_rankings):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)

        for rank, item_id in enumerate(graph_rankings):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)

        return scores

    def mmr_rerank(
        self,
        items: list[RecommendationItem],
        lambda_param: float = 0.7,
        top_n: int = 20,
    ) -> list[RecommendationItem]:
        """
        Maximal Marginal Relevance (MMR) for result diversification.

        Balances relevance (total_score) with novelty relative to already selected items
        to prevent recommending 10 near-identical positions.
        """
        if not items:
            return []

        selected: list[RecommendationItem] = []
        unselected = items.copy()

        # Select the highest-scoring item first
        first = max(unselected, key=lambda x: x.total_score)
        selected.append(first)
        unselected.remove(first)

        while len(selected) < top_n and unselected:
            best_item = None
            best_mmr_score = float("-inf")

            for candidate in unselected:
                # Compute max similarity to already selected items
                max_sim = max(
                    self._item_similarity(candidate, sel)
                    for sel in selected
                )

                # MMR score formula
                mmr_score = (lambda_param * candidate.total_score) - ((1 - lambda_param) * max_sim)

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_item = candidate

            if best_item:
                selected.append(best_item)
                unselected.remove(best_item)
            else:
                break

        return selected

    def _item_similarity(self, a: RecommendationItem, b: RecommendationItem) -> float:
        """Estimate similarity between two recommendation items for MMR."""
        data_a = a.opportunity_data
        data_b = b.opportunity_data

        sim = 0.0

        # Same organization
        if data_a.get("organization") and data_a.get("organization") == data_b.get("organization"):
            sim += 0.5

        # Overlapping research areas
        areas_a = set(data_a.get("research_areas") or [])
        areas_b = set(data_b.get("research_areas") or [])
        if areas_a and areas_b:
            jaccard = len(areas_a & areas_b) / len(areas_a | areas_b)
            sim += 0.5 * jaccard

        return sim
