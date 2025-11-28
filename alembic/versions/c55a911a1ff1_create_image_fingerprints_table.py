"""create image_fingerprints table

Revision ID: c55a911a1ff1
Revises: 7add1142fbe1
Create Date: 2025-07-09 12:06:25.806662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c55a911a1ff1'
down_revision: Union[str, None] = '7add1142fbe1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'image_fingerprints',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_reports.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('phash', sa.String(length=64), nullable=False),
        sa.Column('embedding', sa.LargeBinary(), nullable=False),
    )
    # If you want an index on phash for faster lookup:
    op.create_index('ix_image_fingerprints_phash', 'image_fingerprints', ['phash'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_image_fingerprints_phash', table_name='image_fingerprints')
    op.drop_table('image_fingerprints')
