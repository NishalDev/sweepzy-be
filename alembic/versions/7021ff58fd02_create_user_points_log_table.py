"""create user_points_log table

Revision ID: 7021ff58fd02
Revises: 44351ef6af1e
Create Date: 2025-06-18 16:08:20.428273
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7021ff58fd02'
down_revision: Union[str, Sequence[str], None] = '44351ef6af1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create user_points_log table"""
    op.create_table(
        'user_points_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema: drop user_points_log table"""
    op.drop_table('user_points_log')
