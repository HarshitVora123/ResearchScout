"""Initial database schema from SQLAlchemy models."""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op
from app.core.database import Base
from app.models.db import crawl, interaction, notification, opportunity, user  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Create tables introduced after the first local database version while
    # preserving existing rows in databases that were created before Alembic.
    Base.metadata.create_all(bind=bind)

    user_columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "token_version" not in user_columns:
        op.add_column(
            "users",
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        )

    inspector = inspect(bind)
    unique_source_constraints = [
        constraint
        for constraint in inspector.get_unique_constraints("opportunities")
        if constraint.get("column_names") == ["source_url"]
    ]
    if unique_source_constraints:
        if bind.dialect.name == "sqlite":
            # Older SQLite schemas made source_url unique, which prevented a
            # page containing multiple opportunities from being stored.
            with op.batch_alter_table(
                "opportunities",
                recreate="always",
                naming_convention={
                    "uq": "uq_%(table_name)s_%(column_0_name)s",
                },
            ) as batch_op:
                batch_op.drop_constraint("uq_opportunities_source_url", type_="unique")
        else:
            for constraint in unique_source_constraints:
                if constraint.get("name"):
                    op.drop_constraint(constraint["name"], "opportunities", type_="unique")

    op.create_index(
        "ix_opportunities_source_url",
        "opportunities",
        ["source_url"],
        if_not_exists=True,
    )


def downgrade() -> None:
    # This baseline migration may have adopted a pre-existing database. Do not
    # drop its tables or user data during downgrade.
    bind = op.get_bind()
    user_columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "token_version" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("token_version")
