"""modify litter_reports table add event_id

Revision ID: 9a536882d7ed
Revises: 31fb7b47e25c
Create Date: 2025-07-08 13:12:51.179852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a536882d7ed'
down_revision: Union[str, None] = '31fb7b47e25c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) add the new nullable event_id column
    op.add_column(
        'litter_reports',
        sa.Column(
            'event_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Which cleanup event this report belongs to"
        )
    )
    # 2) create an index for faster lookups
    op.create_index(
        'ix_litter_reports_event_id',
        'litter_reports',
        ['event_id']
    )
    # 3) add the foreign‑key constraint to cleanup_events.id
    op.create_foreign_key(
        'fk_litter_reports_event',
        'litter_reports',
        'cleanup_events',
        ['event_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1) drop foreign‑key constraint
    op.drop_constraint(
        'fk_litter_reports_event',
        'litter_reports',
        type_='foreignkey'
    )
    # 2) drop index
    op.drop_index('ix_litter_reports_event_id', table_name='litter_reports')
    # 3) drop the column
    op.drop_column('litter_reports', 'event_id')
