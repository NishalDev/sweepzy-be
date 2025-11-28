"""create cleanup_event_reports mapping table

Revision ID: 31fb7b47e25c
Revises: 1ef48c8b3921
Create Date: 2025-07-08 13:07:00.727341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '31fb7b47e25c'
down_revision: Union[str, None] = '1ef48c8b3921'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'cleanup_event_reports',
        # Surrogate primary key
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        # Foreign keys
        sa.Column(
            'event_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('cleanup_events.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'report_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('litter_reports.id', ondelete='CASCADE'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('cleanup_event_reports')
