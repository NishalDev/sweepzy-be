"""create badges and user_badges table and add points column to user table

Revision ID: 44351ef6af1e
Revises: 1e9521b854f7
Create Date: 2025-06-18 15:27:22.393092
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '44351ef6af1e'
down_revision: Union[str, None] = '1e9521b854f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # create badges table
    op.create_table(
        'badges',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('icon_key', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # create user_badges table with integer user_id
    op.create_table(
        'user_badges',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('badge_id', sa.Integer(), sa.ForeignKey('badges.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # add points column to users
    op.add_column('users', sa.Column('points', sa.Integer(), nullable=False, server_default='0'))
    # optionally remove default
    op.alter_column('users', 'points', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # remove points column
    op.drop_column('users', 'points')

    # drop user_badges table
    op.drop_table('user_badges')

    # drop badges table
    op.drop_table('badges')
