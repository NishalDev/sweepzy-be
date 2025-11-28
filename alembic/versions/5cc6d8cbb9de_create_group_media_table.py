"""create group_media table

Revision ID: 5cc6d8cbb9de
Revises: 7e359e9b8b71
Create Date: 2025-09-10 18:54:21.368672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5cc6d8cbb9de'
down_revision: Union[str, None] = '7e359e9b8b71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create table with media_type as varchar + CHECK constraint (avoid DB enum creation)
    op.create_table(
        'group_media',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        # matches CleanupEvent.id (UUID)
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', sa.BigInteger(), nullable=True),
        sa.Column('object_key', sa.String(length=1024), nullable=False),
        sa.Column('file_url', sa.String(length=1024), nullable=False),
        sa.Column('thumb_url', sa.String(length=1024), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('media_type', sa.String(length=16), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['event_id'], ['cleanup_events.id'], ondelete='CASCADE'),
        sa.CheckConstraint("media_type IN ('image','video')", name='ck_group_media_media_type_allowed'),
    )

    # Indexes
    op.create_index('idx_group_media_event_id', 'group_media', ['event_id'])
    op.create_index('idx_group_media_uploaded_by', 'group_media', ['uploaded_by'])
    op.create_index('idx_group_media_media_type', 'group_media', ['media_type'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes then table.
    op.drop_index('idx_group_media_media_type', table_name='group_media')
    op.drop_index('idx_group_media_uploaded_by', table_name='group_media')
    op.drop_index('idx_group_media_event_id', table_name='group_media')

    op.drop_table('group_media')

    # No enum type was created by this migration, so nothing to drop.
