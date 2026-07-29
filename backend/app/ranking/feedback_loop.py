"""
Feedback Loop & Learning Agent — dynamic user preference adaptation.

Updates user profile weights based on explicit and implicit feedback signals:
- Saved: +1.0 interest weight
- Applied: +2.0 interest weight
- Dismissed: -1.0 interest weight (suppresses similar positions)
- Clicked: +0.2 interest weight
"""

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

INTERACTION_WEIGHTS = {
    "save": 1.0,
    "apply": 2.0,
    "dismiss": -1.0,
    "click": 0.2,
}


@dataclass
class PreferenceUpdate:
    """Calculated adjustments to user preference weights."""

    topic_delta: dict[str, float]
    skill_delta: dict[str, float]
    country_delta: dict[str, float]


class FeedbackAgent:
    """
    Adapts user recommendations dynamically based on interaction feedback.
    """

    def process_interaction(
        self,
        interaction_type: str,  # "save", "apply", "dismiss", "click"
        opportunity_data: dict[str, Any],
    ) -> PreferenceUpdate:
        """Calculate preference updates for a single user interaction."""
        weight = INTERACTION_WEIGHTS.get(interaction_type.lower(), 0.0)

        topic_delta: dict[str, float] = {}
        skill_delta: dict[str, float] = {}
        country_delta: dict[str, float] = {}

        # 1. Research topics
        for area in opportunity_data.get("research_areas") or []:
            area_name = area.strip().title()
            topic_delta[area_name] = topic_delta.get(area_name, 0.0) + weight

        # 2. Skills
        for skill in opportunity_data.get("required_skills") or []:
            skill_name = skill.strip().lower()
            skill_delta[skill_name] = skill_delta.get(skill_name, 0.0) + weight

        # 3. Country
        country = opportunity_data.get("country")
        if country:
            country_delta[country] = country_delta.get(country, 0.0) + weight

        logger.info(
            "feedback_processed",
            interaction=interaction_type,
            opp_title=opportunity_data.get("title", "")[:50],
            topics_updated=len(topic_delta),
        )

        return PreferenceUpdate(
            topic_delta=topic_delta,
            skill_delta=skill_delta,
            country_delta=country_delta,
        )
