"""modify event join model

Revision ID: 10c7c5144e3d
Revises: 990d6492fd56
Create Date: 2025-06-17 13:08:58.462529
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '10c7c5144e3d'
down_revision: Union[str, None] = '990d6492fd56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Reassign any 'participant' roles to 'volunteer'
    op.execute("UPDATE event_join SET role = 'volunteer' WHERE role = 'participant';")

    # Add new roles to the existing PostgreSQL enum type
    op.execute("ALTER TYPE eventjoinrole ADD VALUE IF NOT EXISTS 'photo_verifier';")
    op.execute("ALTER TYPE eventjoinrole ADD VALUE IF NOT EXISTS 'field_recorder';")
    op.execute("ALTER TYPE eventjoinrole ADD VALUE IF NOT EXISTS 'logistics_assistant';")
    op.execute("ALTER TYPE eventjoinrole ADD VALUE IF NOT EXISTS 'reporter';")


def downgrade() -> None:
    """Downgrade schema (no-op for enum alterations)."""
    # PostgreSQL does not support removing enum values; to revert you would need
    # to recreate the type without those values and migrate the column.
    pass
