"""create cities and landmarks table

Revision ID: 7e359e9b8b71
Revises: 101eb0e2242c
Create Date: 2025-09-07 13:26:52.439244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7e359e9b8b71'
down_revision: Union[str, None] = '101eb0e2242c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # create cities table
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # unique constraint on city name
    op.create_index("uq_cities_name", "cities", ["name"], unique=True)

    # create landmarks table
    op.create_table(
        "landmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    # unique constraint to avoid duplicate landmark names within the same city
    op.create_unique_constraint("uq_landmarks_city_name", "landmarks", ["city_id", "name"])
    # index on landmarks.name for faster searches
    op.create_index("ix_landmarks_name", "landmarks", ["name"])


def downgrade() -> None:
    """Downgrade schema."""
    # drop landmarks first (depends on cities)
    op.drop_index("ix_landmarks_name", table_name="landmarks")
    op.drop_constraint("uq_landmarks_city_name", "landmarks", type_="unique")
    op.drop_table("landmarks")

    # drop cities
    op.drop_index("uq_cities_name", table_name="cities")
    op.drop_table("cities")
