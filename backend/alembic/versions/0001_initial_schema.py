"""Initial database schema from SQLAlchemy models."""

from alembic import op

from app.core.database import Base
from app.models.db import crawl, interaction, notification, opportunity, user  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
