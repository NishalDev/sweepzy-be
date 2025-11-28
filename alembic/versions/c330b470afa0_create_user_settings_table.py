"""create user_settings table

Revision ID: c330b470afa0
Revises: e6703edb3f6b
Create Date: 2025-08-05 18:34:15.021603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c330b470afa0'
down_revision: Union[str, None] = 'e6703edb3f6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_settings',
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('seen_tour', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('language', sa.String(2), nullable=True,  server_default=None),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_settings')
