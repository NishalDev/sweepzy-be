"""create photo verifications table

Revision ID: 3978fc795512
Revises: af618ae533d5
Create Date: 2025-07-01 15:40:47.364100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3978fc795512'
down_revision: Union[str, None] = 'af618ae533d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


enums = {
    'phase': {
        'name': 'photophase',
        'values': ['before', 'after']
    },
    'status': {
        'name': 'verificationstatus',
        'values': ['pending_review', 'approved', 'rejected']
    }
}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    # Create enums if not exist
    for e in enums.values():
        pg_enum = postgresql.ENUM(*e['values'], name=e['name'])
        pg_enum.create(bind=bind, checkfirst=True)

    # Create table with existing enums
    op.create_table(
        'photo_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cleanup_events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('litter_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('captured_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('phase', postgresql.ENUM(name='photophase', create_type=False), nullable=False),
        sa.Column('photo_urls', sa.JSON(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', postgresql.ENUM(name='verificationstatus', create_type=False), nullable=False, server_default=sa.text("'pending_review'")),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('event_id', 'report_id', 'captured_by', 'phase', name='uq_photo_event_user_phase')
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.drop_table('photo_verifications')
    # Drop enums
    for key in ['status', 'phase']:
        name = enums[key]['name']
        postgresql.ENUM(name=name).drop(bind=bind, checkfirst=True)
