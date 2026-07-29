"""
Explanation Agent — generates personalized match explanations for recommendations.

Translates technical match signals (vector similarity, KG paths, skill overlap,
eligibility) into clear, user-friendly markdown bullet points.
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ExplanationAgent:
    """
    Generates human-readable match explanations.

    Example output:
    - 🎯 94% Match: Directly aligns with your research in Natural Language Processing
    - 🛠️ Matches 4 of your skills: Python, PyTorch, Transformers, Knowledge Graphs
    - 🏛️ Top institution: ETH Zurich (fits your preferred location in Switzerland)
    - 🎓 Eligible for your Master's degree background
    """

    def generate_explanation(
        self,
        total_score: float,
        vector_score: float,
        graph_score: float,
        rule_reasons: list[str],
        user_profile: dict[str, Any],
        opportunity: dict[str, Any],
    ) -> list[str]:
        """Generate structured match explanation bullet points."""
        bullets = []

        # 1. High-level match percentage
        match_pct = int(min(total_score, 1.0) * 100)
        bullets.append(f"🎯 {match_pct}% Match Score")

        # 2. Rule reasons (from recommendation engine)
        for reason in rule_reasons[:3]:
            bullets.append(f"✨ {reason}")

        # 3. Graph connections (if graph score contributed)
        if graph_score > 0.3:
            bullets.append("🔗 High graph connectivity with your research network")

        # 4. Verification & Confidence
        confidence = opportunity.get("confidence_score", 0.0)
        if confidence >= 0.85:
            bullets.append("🛡️ High authenticity score (verified listing)")

        # 5. Deadline urgency
        deadline_str = opportunity.get("deadline")
        if deadline_str:
            bullets.append("⏰ Application open")

        return bullets
