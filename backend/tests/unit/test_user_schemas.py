from datetime import UTC, datetime
from uuid import uuid4

from app.models.schemas.user import UserProfileResponse


def test_profile_response_normalizes_missing_preferences():
    now = datetime.now(UTC)
    profile = UserProfileResponse.model_validate(
        {
            "id": uuid4(),
            "email": "researcher@example.com",
            "full_name": "Researcher",
            "preferred_countries": None,
            "preferred_domains": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert profile.preferred_countries == []
    assert profile.preferred_domains == []
